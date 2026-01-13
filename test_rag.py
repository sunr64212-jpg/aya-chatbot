from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 配置 (必须和构建时一致)
DB_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"


def test_retrieval():
    print("🚀 正在加载数据库...")
    # 加载本地嵌入模型
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 加载向量数据库
    vector_store = Chroma(
        persist_directory=DB_PERSIST_DIR,
        embedding_function=embeddings
    )

    # 测试问题
    questions = [
        "你是谁？",
        "你觉得千圣怎么样？",
        "你之前的梦想是什么？"
    ]

    for q in questions:
        print(f"\n❓ 问题: {q}")
        # 搜索最相似的 2 条记忆
        docs = vector_store.similarity_search(q, k=2)

        if not docs:
            print("❌ 未找到相关记忆")
            continue

        for i, doc in enumerate(docs):
            print(f"   📄 [记忆 {i + 1}] (来源: {doc.metadata['source']})")
            # 只打印前 50 个字预览
            content_preview = doc.page_content.replace('\n', ' ')[:50]
            print(f"      内容: {content_preview}...")


if __name__ == "__main__":
    test_retrieval()