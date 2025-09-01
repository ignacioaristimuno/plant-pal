"""
Event classes for the Plant-Pal multi-agent workflow system.

This module defines all the workflow events used in the PlantPalWorkflow,
following the LlamaIndex workflow pattern with proper event-driven architecture.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, List

from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import (
    Event,
    StopEvent,
)


class OutputEvent(StopEvent):
    """Final event returned by the workflow with the complete response."""

    response: str = Field(description="Final response to the user")
    chat_history: List[ChatMessage] = Field(description="Updated conversation history")
    state: dict[str, Any] = Field(description="Final workflow state")


class StreamEvent(Event):
    """Event for streaming response chunks back to the user in real-time."""

    delta: str = Field(description="Incremental text chunk from LLM streaming")


class PlanEvent(Event):
    """Event emitted when a plan step is being executed."""

    step_info: str = Field(
        description="Information about the current step being executed"
    )


class DirectResponseEvent(Event):
    """Event emitted when the planner responds directly without using agents."""

    response: str = Field(description="Direct response from the planner")


# Plan modeling classes
class PlanStep(BaseModel):
    """Represents a single step in an execution plan."""

    agent_name: str = Field(description="Name of the agent to execute this step")
    agent_input: str = Field(description="Input message to send to the agent")


class Plan(BaseModel):
    """Complete execution plan containing multiple sequential steps."""

    steps: List[PlanStep] = Field(description="List of steps to execute in order")


class ExecuteEvent(Event):
    """Event triggered when a plan needs to be executed step by step."""

    plan: Plan = Field(description="The execution plan to run")
    chat_history: List[ChatMessage] = Field(description="Current conversation history")


# Additional workflow events for enhanced functionality
class AgentExecutionEvent(Event):
    """Event emitted when an individual agent starts executing."""

    agent_name: str = Field(description="Name of the agent being executed")
    input_message: str = Field(description="Input being sent to the agent")
    step_number: Optional[int] = Field(
        default=None, description="Step number if part of a plan"
    )


class AgentCompletionEvent(Event):
    """Event emitted when an agent completes its execution."""

    agent_name: str = Field(description="Name of the agent that completed")
    result: str = Field(description="Result returned by the agent")
    step_number: Optional[int] = Field(
        default=None, description="Step number if part of a plan"
    )
    success: bool = Field(
        default=True, description="Whether the execution was successful"
    )
