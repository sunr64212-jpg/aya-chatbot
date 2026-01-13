# memory.py
from collections import defaultdict

# 存储结构： session_id -> [message_list]
# 限制历史记录长度，防止 Token 消耗过大
MAX_HISTORY_LEN = 20

class MemoryManager:
    def __init__(self):
        self.conversations = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str):
        self.conversations[session_id].append({"role": role, "content": content})
        # 保持记忆在限制范围内（滑动窗口）
        if len(self.conversations[session_id]) > MAX_HISTORY_LEN:
            self.conversations[session_id] = self.conversations[session_id][-MAX_HISTORY_LEN:]

    def get_history(self, session_id: str):
        return self.conversations.get(session_id, [])

    def clear_history(self, session_id: str):
        if session_id in self.conversations:
            del self.conversations[session_id]

# 实例化一个全局记忆管理器
memory_store = MemoryManager()