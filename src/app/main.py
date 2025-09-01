import asyncio
import base64
import uuid
from typing import Dict, Optional, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core.agent.workflow import (
    AgentStream,
    AgentOutput,
    ToolCallResult,
    ToolCall,
)
from llama_index.core.workflow import Context
from pydantic import BaseModel

from src.workflows.workflow import agent_workflow
from src.settings.logger import custom_logger


# Set up logger
logger = custom_logger(__name__)


# Create FastAPI app
app = FastAPI(title="PlantPal Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define classes
class SessionData:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.conversation_history: List[Dict[str, str]] = []

sessions: Dict[str, SessionData] = {}


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ImageChatMessage(BaseModel):
    session_id: Optional[str] = None


# Get or create session
def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, SessionData]:
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {session_id}")

    elif session_id and (session_id in sessions):
        logger.info(f"Session {session_id} already exists, returning existing session")
        return session_id, sessions[session_id]
    
    ctx = Context(agent_workflow)
    session_data = SessionData(ctx)
    sessions[session_id] = session_data
    
    logger.info(f"Running new session: {session_id}")
    return session_id, session_data


# Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatMessage):
    try:
        session_id, session_data = get_or_create_session(chat_request.session_id)
        
        # Build context message with conversation history
        context_message = ""
        if session_data.conversation_history:
            context_message = "Previous conversation context:\n"
            for msg in session_data.conversation_history[-5:]:  # Last 5 messages for context
                context_message += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
            context_message += f"Current question: {chat_request.message}"
        else:
            context_message = chat_request.message
        
        handler = agent_workflow.run(context_message, ctx=session_data.ctx)
        
        response_content = ""
        current_agent = None
        
        async for event in handler.stream_events():
            if (
                hasattr(event, "current_agent_name")
                and event.current_agent_name != current_agent
            ):
                current_agent = event.current_agent_name
                logger.info(f"Agent switched to: {current_agent}")
            
            if isinstance(event, AgentStream):
                if event.delta:
                    response_content += event.delta
            elif isinstance(event, AgentOutput):
                if event.response.content and not response_content:
                    response_content = event.response.content
            elif isinstance(event, ToolCallResult):
                logger.info(f"Tool {event.tool_name} executed")
            elif isinstance(event, ToolCall):
                logger.info(f"Calling tool: {event.tool_name}")
        
        final_response = await handler
        if not response_content and final_response:
            response_content = str(final_response)
        
        # Store conversation in history
        session_data.conversation_history.append({
            "user": chat_request.message,
            "assistant": response_content
        })
        
        return ChatResponse(response=response_content, session_id=session_id)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/image", response_model=ChatResponse)
async def chat_with_image(
    image: UploadFile = File(...),
    session_id: Optional[str] = None
):
    try:
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        session_id, session_data = get_or_create_session(session_id)
        
        image_bytes = await image.read()
        await session_data.ctx.store.set("image_bytes", image_bytes)
        
        logger.info(f"Image stored in session {session_id}: {len(image_bytes)} bytes")
        
        # Build context message with conversation history
        context_message = ""
        if session_data.conversation_history:
            context_message = "Previous conversation context:\n"
            for msg in session_data.conversation_history[-5:]:  # Last 5 messages for context
                context_message += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
            context_message += "Current request: I have a plant image to identify"
        else:
            context_message = "I have a plant image to identify"
        
        handler = agent_workflow.run(context_message, ctx=session_data.ctx)
        
        response_content = ""
        current_agent = None
        
        async for event in handler.stream_events():
            if (
                hasattr(event, "current_agent_name")
                and event.current_agent_name != current_agent
            ):
                current_agent = event.current_agent_name
                logger.info(f"Agent switched to: {current_agent}")
            
            if isinstance(event, AgentStream):
                if event.delta:
                    response_content += event.delta
            elif isinstance(event, AgentOutput):
                if event.response.content and not response_content:
                    response_content = event.response.content
            elif isinstance(event, ToolCallResult):
                logger.info(f"Tool {event.tool_name} executed")
            elif isinstance(event, ToolCall):
                logger.info(f"Calling tool: {event.tool_name}")
        
        final_response = await handler
        if not response_content and final_response:
            response_content = str(final_response)
        
        # Store conversation in history
        session_data.conversation_history.append({
            "user": "Uploaded plant image for identification",
            "assistant": response_content
        })
        
        return ChatResponse(response=response_content, session_id=session_id)
    
    except Exception as e:
        logger.error(f"Error in image chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/status")
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


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    logger.info(f"Deleted session: {session_id}")
    
    return {"message": "Session deleted successfully"}


@app.get("/sessions")
async def list_sessions():
    return {"sessions": list(sessions.keys())}


@app.get("/")
async def root():
    return {"message": "PlantPal Chat API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)