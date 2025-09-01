from typing import Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ImageChatMessage(BaseModel):
    session_id: Optional[str] = None