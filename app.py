import streamlit as st

# 引入你之前的后端逻辑
# from backend import Chatbot (假设你封装了类) 或者直接写逻辑

# 设置网页标题和图标
st.set_page_config(page_title="丸山彩 AI Chat", page_icon="🌸")

st.title("🌸 丸山彩 AI Chatbot 🌸")
st.write("我是 Pastel*Palettes 的丸山彩！请多指教！( > < )")

# 初始化聊天历史 (Streamlit 特性: 页面刷新需保持状态)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示之前的聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 获取用户输入
if prompt := st.chat_input("和彩彩说点什么吧..."):
    # 1. 显示用户的话
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. 调用你的 AI 逻辑 (这里是伪代码，你需要替换成你的真实逻辑)
    # response = your_ai_function(prompt)
    # 假设 response 是 "嘿嘿，我会加油的！"

    # --- 关键：在这里接入你之前的 RAG 搜索和 LLM 调用逻辑 ---
    # context = search_vector_db(prompt)
    # response = call_llm(prompt, context)

    # 3. 显示 AI 的回复
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})