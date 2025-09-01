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

logger = custom_logger("PlantPalWorkflow")


class PlantPalWorkflow(Workflow):
    llm = llm_client
    vlm = vlm_client
    agents: dict[str, FunctionAgent] = {
        plant_recognition_agent.name: plant_recognition_agent,
        plant_care_agent.name: plant_care_agent,
    }

    async def _initialize_state(self, ctx: Context, initial_state: Any) -> dict:
        """Initialize workflow state."""
        if isinstance(initial_state, dict):
            await ctx.store.set("state", initial_state)
            if "image_bytes" in initial_state:
                await ctx.store.set("image_bytes", initial_state["image_bytes"])
            return initial_state
        
        if not await ctx.store.get("state"):
            await ctx.store.set("state", {})
        return {}

    def _build_system_prompt(self, state: dict) -> ChatMessage:
        """Build system prompt with current state and available agents."""
        language = state.get("language", "en")
        language_instruction = f"Please respond in {language} language." if language != "en" else ""
        
        available_agents_str = "\n".join(
            f'<agent name="{agent.name}">{agent.description}</agent>'
            for agent in self.agents.values()
        )
        
        return ChatMessage(
            role="system",
            content=PLANNER_PROMPT.format(
                language_instruction=language_instruction,
                state=str(state),
                available_agents=available_agents_str,
            ),
        )

    async def _stream_llm_response(self, ctx: Context, messages: list[ChatMessage]) -> str:
        """Stream LLM response and return full response."""
        response = await self.llm.astream_chat(messages)
        full_response = ""
        async for chunk in response:
            full_response += chunk.delta or ""
            if chunk.delta:
                ctx.write_event_to_stream(StreamEvent(delta=chunk.delta))
        return full_response

    def _parse_response(self, response: str) -> tuple[Optional[str], Optional[Plan]]:
        """Parse LLM response for direct response or plan."""
        direct_match = re.search(r"<direct_response>(.*?)</direct_response>", response, re.DOTALL)
        plan_match = re.search(r"<plan>(.*?)</plan>", response, re.DOTALL)
        
        if direct_match:
            return direct_match.group(1).strip(), None
        
        if plan_match:
            xml_str = f"<plan>{plan_match.group(1)}</plan>"
            root = ET.fromstring(xml_str)
            plan = Plan(steps=[
                PlanStep(
                    agent_name=step.attrib["agent"],
                    agent_input=step.text.strip() if step.text else "",
                )
                for step in root.findall("step")
            ])
            return None, plan
        
        # Fallback: clean response of any XML tags
        clean_response = re.sub(r"</?(?:direct_response|plan)[^>]*>", "", response).strip()
        return clean_response, None

    async def _call_agent(self, ctx: Context, agent_name: str, agent_input: str, step_number: Optional[int] = None) -> str:
        """Generic agent calling method."""
        ctx.write_event_to_stream(
            AgentExecutionEvent(
                agent_name=agent_name,
                input_message=agent_input,
                step_number=step_number,
            )
        )

        try:
            agent = self.agents[agent_name]
            result = ""

            if agent_name == "PlantRecognitionAgent":
                result = await self._execute_plant_recognition(ctx, agent_input)
            elif agent_name == "PlantCareAgent":
                result = await self._execute_plant_care(ctx, agent, agent_input)

            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name=agent_name,
                    result=result,
                    step_number=step_number,
                    success=True,
                )
            )
            return result

        except Exception as e:
            logger.error(f"{agent_name} execution failed: {str(e)}")
            ctx.write_event_to_stream(
                AgentCompletionEvent(
                    agent_name=agent_name,
                    result=f"Error: {str(e)}",
                    step_number=step_number,
                    success=False,
                )
            )
            return f"Error during {agent_name.lower()}: {str(e)}"

    async def _execute_plant_recognition(self, ctx: Context, input_msg: str) -> str:
        """Execute plant recognition logic."""
        try:
            from src.workflows.tools.recognize_plant import recognize_plant
            return await recognize_plant(ctx)
        except Exception as e:
            logger.error(f"Direct tool call failed: {e}")
            raise e

    async def _execute_plant_care(self, ctx: Context, agent: FunctionAgent, input_msg: str) -> str:
        """Execute plant care logic."""
        state = await ctx.store.get("state") or {}
        plant_identification = state.get("plant_identification", "")
        language = state.get("language", "en")

        enhanced_input = input_msg
        if plant_identification:
            enhanced_input = f"Previously identified plant: {plant_identification}\n\nPlease start your response by mentioning that this plant was identified as the above species, then provide the care instructions.\n\n{enhanced_input}"
        if language != "en":
            enhanced_input = f"Please respond in {language} language.\n\n{enhanced_input}"

        if hasattr(agent, "achat"):
            response = await agent.achat(enhanced_input)
        elif hasattr(agent, "chat"):
            response = agent.chat(enhanced_input)
        else:
            response = await agent.run(enhanced_input)
        
        return str(response)

    @step
    async def plan(self, ctx: Context, ev: StartEvent) -> ExecuteEvent | OutputEvent:
        user_msg_text = getattr(ev, "user_msg", "") or ""
        chat_history = getattr(ev, "chat_history", []) or []
        initial_state = getattr(ev, "state", {}) or {}

        state = await self._initialize_state(ctx, initial_state)
        chat_history = chat_history if isinstance(chat_history, list) else []

        if user_msg_text:
            chat_history.append(ChatMessage(role="user", content=user_msg_text))

        system_prompt = self._build_system_prompt(state)
        full_response = await self._stream_llm_response(ctx, [system_prompt] + chat_history)
        
        direct_content, plan = self._parse_response(full_response)

        if direct_content:
            ctx.write_event_to_stream(DirectResponseEvent(response=direct_content))
            chat_history.append(ChatMessage(role="assistant", content=direct_content))
            return OutputEvent(response=direct_content, chat_history=chat_history, state=state)
        
        if plan:
            return ExecuteEvent(plan=plan, chat_history=chat_history)
        
        # Should not reach here due to fallback in _parse_response
        return OutputEvent(response="Error parsing response", chat_history=chat_history, state=state)

    @step
    async def execute(self, ctx: Context, ev: ExecuteEvent) -> OutputEvent:
        chat_history = ev.chat_history if isinstance(ev.chat_history, list) else []
        state = await ctx.store.get("state") or {}

        for step_number, step in enumerate(ev.plan.steps, 1):
            ctx.write_event_to_stream(
                PlanEvent(step_info=f"🔄 Step {step_number}/{len(ev.plan.steps)}: {step.agent_input}")
            )

            result = await self._call_agent(ctx, step.agent_name, step.agent_input, step_number)
            
            if step.agent_name == "PlantRecognitionAgent":
                state["plant_identification"] = result
            elif step.agent_name == "PlantCareAgent":
                state["plant_care"] = result

            await ctx.store.set("state", state)

        final_response = state.get("plant_care") or state.get("plant_identification") or "Task completed successfully."
        chat_history.append(ChatMessage(role="assistant", content=final_response))

        return OutputEvent(response=final_response, chat_history=chat_history, state=state)
