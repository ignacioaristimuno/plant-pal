from typing import List, Dict

from llama_index.core.workflow import Context


class SessionData:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.conversation_history: List[Dict[str, str]] = []
