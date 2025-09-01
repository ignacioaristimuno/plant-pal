from fastapi import APIRouter, HTTPException

from src.app.controller.state import sessions
from src.settings.logger import custom_logger


# Initialize logger
logger = custom_logger("Sessions Router")

# Initialize router
router = APIRouter(tags=["Sessions"])


# Endpoints
@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    store_data = {}
    try:
        image_bytes = await session_data.ctx.store.get("image_bytes")
        if image_bytes:
            store_data["has_image"] = True
            store_data["image_size"] = len(image_bytes)
    except:
        store_data["has_image"] = False
    
    return {
        "session_id": session_id,
        "active": True,
        "conversation_history_length": len(session_data.conversation_history),
        "store_data": store_data
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    logger.info(f"Deleted session: {session_id}")
    
    return {"message": "Session deleted successfully"}


@router.get("/sessions")
async def list_sessions():
    return {"sessions": list(sessions.keys())}
