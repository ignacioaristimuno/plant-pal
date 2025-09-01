import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import (
    Context,
    StartEvent,
    Workflow,
    step,
)
from llama_index.core.agent import FunctionAgent

from src.llm.client import llm_client, vlm_client
from src.settings.logger import custom_logger
from src.workflows.agents import (
    plant_recognition_agent,
    plant_care_agent,
)
from src.workflows.events import (
    OutputEvent,
    StreamEvent,
    PlanEvent,
    DirectResponseEvent,
    ExecuteEvent,
    AgentExecutionEvent,
    AgentCompletionEvent,
    Plan,
    PlanStep,
)
from src.workflows.prompts import PLANNER_PROMPT


# Initialize logger
logger = custom_logger("PlantPalWorkflow")


# Workflow
class PlantPalWorkflow(Workflow):
    llm = llm_client
    vlm = vlm_client
    agents: dict[str, FunctionAgent] = {
        plant_recognition_agent.name: plant_recognition_agent,
        plant_care_agent.name: plant_care_agent,
    }

    @step
    async def plan(self, ctx: Context, ev: StartEvent) -> ExecuteEvent | OutputEvent:
        # Get user message from the StartEvent (this will be passed by workflow.run())
        user_msg_text = getattr(ev, "user_msg", "") or ""
        chat_history = getattr(ev, "chat_history", []) or []
        initial_state = getattr(ev, "state", {}) or {}

        # Set initial state, ensure it's always a dict
        if isinstance(initial_state, dict):
            await ctx.store.set("state", initial_state)
            # If image_bytes is in the initial state, store it separately for agent access
            if "image_bytes" in initial_state:
                await ctx.store.set("image_bytes", initial_state["image_bytes"])
        elif not await ctx.store.get("state"):
            await ctx.store.set("state", {})

        # Ensure chat_history is a list
        if not isinstance(chat_history, list):
            chat_history = []

        if user_msg_text:
            user_msg = ChatMessage(
                role="user",
                content=user_msg_text,
            )
            chat_history.append(user_msg)

        # Inject the system prompt with state and available agents
        state = await ctx.store.get("state") or {}
        language = state.get("language", "en")

        # Create language instruction based on the language parameter
        if language and language != "en":
            language_instruction = f"Please respond in {language} language."
        else:
            language_instruction = ""

        available_agents_str = "\n".join(
            [
                f'<agent name="{agent.name}">{agent.description}</agent>'
                for agent in self.agents.values()
            ]
        )
        system_prompt = ChatMessage(
            role="system",
            content=PLANNER_PROMPT.format(
                language_instruction=language_instruction,
                state=str(state),
                available_agents=available_agents_str,
            ),
        )

        # Stream the response from the llm
        response = await self.llm.astream_chat(
            messages=[system_prompt] + chat_history,
        )
        full_response = ""
        async for chunk in response:
            full_response += chunk.delta or ""
            if chunk.delta:
                ctx.write_event_to_stream(
                    StreamEvent(delta=chunk.delta),
                )

        # Parse the response for direct response or plan
        direct_response_match = re.search(
            r"<direct_response>(.*?)</direct_response>", full_response, re.DOTALL
        )
        plan_match = re.search(r"<plan>(.*?)</plan>", full_response, re.DOTALL)

        if direct_response_match:
            # Direct response from planner - no agents needed
            direct_content = direct_response_match.group(1).strip()

            # Emit direct response event
            ctx.write_event_to_stream(DirectResponseEvent(response=direct_content))

            chat_history.append(
                ChatMessage(
                    role="assistant",
                    content=direct_content,
                )
            )
            return OutputEvent(
                response=direct_content,
                chat_history=chat_history,
                state=state or {},
            )
        elif plan_match:
            # Plan execution needed
            xml_str = f"<plan>{plan_match.group(1)}</plan>"
            root = ET.fromstring(xml_str)
            plan = Plan(steps=[])
            for step in root.findall("step"):
                plan.steps.append(
                    PlanStep(
                        agent_name=step.attrib["agent"],
                        agent_input=step.text.strip() if step.text else "",
                    )
                )

            return ExecuteEvent(plan=plan, chat_history=chat_history)
        else:
            # Fallback - treat as direct response if no tags found, but clean any remaining tags
            clean_response = full_response
            # Remove any leftover direct_response tags
            clean_response = re.sub(
                r"</?direct_response[^>]*>", "", clean_response
            ).strip()
            # Remove any leftover plan tags
            clean_response = re.sub(r"</?plan[^>]*>", "", clean_response).strip()

            chat_history.append(
                ChatMessage(
                    role="assistant",
                    content=clean_response,
                )
            )
            return OutputEvent(
                response=clean_response,
                chat_history=chat_history,
                state=state or {},
            )

    @step
    async def execute(self, ctx: Context, ev: ExecuteEvent) -> OutputEvent:
        chat_history = ev.chat_history if isinstance(ev.chat_history, list) else []
        plan = ev.plan
        state = await ctx.store.get("state")
        if not isinstance(state, dict):
            state = {}

        for step_number, step in enumerate(plan.steps, 1):
            agent = self.agents[step.agent_name]
            agent_input = step.agent_input
            ctx.write_event_to_stream(
                PlanEvent(
                    step_info=f"🔄 Step {step_number}/{len(plan.steps)}: {step.agent_input}"
                ),
            )

            if step.agent_name == "PlantRecognitionAgent":
                # Execute plant recognition
                result = await self.call_plant_recognition_agent(
                    ctx, agent, agent_input, step_number
                )
                state["plant_identification"] = result

            elif step.agent_name == "PlantCareAgent":
                # Execute plant care
                result = await self.call_plant_care_agent(
                    ctx, agent, agent_input, step_number
                )
                state["plant_care"] = result

            await ctx.store.set("state", state)

        # Create final response based on executed steps
        final_response = "Task completed successfully."
        if "plant_care" in state:
            final_response = state["plant_care"]
        elif "plant_identification" in state:
            final_response = state["plant_identification"]

        chat_history.append(ChatMessage(role="assistant", content=final_response))

        return OutputEvent(
            response=final_response, chat_history=chat_history, state=state
        )

    async def call_plant_recognition_agent(
        self,
        ctx: Context,
        agent: FunctionAgent,
        input_msg: str,
        step_number: Optional[int] = None,
    ) -> str:
        """Call the plant recognition agent and return the result."""
        # Emit agent execution event
        ctx.write_event_to_stream(
            AgentExecutionEvent(
                agent_name="PlantRecognitionAgent",
                input_message=input_msg,
                step_number=step_number,
            )
        )

        try:
            # Call recognition tool directly with context
            logger.info("Calling recognition tool with context...")
            from src.workflows.tools.recognize_plant import recognize_plant

            try:
                result = await recognize_plant(ctx)
                logger.info(f"Direct tool call result: {result[:100]}...")
            except Exception as tool_error:
                logger.error(f"Direct tool call failed: {tool_error}")
                # Fallback to agent call
                try:
                    if hasattr(agent, "achat"):
                        response = await agent.achat(input_msg)
                    elif hasattr(agent, "chat"):
                        response = agent.chat(input_msg)
                    else:
                        response = await agent.run(input_msg)
                    result = str(response)
                except Exception as call_error:
                    logger.error(
                        f"Error calling recognition agent method: {call_error}"
                    )
                    raise call_error

            # Emit completion event
            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name="PlantRecognitionAgent",
                    result=result,
                    step_number=step_number,
                    success=True,
                )
            )

            return result

        except Exception as e:
            # Log the full error for debugging
            import logging

            workflow_logger = logging.getLogger("PlantPalWorkflow")
            workflow_logger.error(f"PlantRecognitionAgent execution failed: {str(e)}")
            import traceback

            workflow_logger.error(f"Traceback: {traceback.format_exc()}")

            # Emit completion event with error
            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name="PlantRecognitionAgent",
                    result=f"Error: {str(e)}",
                    step_number=step_number,
                    success=False,
                )
            )
            return f"Error during plant recognition: {str(e)}"

    async def call_plant_care_agent(
        self,
        ctx: Context,
        agent: FunctionAgent,
        input_msg: str,
        step_number: Optional[int] = None,
    ) -> str:
        """Call the plant care agent and return the result."""
        # Emit agent execution event
        ctx.write_event_to_stream(
            AgentExecutionEvent(
                agent_name="PlantCareAgent",
                input_message=input_msg,
                step_number=step_number,
            )
        )

        try:
            # Get previous plant identification and language if available
            state = await ctx.store.get("state") or {}
            plant_identification = state.get("plant_identification", "")
            language = state.get("language", "en")

            # Enhance the input with plant identification and language if needed
            enhanced_input = input_msg
            if plant_identification:
                enhanced_input = f"Previously identified plant: {plant_identification}\n\nPlease start your response by mentioning that this plant was identified as the above species, then provide the care instructions.\n\n{enhanced_input}"
                logger.info(
                    f"Enhanced input with plant identification: {enhanced_input[:200]}..."
                )
            if language and language != "en":
                enhanced_input = (
                    f"Please respond in {language} language.\n\n{enhanced_input}"
                )

            # Try different methods to call the agent
            try:
                if hasattr(agent, "achat"):
                    response = await agent.achat(enhanced_input)
                elif hasattr(agent, "chat"):
                    response = agent.chat(enhanced_input)
                else:
                    # Fallback - try to run the agent directly
                    response = await agent.run(enhanced_input)
                result = str(response)
            except Exception as call_error:
                logger.error(f"Error calling agent method: {call_error}")
                raise call_error

            # Emit completion event
            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name="PlantCareAgent",
                    result=result,
                    step_number=step_number,
                    success=True,
                )
            )

            return result

        except Exception as e:
            # Log the full error for debugging
            import logging

            workflow_logger = logging.getLogger("PlantPalWorkflow")
            workflow_logger.error(f"PlantCareAgent execution failed: {str(e)}")
            import traceback

            workflow_logger.error(f"Traceback: {traceback.format_exc()}")

            # Emit completion event with error
            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name="PlantCareAgent",
                    result=f"Error: {str(e)}",
                    step_number=step_number,
                    success=False,
                )
            )
            return f"Error during plant care advice: {str(e)}"
