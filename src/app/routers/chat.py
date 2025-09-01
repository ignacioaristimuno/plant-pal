from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json
from llama_index.core.llms import ChatMessage as LlamaChatMessage

from src.app.controller.state import get_or_create_session
from src.app.models.responses import ChatResponse
from src.app.models.messages import ChatMessage, ImageChatMessage
from src.settings.logger import custom_logger
from src.workflows.events import (
    OutputEvent,
    StreamEvent,
    PlanEvent,
    DirectResponseEvent,
    AgentExecutionEvent,
    AgentCompletionEvent,
)


# Initialize logger
logger = custom_logger("Chat Router")

# Initialize router
router = APIRouter(tags=["Chat"])


# Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatMessage):
    try:
        print(f"DEBUG: Chat endpoint hit with message: {chat_request.message[:50]}...")
        logger.info(f"Received chat request: {chat_request.message[:50]}..., language: {chat_request.language}")
        session_id, session_data = get_or_create_session(chat_request.session_id)
        print(f"DEBUG: Using session: {session_id}")
        logger.info(f"Using session: {session_id}")

        # Create input event for the planner workflow  
        if not isinstance(session_data.state, dict):
            logger.warning(f"Session state is not dict, resetting to empty dict")
            session_data.state = {}
            
        state = session_data.state.copy()
        if session_data.image_bytes:
            state["image_bytes"] = session_data.image_bytes
        state["language"] = chat_request.language

        # Run the planner workflow with direct parameters
        handler = session_data.workflow.run(
            user_msg=chat_request.message,
            chat_history=session_data.chat_history.copy() if isinstance(session_data.chat_history, list) else [],
            state=state if state else {}
        )

        response_content = ""
        plan_steps = []
        agent_executions = []

        async for event in handler.stream_events():
            if isinstance(event, StreamEvent):
                # Only use stream events for direct responses, not for plan XML
                if event.delta and not event.delta.strip().startswith('<plan'):
                    response_content += event.delta
            elif isinstance(event, PlanEvent):
                plan_steps.append(event.step_info)
                logger.info(f"Plan step: {event.step_info}")
            elif isinstance(event, DirectResponseEvent):
                response_content = event.response
                logger.info("Direct response from planner")
            elif isinstance(event, AgentExecutionEvent):
                agent_executions.append(f"Starting {event.agent_name}")
                logger.info(f"Agent execution: {event.agent_name}")
            elif isinstance(event, AgentCompletionEvent):
                status = "completed" if event.success else "failed"
                agent_executions.append(f"{event.agent_name} {status}")
                logger.info(f"Agent {event.agent_name} {status}")

        # Get final result - this contains the actual agent response
        result = await handler
        if isinstance(result, OutputEvent):
            # Always use the final result response, which contains the agent's actual output
            response_content = result.response
            
            # Update session data
            session_data.chat_history = result.chat_history if isinstance(result.chat_history, list) else []
            session_data.state = result.state if isinstance(result.state, dict) else {}

        if not response_content:
            response_content = "I apologize, but I wasn't able to process your request properly."

        return ChatResponse(response=response_content, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/image", response_model=ChatResponse)
async def chat_with_image(
    image: UploadFile = File(...),
    message: Optional[str] = Form("I have a plant image to identify"),
    session_id: Optional[str] = Form(None),
    language: Optional[str] = Form("en")
):
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        logger.info(f"Image chat request - message: {message[:50]}..., language: {language}")
        session_id, session_data = get_or_create_session(session_id)

        # Store image in session
        image_bytes = await image.read()
        session_data.image_bytes = image_bytes
        
        logger.info(f"Image stored in session {session_id}: {len(image_bytes)} bytes")

        # Create input event with image data and language - store in workflow context
        if not isinstance(session_data.state, dict):
            logger.warning(f"Session state is not dict, resetting to empty dict")
            session_data.state = {}
            
        state = session_data.state.copy()
        state["image_bytes"] = image_bytes
        state["language"] = language

        # Run the planner workflow with direct parameters
        handler = session_data.workflow.run(
            user_msg=message,
            chat_history=session_data.chat_history.copy() if isinstance(session_data.chat_history, list) else [],
            state=state
        )

        response_content = ""
        plan_steps = []
        agent_executions = []

        async for event in handler.stream_events():
            if isinstance(event, StreamEvent):
                # Only use stream events for direct responses, not for plan XML
                if event.delta and not event.delta.strip().startswith('<plan'):
                    response_content += event.delta
            elif isinstance(event, PlanEvent):
                plan_steps.append(event.step_info)
                logger.info(f"Plan step: {event.step_info}")
            elif isinstance(event, DirectResponseEvent):
                response_content = event.response
                logger.info("Direct response from planner")
            elif isinstance(event, AgentExecutionEvent):
                agent_executions.append(f"Starting {event.agent_name}")
                logger.info(f"Agent execution: {event.agent_name}")
            elif isinstance(event, AgentCompletionEvent):
                status = "completed" if event.success else "failed"
                agent_executions.append(f"{event.agent_name} {status}")
                logger.info(f"Agent {event.agent_name} {status}")

        # Get final result - this contains the actual agent response
        result = await handler
        if isinstance(result, OutputEvent):
            # Always use the final result response, which contains the agent's actual output
            response_content = result.response
            
            # Update session data
            session_data.chat_history = result.chat_history if isinstance(result.chat_history, list) else []
            session_data.state = result.state if isinstance(result.state, dict) else {}

        if not response_content:
            response_content = "I apologize, but I wasn't able to process your image properly."

        return ChatResponse(response=response_content, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in image chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(chat_request: ChatMessage):
    """Stream chat responses with real-time workflow events."""
    try:
        logger.info(f"Streaming chat request: {chat_request.message[:50]}..., language: {chat_request.language}")
        session_id, session_data = get_or_create_session(chat_request.session_id)
        
        async def generate_stream():
            try:
                # Create input event for the planner workflow
                state = session_data.state.copy() if isinstance(session_data.state, dict) else {}
                if session_data.image_bytes:
                    state["image_bytes"] = session_data.image_bytes
                state["language"] = chat_request.language

                # Run the planner workflow with direct parameters
                handler = session_data.workflow.run(
                    user_msg=chat_request.message,
                    chat_history=session_data.chat_history.copy() if isinstance(session_data.chat_history, list) else [],
                    state=state if state else {}
                )

                response_content = ""
                
                async for event in handler.stream_events():
                    if isinstance(event, StreamEvent):
                        if event.delta:
                            response_content += event.delta
                            yield f"data: {json.dumps({'type': 'stream', 'content': event.delta})}\n\n"
                    elif isinstance(event, PlanEvent):
                        yield f"data: {json.dumps({'type': 'plan', 'content': event.step_info})}\n\n"
                    elif isinstance(event, DirectResponseEvent):
                        response_content = event.response
                        yield f"data: {json.dumps({'type': 'direct_response', 'content': event.response})}\n\n"
                    elif isinstance(event, AgentExecutionEvent):
                        yield f"data: {json.dumps({'type': 'agent_start', 'agent': event.agent_name, 'message': event.input_message})}\n\n"
                    elif isinstance(event, AgentCompletionEvent):
                        status = "success" if event.success else "error"
                        yield f"data: {json.dumps({'type': 'agent_complete', 'agent': event.agent_name, 'status': status})}\n\n"

                # Get final result
                result = await handler
                if isinstance(result, OutputEvent):
                    if not response_content:
                        response_content = result.response
                    
                    # Update session data
                    session_data.chat_history = result.chat_history
                    session_data.state = result.state if isinstance(result.state, dict) else {}

                # Send final response
                yield f"data: {json.dumps({'type': 'final', 'content': response_content, 'session_id': session_id})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Error in stream generation: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
