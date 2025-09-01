from typing import List, Any, Dict, Optional
from llama_index.core.llms import ChatMessage
from src.workflows.workflow import PlantPalWorkflow


class SessionData:
    def __init__(
        self,
        session_id: str,
        chat_history: List[ChatMessage],
        workflow: PlantPalWorkflow,
    ):
        self.session_id = session_id
        self.chat_history = chat_history
        self.workflow = workflow
        self.state: Dict[str, Any] = {}
        self.image_bytes: Optional[bytes] = None
