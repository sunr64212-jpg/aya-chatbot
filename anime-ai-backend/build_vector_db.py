import os
import glob
import shutil
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ================= 配置区 =================
# 获取当前脚本所在目录 (即 anime-ai-backend)
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 获取项目根目录 (即 chatbot1，向上一级)
PROJECT_ROOT = os.path.dirname(CURRENT_SCRIPT_DIR)

# 修正：指向隔壁的 data_source 目录
DATA_SOURCE_DIR = os.path.join(PROJECT_ROOT, "data_source")

# 数据库依然存在当前脚本目录下即可
DB_PERSIST_DIR = os.path.join(CURRENT_SCRIPT_DIR, "chroma_db")
INDEX_MAP_FILE = os.path.join(DB_PERSIST_DIR, "index_map.txt")

EMBEDDING_MODEL_NAME = "shibing624/text2vec-base-chinese"


# =========================================

def extract_file_summary(file_path):
    """
    从文本文件头部提取关键信息，用于生成路由索引。
    读取 [关键人物], [核心事件] 或 [简介] 等标签。
    """
    filename = os.path.basename(file_path)
    summary = f"- {filename}: "

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 只读前 10 行找标签
            head_lines = [next(f) for _ in range(10)]

        tags = []
        for line in head_lines:
            line = line.strip()
            # 提取中括号内的信息作为简介
            if line.startswith("[档案类型:") or line.startswith("[剧情阶段:"):
                tags.append(line.split(":", 1)[1].strip(" ]"))
            elif line.startswith("[关键人物:") or line.startswith("[核心事件:"):
                content = line.split(":", 1)[1].strip(" ]")
                # 截取过长的描述
                if len(content) > 20: content = content[:20] + "..."
                tags.append(content)

        if tags:
            summary += " / ".join(tags)
        else:
            # 如果没有标签，使用通用描述（针对 00_glossary 等）
            if "glossary" in filename:
                summary += "世界观实体字典 / 角色昵称对照表"
            else:
                summary += "剧情档案"

    except Exception as e:
        summary += "未知档案"

    return summary


def process_memory_file(file_path):
    # ... (保持原本的切分逻辑不变，为了节省篇幅省略) ...
    # 这里直接复制你之前确认过的 process_memory_file 函数内容
    filename = os.path.basename(file_path)
    try:
        loader = TextLoader(file_path, encoding='utf-8')
        raw_docs = loader.load()
    except Exception:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600, chunk_overlap=150,
        separators=["\n\n", "\n", "【", "。", "！", "？"]
    )
    docs = text_splitter.split_documents(raw_docs)

    final_docs = []
    for doc in docs:
        content = doc.page_content.strip()
        if not content: continue
        doc.page_content = f"【记忆来源：{filename}】\n{content}"
        doc.metadata = {"source": filename, "category": "aya_memory"}
        final_docs.append(doc)
    return final_docs


def build_database():
    # 1. 清理旧数据
    if os.path.exists(DB_PERSIST_DIR):
        print(f"🗑️  正在清理旧数据库: {DB_PERSIST_DIR}")
        shutil.rmtree(DB_PERSIST_DIR)

    # 必须重新创建目录以存放 index_map.txt
    os.makedirs(DB_PERSIST_DIR, exist_ok=True)

    print(f"📂 开始扫描记忆库: {DATA_SOURCE_DIR} ...")
    txt_files = glob.glob(os.path.join(DATA_SOURCE_DIR, "*.txt"))

    if not txt_files:
        print("❌ 目录为空")
        return

    all_docs = []
    index_lines = []  # 📍 用于存储路由表内容

    # 2. 遍历处理
    for txt_file in txt_files:
        filename = os.path.basename(txt_file)

        # A. 生成索引条目
        summary_line = extract_file_summary(txt_file)
        index_lines.append(summary_line)

        # B. 生成向量数据
        docs = process_memory_file(txt_file)
        if docs:
            all_docs.extend(docs)
            print(f"   📖 处理: {filename} -> {len(docs)} 片段 | 索引: {summary_line}")

    # 3. 保存路由索引表到 chroma_db 文件夹
    with open(INDEX_MAP_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(index_lines)))
    print(f"📍 路由索引表已生成: {INDEX_MAP_FILE}")

    # 4. 向量化存库
    print(f"\n🚀 正在向量化 {len(all_docs)} 条数据...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    Chroma.from_documents(
        documents=all_docs,
        embedding=embeddings,
        persist_directory=DB_PERSIST_DIR,
        collection_name="aya_memory_v3"
    )

    print(f"✅ 构建完成！数据与索引均已保存至 {DB_PERSIST_DIR}")


if __name__ == "__main__":
    build_database()