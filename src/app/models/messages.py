from typing import Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = "en"


class ImageChatMessage(BaseModel):
    message: Optional[str] = "I have a plant image to identify"
    session_id: Optional[str] = None
    language: Optional[str] = "en"