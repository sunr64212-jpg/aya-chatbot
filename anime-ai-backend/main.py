import os
import sys
import glob
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 路径与环境设置
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 加载环境变量 (.env)
env_path = os.path.join(current_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# 配置 DeepSeek 客户端
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(
    api_key=DEEPSEEK_KEY,
    base_url="https://api.deepseek.com"
)

# 初始化 FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 数据模型 ===
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


# ==================== 资源初始化 ====================
print("🔄 正在初始化系统 (最终工程版)...")

# 1. 智能配置路径
# 获取 main.py 所在的文件夹
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录 (chatbot1)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 修正：指向上一级的 data_source
DATA_SOURCE_DIR = os.path.join(PROJECT_ROOT, "data_source")
# 指向当前目录下的 chroma_db
DB_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")

INDEX_MAP_PATH = os.path.join(DB_PERSIST_DIR, "index_map.txt")
GLOSSARY_PATH = os.path.join(DATA_SOURCE_DIR, "00_glossary.txt")

# 2. 加载 Embedding 模型 (必须与构建时一致)
# 推荐: shibing624/text2vec-base-chinese
EMBEDDING_MODEL_NAME = "shibing624/text2vec-base-chinese"
try:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print(f"✅ Embedding 模型已加载: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    sys.exit(1)

# 3. 加载向量数据库 (从硬盘读取)
vector_db = None
if os.path.exists(DB_PERSIST_DIR):
    try:
        print(f"📂 正在挂载向量数据库: {DB_PERSIST_DIR}")
        vector_db = Chroma(
            persist_directory=DB_PERSIST_DIR,
            embedding_function=embeddings,
            collection_name="aya_memory_v3"  # 必须与 build_vector_db.py 中的名称一致
        )
        print("✅ 知识库挂载成功！")
    except Exception as e:
        print(f"❌ 数据库挂载失败: {e}")
        print("💡 请先运行 'python build_vector_db.py'")
else:
    print(f"⚠️ 警告: 未找到数据库目录 {DB_PERSIST_DIR}")
    print("💡 请务必先运行 'python build_vector_db.py' 构建数据！")

# 4. 加载动态剧情索引 (用于 Router)
STORY_INDEX_CONTEXT = ""
if os.path.exists(INDEX_MAP_PATH):
    with open(INDEX_MAP_PATH, 'r', encoding='utf-8') as f:
        STORY_INDEX_CONTEXT = f.read()
    print(f"🗺️  已加载动态剧情索引: {len(STORY_INDEX_CONTEXT.splitlines())} 条记录")
else:
    print("⚠️ 严重警告: 未找到 index_map.txt！Router 将无法正确锁定文件。")
    print("💡 请重新运行 build_vector_db.py 生成索引。")

# 5. 加载世界观字典 (用于 Rewrite)
WORLD_VIEW_CONTEXT = ""
if os.path.exists(GLOSSARY_PATH):
    with open(GLOSSARY_PATH, 'r', encoding='utf-8') as f:
        WORLD_VIEW_CONTEXT = f.read()
    print("📚 已加载世界观字典")
else:
    print("⚠️ 未找到 00_glossary.txt，将使用通用重写模式")


# ==================== 🧠 核心 1：意图理解与重写 ====================
def rewrite_query(user_msg: str, history: List[ChatMessage]):
    """利用对话历史和字典，将用户口语转换为精准搜索词"""
    if not history and not WORLD_VIEW_CONTEXT:
        return user_msg

    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in history[-4:]])

    rewrite_prompt = f"""
    你是一名《BanG Dream!》剧情搜索专家。
    请利用下方的【世界观实体字典】，将用户口语化的问题转换为准确的搜索语句。

    【世界观实体字典】
    {WORLD_VIEW_CONTEXT}

    【任务】
    1. 补全省略的主语。
    2. 将昵称/黑话转换为标准全名（如"ksm" -> "户山香澄"）。
    3. 保持问题原意，不要回答。

    【对话历史】
    {history_text}
    【用户新问题】
    {user_msg}

    【输出】
    仅输出重写后的句子。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个精准的查询重写器。"},
                {"role": "user", "content": rewrite_prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Rewrite Error: {e}")
        return user_msg


# ==================== 🧠 核心 2：剧情范围锁定 (Router - 动态版) ====================
def detect_story_scope(search_query: str):
    """
    根据 index_map.txt 动态判断需要检索哪些文件。
    """
    if not STORY_INDEX_CONTEXT:
        return "NONE"

    scope_prompt = f"""
    你是一个《BanG Dream!》Pastel*Palettes 乐队的剧情导航员。
    你需要根据用户问题，从下方的【文件索引】中选出 **1到3个** 最相关的档案文件。

    【文件索引】
    {STORY_INDEX_CONTEXT}

    【用户问题】
    {search_query}

    【任务】
    1. 分析问题涉及的角色（如提到"日菜"）或事件（如提到"海边打工"）。
    2. 对照【文件索引】中的描述，找到最匹配的文件名。
    3. 输出文件名，用英文逗号分隔。
    4. 如果完全无法确定或没有对应文件，输出 "NONE"。

    【示例】
    用户: "日菜和纱夜怎么和好的" -> 输出: B2.txt,B7.txt
    用户: "彩的自我介绍" -> 输出: B0.txt
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "只输出文件名，用逗号分隔，无多余解释。"},
                {"role": "user", "content": scope_prompt}
            ],
            temperature=0.0
        )
        file_scope = response.choices[0].message.content.strip()

        # 简单清洗
        if "txt" not in file_scope and file_scope != "NONE":
            # 尝试提取可能的文件名
            import re
            files = re.findall(r'[A-Z]\d+\.txt', file_scope)
            if files:
                return ",".join(files)
            return "NONE"

        return file_scope

    except Exception as e:
        print(f"Router Error: {e}")
        return "NONE"


