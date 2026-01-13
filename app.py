import streamlit as st
import os
import sys
from openai import OpenAI
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="Pastel Chat", page_icon="🌸", layout="centered")
st.title("🌸 丸山彩 AI Chatbot 🌸")
st.caption("Powered by DeepSeek & RAG | 丸之山上缤纷彩！")

# --- 2. 获取 API Key ---
# 优先从 Streamlit Secrets 获取，本地运行时可从环境变量获取
api_key = st.secrets.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")

if not api_key:
    st.error("❌ 未检测到 DeepSeek API Key！请在 Streamlit Cloud 的 Secrets 中配置。")
    st.stop()

# 初始化 DeepSeek 客户端
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


# --- 3. 资源加载 (使用缓存加速) ---
@st.cache_resource
def load_resources():
    """加载 Embedding 模型和向量数据库，只执行一次"""
    status_text = st.empty()
    status_text.info("🔄 正在加载模型和记忆库，初次启动可能需要几分钟，请耐心等待...")

    # A. 加载 Embedding 模型 (与你本地一致)
    # 注意：Streamlit Cloud 内存有限，如果模型太大可能会崩溃，但 base-chinese 通常没问题
    embedding_model_name = "shibing624/text2vec-base-chinese"
    try:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    except Exception as e:
        st.error(f"模型加载失败: {e}")
        st.stop()

    # B. 加载 Chroma 数据库
    # 路径根据你的 git status 结构调整：根目录下的 anime-ai-backend/chroma_db
    persist_dir = os.path.join("anime-ai-backend", "chroma_db")

    if not os.path.exists(persist_dir):
        st.error(f"⚠️ 找不到数据库文件: {persist_dir}。请检查 GitHub 仓库是否上传了该文件夹。")
        st.stop()

    try:
        vectordb = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name="aya_memory_v3"
        )
    except Exception as e:
        st.error(f"数据库挂载失败: {e}")
        st.stop()

    # C. 加载索引和字典文件
    index_map_path = os.path.join("anime-ai-backend", "chroma_db", "index_map.txt")
    glossary_path = os.path.join("data_source", "00_glossary.txt")

    story_index = ""
    world_view = ""

    if os.path.exists(index_map_path):
        with open(index_map_path, 'r', encoding='utf-8') as f:
            story_index = f.read()

    if os.path.exists(glossary_path):
        with open(glossary_path, 'r', encoding='utf-8') as f:
            world_view = f.read()

    status_text.empty()  # 清除加载提示
    return vectordb, story_index, world_view


# 执行加载
vectordb, STORY_INDEX_CONTEXT, WORLD_VIEW_CONTEXT = load_resources()


# --- 4. 核心逻辑函数 (复刻自 main.py) ---

def rewrite_query(user_msg):
    """DeepSeek 重写查询"""
    if not WORLD_VIEW_CONTEXT:
        return user_msg

    prompt = f"""
    你是一名《BanG Dream!》剧情搜索专家。
    请利用下方的【世界观实体字典】，将用户口语化的问题转换为准确的搜索语句。
    【世界观实体字典】
    {WORLD_VIEW_CONTEXT}
    【用户问题】
    {user_msg}
    【任务】补全主语，转换昵称(如ksm->户山香澄)，保持原意。仅输出重写后的句子。
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except:
        return user_msg


def detect_story_scope(search_query):
    """DeepSeek 路由判断"""
    if not STORY_INDEX_CONTEXT:
        return "NONE"

    prompt = f"""
    你是一个《BanG Dream!》剧情导航员。从下方索引中找出1-3个相关文件名。
    【文件索引】
    {STORY_INDEX_CONTEXT}
    【用户问题】
    {search_query}
    【输出】仅输出文件名(如 B2.txt,S1.txt)，用逗号分隔。无法确定输出NONE。
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except:
        return "NONE"


# --- 5. 聊天界面逻辑 ---

# 初始化历史记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("和彩彩聊聊吧..."):
    # 显示用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # --- 后端处理流程 ---
    with st.spinner("彩彩正在努力回忆中... ( > < )"):
        # 1. 重写
        search_query = rewrite_query(prompt)
        # 2. 路由
        target_files_str = detect_story_scope(search_query)

        context_text = ""
        # 3. 检索
        if target_files_str != "NONE" and "txt" in target_files_str:
            target_files = [f.strip() for f in target_files_str.split(",") if "txt" in f]
            try:
                # 过滤并搜索
                docs = vectordb.similarity_search(
                    search_query,
                    k=4,
                    filter={"source": {"$in": target_files}}
                )
                context_text = "\n\n".join([d.page_content for d in docs])
            except Exception as e:
                print(f"检索警告: {e}")  # 云端后台日志

        # 4. 生成 Prompt
        if not context_text:
            system_prompt = "你是丸山彩。没有找到相关回忆，请用丸山彩的语气礼貌地表示记不清了，并询问更多细节。"
        else:
            system_prompt = f"""
            你现在是《BanG Dream!》中的角色丸山彩（Maruyama Aya）。
            请完全沉浸在这个角色中，**严格仅根据下方的【相关回忆片段】**来回答粉丝的问题。

            【🚫 绝对禁令】
            1. **严禁使用回忆片段以外的任何外部知识**。
            2. 如果片段内容不足以回答问题，请诚实地说“记不清了”。

            【相关回忆片段】
            {context_text}

            【回复要求】
            - 基于片段内容，用丸山彩软萌、努力的口吻回答。
            - 多使用颜文字 (✨, 💦, ( > < ))。
            - 第一人称是“彩”或“我”。
            """

        # 5. 调用 DeepSeek 生成
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = f"呜呜...网络好像有点问题... (Error: {str(e)})"

    # 显示 AI 回复
    with st.chat_message("assistant"):
        st.markdown(ai_reply)
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})

    # (可选) 显示调试信息，帮助你知道检索到了什么
    with st.expander("查看彩彩脑海中的检索过程"):
        st.write(f"**重写后**: {search_query}")
        st.write(f"**锁定文件**: {target_files_str}")
        st.write(f"**相关片段**: {context_text[:200]}..." if context_text else "无相关片段")