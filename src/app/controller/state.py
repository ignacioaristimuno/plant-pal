"""State management for the PlantPal API."""

import uuid
from typing import Dict, Optional

from src.app.models.session import SessionData
from llama_index.core.llms import ChatMessage

from src.settings.logger import custom_logger
from src.workflows.workflow import PlantPalWorkflow


# Set up logger
logger = custom_logger("State Controller")

# Global planner workflow instance
workflow = PlantPalWorkflow()

# Sessions
sessions: Dict[str, SessionData] = {}


# Get or create session
def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, SessionData]:
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {session_id}")

    elif session_id and (session_id in sessions):
        logger.info(f"Session {session_id} already exists, returning existing session")
        return session_id, sessions[session_id]

    # Create a new workflow instance for each session to avoid state conflicts
    session_workflow = PlantPalWorkflow()

    session_data = SessionData(
        session_id=session_id, chat_history=[], workflow=session_workflow
    )
    sessions[session_id] = session_data

    logger.info(f"Running new session: {session_id}")
    return session_id, session_data