# ==================== 核心逻辑：生成回复 (RAG) ====================
def conversational_rag(user_query: str, history: List[ChatMessage]):
    # 1. 意图理解
    print(f"\n🤔 用户原话: {user_query}")
    search_query = rewrite_query(user_query, history)
    print(f"🎯 检索用语: {search_query}")

    # 2. 剧情范围锁定
    target_files_str = detect_story_scope(search_query)
    print(f"🧭 锁定范围: {target_files_str}")

    context_text = ""

    # 3. 精准检索
    if vector_db and target_files_str != "NONE":
        try:
            target_files = [f.strip() for f in target_files_str.split(",") if "txt" in f]

            if target_files:
                # 使用 metadata 过滤器只检索相关文件
                search_kwargs = {
                    "k": 6,
                    "filter": {"source": {"$in": target_files}}
                }

                docs = vector_db.similarity_search(search_query, **search_kwargs)

                print("--- 🕵️‍♀️ 最终检索结果 ---")
                for i, d in enumerate(docs):
                    src = d.metadata.get('source')
                    print(f"[{i + 1}] {src} | {d.page_content[:20]}...")
                    context_text += f"{d.page_content}\n\n"
                print("-----------------------")
        except Exception as e:
            print(f"检索出错: {e}")

    # 4. 防幻觉兜底
    if not context_text:
        print("⚠️ 未检索到信息，触发兜底回复。")
        return "那个……彩有点记不太清了( > < ) 或者是彩还没经历过这件事？\n如果可以的话，能告诉我更多细节吗？💦"

    # 5. 生成回复
    final_prompt = f"""
    你现在是《BanG Dream!》中的角色丸山彩（Maruyama Aya）。
    请完全沉浸在这个角色中，**严格仅根据下方的【相关回忆片段】**来回答粉丝的问题。

    【🚫 绝对禁令】
    1. **严禁使用回忆片段以外的任何外部知识**。即使你知道答案，但片段里没写，就当作不知道。
    2. 如果片段内容不足以回答问题，请诚实地说“记不清了”。

    【相关回忆片段】
    {context_text}

    【当前对话】
    粉丝：{user_query}

    【回复要求】
    - 基于片段内容，用丸山彩软萌、努力的口吻回答。
    - 多使用颜文字 (✨, 💦, ( > < ))。
    - 第一人称是“彩”或“我”。

    请作为丸山彩回复：
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return "呜呜...脑子突然一片空白...彩、彩是不是又搞砸了？( > < )"


# ==================== API 接口 ====================
@app.post("/chat")
async def chat(request: ChatRequest):
    response_text = conversational_rag(request.message, request.history)

    # 简单的情感分析（用于前端Live2D动作）
    emotion = "idle"
    check_text = response_text
    if any(k in check_text for k in ["呜", "难过", "对不起", "紧张", "哭", "💦", "搞砸"]):
        emotion = "cry"
    elif any(k in check_text for k in ["开心", "嘿嘿", "成功", "谢谢", "✨", "缤纷彩"]):
        emotion = "smile"
    elif any(k in check_text for k in ["诶", "那个", "害羞", "脸红", "///", "喜欢"]):
        emotion = "shy"
    elif any(k in check_text for k in ["生气", "过分", "讨厌"]):
        emotion = "anger"

    return {"text": response_text, "emotion": emotion}


if __name__ == "__main__":
    import uvicorn

    print("🚀 启动后端服务: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)