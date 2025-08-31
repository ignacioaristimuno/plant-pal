import logging
from llama_index.core.agent import FunctionAgent

from src.llm.client import llm_client
from src.workflows.tools import recognize_plant

# Set up logging
logger = logging.getLogger(__name__)


PLANT_ROUTER_SYSTEM_PROMPT = """
## Role
You are the PlantRouterAgent, an expert in routing the user's request to the correct agent.
You should identify the type of request the user is making and route it to the correct agent.

## Instructions
** Conversation **
- Keep the conversation friendly and engaging.
- Be concise, the user wants to know the type of request they are making.
- If you understand that the user knows a lot about the plant, be more technical and informative. If not, explain in a way that is easy to understand.

** Routing **
- If the user mentions having an image, wants to identify a plant from an image, or says "I have a plant image to identify", IMMEDIATELY route to PlantRecognitionAgent.
- If the user asks about plant care, watering, or general plant advice, route to PlantCareAgent.
- If you can't identify the request, say so.
- If that plant could be confused with another plant, mentioned the possible confusions.

** Important **
- When routing to PlantRecognitionAgent, use the handoff function to transfer to that agent.
- When routing to PlantCareAgent, use the handoff function to transfer to that agent.
- DO NOT ask for image upload if the user mentions having an image - route directly to PlantRecognitionAgent.
"""


plant_router_agent = FunctionAgent(
    name="PlantRouterAgent",
    description="Useful for routing the user's request to the correct agent.",
    system_prompt=PLANT_ROUTER_SYSTEM_PROMPT,
    llm=llm_client,
    tools=[],
    can_handoff_to=["PlantRecognitionAgent", "PlantCareAgent"],
    streaming=False,
)
