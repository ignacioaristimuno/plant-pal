from fastapi import APIRouter, HTTPException

from src.app.controller.state import sessions
from src.app.controller.exceptions import NonValidSessionException, ValidationException
from src.app.controller.validations import is_valid_session_id
from src.settings.logger import custom_logger


# Initialize logger
logger = custom_logger("Sessions Router")

# Initialize router
router = APIRouter(tags=["Sessions"])


# Endpoints
@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    try:
        # Validate session_id format
        session_validation = is_valid_session_id(session_id)
        if not session_validation["is_valid"]:
            raise NonValidSessionException(session_validation["message"], session_id)
        
        if session_id not in sessions:
            raise NonValidSessionException("Session not found", session_id)
        
        session_data = sessions[session_id]
        
        # Check image data stored directly on session object
        store_data = {}
        if hasattr(session_data, 'image_bytes') and session_data.image_bytes:
            store_data["has_image"] = True
            store_data["image_size"] = len(session_data.image_bytes)
        else:
            store_data["has_image"] = False
        
        # Check chat history for memory info
        memory_info = {}
        if hasattr(session_data, 'chat_history') and session_data.chat_history:
            memory_info["has_memory"] = True
            memory_info["message_count"] = len(session_data.chat_history)
        else:
            memory_info["has_memory"] = False
        
        return {
            "session_id": session_id,
            "active": True,
            "memory_info": memory_info,
            "store_data": store_data
        }
    
    except (NonValidSessionException, ValidationException) as e:
        logger.warning(f"Validation error in get_session_status: {e}")
        raise HTTPException(status_code=400 if isinstance(e, ValidationException) else 404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_session_status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        # Validate session_id format
        session_validation = is_valid_session_id(session_id)
        if not session_validation["is_valid"]:
            raise NonValidSessionException(session_validation["message"], session_id)
        
        if session_id not in sessions:
            raise NonValidSessionException("Session not found", session_id)
        
        del sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        
        return {"message": "Session deleted successfully"}
    
    except (NonValidSessionException, ValidationException) as e:
        logger.warning(f"Validation error in delete_session: {e}")
        raise HTTPException(status_code=400 if isinstance(e, ValidationException) else 404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in delete_session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions")
async def list_sessions():
    try:
        return {"sessions": list(sessions.keys())}
    except Exception as e:
        logger.error(f"Unexpected error in list_sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
