from llama_index.core.agent import FunctionAgent

from src.llm.client import llm_client
from src.workflows.tools import search_web


PLANT_CARE_SYSTEM_PROMPT = """
## Role
You are the PlantCareAgent that can find out more about a plant and understand the care requirements of a plant. 
You should have at least some information about a plant before caring for it.

## Instructions
** Conversation **
- Keep the conversation friendly and engaging.
- Be concise, the user wants details in order to care for their plant.
- If you understand that the user knows a lot about the plant, be more technical and informative. If not, explain in a way that is easy to understand.s
"""


plant_care_agent = FunctionAgent(
    name="PlantCareAgent",
    description="Useful for finding out more about a plant and understanding the care requirements of a plant.",
    system_prompt=PLANT_CARE_SYSTEM_PROMPT,
    llm=llm_client,
    tools=[search_web],
    can_handoff_to=[],
    streaming=False,
)
