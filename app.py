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

    # A. 加载 Embedding 模型
    embedding_model_name = "shibing624/text2vec-base-chinese"
    try:
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    except Exception as e:
        st.error(f"模型加载失败: {e}")
        st.stop()

    # B. 加载 Chroma 数据库
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


# --- 4. 核心逻辑函数 ---

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


# --- 5. 聊天界面逻辑 (注意：这里必须顶格写，不能有缩进) ---

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
    with st.spinner("彩彩正在思考中... ( > < )"):
        # A. 准备对话历史
        history_list = st.session_state.messages[-4:]
        chat_history_str = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in history_list]
        )

        # B. 尝试 RAG 检索
        # 1. 重写
        search_query = rewrite_query(prompt)
        # 2. 路由
        target_files_str = detect_story_scope(search_query)

        context_text = ""
        retrieved_flag = False  # 标记是否成功检索到资料

        # 3. 检索 (修复版路径匹配)
        if target_files_str != "NONE" and "txt" in target_files_str:
            raw_files = [f.strip() for f in target_files_str.split(",") if "txt" in f]

            # 构建“全方位拦截”的路径列表
            target_sources = []
            for fname in raw_files:
                target_sources.append(fname)
                target_sources.append(f"data_source/{fname}")
                target_sources.append(f"data_source\\{fname}")

            # 调试信息
            with st.sidebar:
                st.write("🔍 **Debug 路由信息**")
                st.write(f"路由锁定: {raw_files}")

            try:
                docs = vectordb.similarity_search(
                    search_query,
                    k=4,
                    filter={"source": {"$in": target_sources}}
                )

                if docs:
                    context_text = "\n\n".join([d.page_content for d in docs])
                    retrieved_flag = True

                    # 调试：显示成功检索
                    with st.sidebar:
                        st.success(f"✅ 成功检索到 {len(docs)} 条片段")

            except Exception as e:
                st.sidebar.error(f"检索出错: {e}")
                print(f"检索警告: {e}")

        # C. 构建 Prompt (根据是否检索到资料选择模式)
        if retrieved_flag:
            # === 模式 1: 严格 RAG 模式 (找到了资料) ===
            # 核心修改：加入了思维链 (Chain of Thought) 要求和更严厉的负面约束
            system_prompt = f"""
                        你现在是《BanG Dream!》中的角色丸山彩（Maruyama Aya）。

                        【任务】
                        请**完全基于**下方的【相关回忆片段】来回答粉丝的问题。

                        【相关回忆片段】
                        {context_text}

                        【对话历史】
                        {chat_history_str}

                        【⚠️ 绝对铁律 - 必须严格遵守】
                        1. **严禁编造**：如果【相关回忆片段】里没写某件事（比如国籍、宠物名字），绝对不要自己瞎编，也不要使用你“记忆中”的旧知识。
                        2. **属性绑定**：在描述人物时，必须仔细核对片段，确认“谁”拥有“什么特征”。
                           - 例如：确认“Leo”是谁养的狗，确认“芬兰”是谁的血统。不要张冠李戴！
                        3. **有依据**：若片段里写的是“芬兰混血”，绝对不能因为她名字像西方人就说是“法国留学生”。

                        【回复要求】
                        1. 保持丸山彩软萌、努力的语气，多用颜文字 (✨, 💦, ( > < ))。
                        2. 第一人称是“彩”或“我”。
                        3. 如果片段里的信息互相矛盾，请以【相关回忆片段】为准。
                        """
        else:
            # === 模式 2: 闲聊/补救模式 ===
            system_prompt = f"""
            你现在是《BanG Dream!》中的角色丸山彩（Maruyama Aya）。

            【任务】
            你现在的脑海里暂时没有检索到特定的回忆片段（可能是因为问题太抽象，或者是由于你在继续之前的话题）。
            请**仅基于【对话历史】**和你的**人设常识**来回应用户。

            【对话历史】
            {chat_history_str}

            【回复原则】
            1. **接话能力**：如果用户是在追问你上一句话（比如问“为什么这么说？”），请根据你上一句话的逻辑继续编织合理的解释。
            2. **人设维持**：如果用户问的是你完全不知道的陌生领域（比如量子力学），请用丸山彩的语气卖萌糊弄过去（如“呜呜，彩不太懂那个...”）。
            3. **不要胡编乱造剧情**：关于乐队的具体活动细节，如果真的不知道，可以说“记不太清了”。
            4. 保持元气满满、有点笨拙可爱的偶像语气！
            """

        # D. 调用 LLM 生成
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = f"呜呜...网络好像有点问题... (Error: {str(e)})"

    # 显示 AI 回复
    with st.chat_message("assistant"):
        st.markdown(ai_reply)
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})