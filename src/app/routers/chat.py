from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from llama_index.core.agent.workflow import (
    AgentStream,
    AgentOutput,
    ToolCallResult,
    ToolCall,
)


from src.app.controller.state import get_or_create_session
from src.app.models.responses import ChatResponse
from src.app.models.messages import ChatMessage
from src.settings.logger import custom_logger
from src.workflows.workflow import agent_workflow


# Initialize logger
logger = custom_logger("Chat Router")

# Initialize router
router = APIRouter(tags=["Chat"])


# Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatMessage):
    try:
        session_id, session_data = get_or_create_session(chat_request.session_id)

        # Build context message with conversation history
        context_message = ""
        if session_data.conversation_history:
            context_message = "Previous conversation context:\n"
            for msg in session_data.conversation_history[
                -5:
            ]:  # Last 5 messages for context
                context_message += (
                    f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
                )
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
        session_data.conversation_history.append(
            {"user": chat_request.message, "assistant": response_content}
        )

        return ChatResponse(response=response_content, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/image", response_model=ChatResponse)
async def chat_with_image(
    image: UploadFile = File(...), session_id: Optional[str] = None
):
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        session_id, session_data = get_or_create_session(session_id)

        image_bytes = await image.read()
        await session_data.ctx.store.set("image_bytes", image_bytes)

        logger.info(f"Image stored in session {session_id}: {len(image_bytes)} bytes")

        # Build context message with conversation history
        context_message = ""
        if session_data.conversation_history:
            context_message = "Previous conversation context:\n"
            for msg in session_data.conversation_history[
                -5:
            ]:  # Last 5 messages for context
                context_message += (
                    f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
                )
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
        session_data.conversation_history.append(
            {
                "user": "Uploaded plant image for identification",
                "assistant": response_content,
            }
        )

        return ChatResponse(response=response_content, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in image chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
