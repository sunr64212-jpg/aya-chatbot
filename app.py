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
        with st.spinner("彩彩正在思考中... ( > < )"):
            # A. 准备对话历史 (取最近 4 轮，帮助模型理解上下文)
            # 格式化历史记录： User: xxx \n Assistant: xxx
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

            # 3. 检索 (修改后的鲁棒版本)
            if target_files_str != "NONE" and "txt" in target_files_str:
                # 原始文件名列表，例如 ['B30.txt', 'D6.txt']
                raw_files = [f.strip() for f in target_files_str.split(",") if "txt" in f]

                # 构建“全方位拦截”的路径列表
                # 因为我们不知道当初建库时存的是 "B30.txt" 还是 "data_source/B30.txt" 还是 "data_source\B30.txt"
                target_sources = []
                for fname in raw_files:
                    target_sources.append(fname)  # 尝试1: 纯文件名
                    target_sources.append(f"data_source/{fname}")  # 尝试2: Linux/Mac 相对路径
                    target_sources.append(f"data_source\\{fname}")  # 尝试3: Windows 相对路径 (关键!)

                # 打印调试信息到侧边栏（帮你确认到底锁定了什么文件）
                with st.sidebar:
                    st.write("🔍 **Debug 路由信息**")
                    st.write(f"路由锁定: {raw_files}")
                    st.write(f"尝试匹配路径: {target_sources}")

                try:
                    # 使用扩大范围后的列表进行过滤
                    docs = vectordb.similarity_search(
                        search_query,
                        k=4,
                        filter={"source": {"$in": target_sources}}
                    )

                    # 只有当检索结果不为空时，才视为检索成功
                    if docs:
                        context_text = "\n\n".join([d.page_content for d in docs])
                        retrieved_flag = True

                        # 调试：显示检索到的真实来源，让你知道数据库里到底存了什么
                        with st.sidebar:
                            st.success(f"✅ 成功检索到 {len(docs)} 条片段")
                            sources_found = set([d.metadata.get('source') for d in docs])
                            st.write(f"真实数据来源: {sources_found}")

                except Exception as e:
                    st.sidebar.error(f"检索出错: {e}")
                    print(f"检索警告: {e}")

                    # C. 构建 Prompt (关键分支逻辑)

            if retrieved_flag:
                # === 模式 1: 严格 RAG 模式 (找到了资料) ===
                # 这种模式下，我们要求 AI 优先基于资料回答
                system_prompt = f"""
                你现在是《BanG Dream!》中的角色丸山彩（Maruyama Aya）。

                【任务】
                请结合【对话历史】和【相关回忆片段】回答粉丝的问题。

                【相关回忆片段】
                {context_text}

                【对话历史】
                {chat_history_str}

                【回复要求】
                1. 优先使用回忆片段中的信息。
                2. 如果用户在追问上文提到的内容（例如“那是什么意思？”），请结合对话历史进行解释。
                3. 保持丸山彩软萌、努力的语气，多用颜文字 (✨, 💦, ( > < ))。
                4. 第一人称是“彩”或“我”。
                """
            else:
                # === 模式 2: 闲聊/补救模式 (没找到资料) ===
                # 这种模式下，不仅仅是说“不知道”，而是尝试接话或解释上文
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
                        {"role": "user", "content": prompt}  # 这里其实 user prompt 已经在 history 里了，但为了触发再次发送
                    ],
                    temperature=0.7  # 稍微提高一点温度，让闲聊更自然
                )
                ai_reply = response.choices[0].message.content
            except Exception as e:
                ai_reply = f"呜呜...网络好像有点问题... (Error: {str(e)})"

        # 显示 AI 回复
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})