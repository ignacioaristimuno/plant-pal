from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json
from llama_index.core.llms import ChatMessage as LlamaChatMessage

from src.app.controller.state import get_or_create_session
from src.app.models.responses import ChatResponse
from src.app.models.messages import ChatMessage, ImageChatMessage
from src.app.controller.exceptions import (
    NonValidMessageException,
    NonValidSessionException,
    WorkflowExecutionException,
    ValidationException
)
from src.app.controller.validations import is_valid_message, is_valid_session_id, is_valid_image_file
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
        # Validate message
        message_validation = is_valid_message(chat_request.message)
        if not message_validation["is_valid"]:
            raise NonValidMessageException(message_validation["message"], chat_request.message)
        
        # Validate session_id if provided
        if chat_request.session_id:
            session_validation = is_valid_session_id(chat_request.session_id)
            if not session_validation["is_valid"]:
                raise NonValidSessionException(session_validation["message"], chat_request.session_id)
        
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

    except (NonValidMessageException, NonValidSessionException, ValidationException) as e:
        logger.warning(f"Validation error in chat endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowExecutionException as e:
        logger.error(f"Workflow execution error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise WorkflowExecutionException("Chat processing failed", workflow_error=e)


@router.post("/chat/image", response_model=ChatResponse)
async def chat_with_image(
    image: UploadFile = File(...),
    message: Optional[str] = Form("I have a plant image to identify"),
    session_id: Optional[str] = Form(None),
    language: Optional[str] = Form("en")
):
    try:
        # Validate message
        if message:
            message_validation = is_valid_message(message)
            if not message_validation["is_valid"]:
                raise NonValidMessageException(message_validation["message"], message)
        
        # Validate session_id if provided
        if session_id:
            session_validation = is_valid_session_id(session_id)
            if not session_validation["is_valid"]:
                raise NonValidSessionException(session_validation["message"], session_id)
        
        # Read image to get size for validation
        image_bytes = await image.read()
        
        # Validate image file
        image_validation = is_valid_image_file(image.content_type, len(image_bytes))
        if not image_validation["is_valid"]:
            raise ValidationException(image_validation["message"], field="image", value=image.filename)

        logger.info(f"Image chat request - message: {message[:50]}..., language: {language}")
        session_id, session_data = get_or_create_session(session_id)

        # Store image in session (already read above for validation)
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

    except (NonValidMessageException, NonValidSessionException, ValidationException) as e:
        logger.warning(f"Validation error in image chat endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowExecutionException as e:
        logger.error(f"Workflow execution error in image chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")
    except Exception as e:
        logger.error(f"Unexpected error in image chat endpoint: {e}")
        raise WorkflowExecutionException("Image chat processing failed", workflow_error=e)


