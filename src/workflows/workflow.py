import asyncio
import base64
import logging

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.schema import ImageDocument
from llama_index.core.workflow import Context

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Enable LlamaIndex debug logging
logging.getLogger("llama_index").setLevel(logging.DEBUG)
logging.getLogger("workflows").setLevel(logging.DEBUG)

from src.workflows.agents.router.agent import plant_router_agent
from src.workflows.agents.plant_recognition.agent import plant_recognition_agent
from src.workflows.agents.plant_care.agent import plant_care_agent
from src.utils.image_documents import (
    run_workflow_with_base64_image,
    create_image_document_from_base64,
)


# Create the agent workflow
agent_workflow = AgentWorkflow(
    agents=[plant_router_agent, plant_recognition_agent, plant_care_agent],
    root_agent=plant_router_agent.name,
    initial_state={
        "plant_recognition": {},
        "plant_care": {},
    },
)


# Add event logging
logger.info("Agent workflow created with agents:")
logger.info(f"  - Root agent: {plant_router_agent.name}")
logger.info(
    f"  - Available agents: {[agent.name for agent in [plant_router_agent, plant_recognition_agent, plant_care_agent]]}"
)

# Create the context
ctx = Context(agent_workflow)


# Run the workflow
if __name__ == "__main__":
    # Create the image document
    with open("images/my_plant.jpeg", "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    async def main():
        while True:
            user_message = input("User: ")
            if user_message == "q":
                break

            elif user_message == "img":
                # Process the image immediately
                logger.info("Processing image request")

                # Store image in the workflow's initial state
                logger.info("Storing image in workflow initial state")
                agent_workflow.initial_state["image_bytes"] = base64.b64decode(
                    base64_image
                )
                logger.info(
                    f"Image stored in workflow state: {len(agent_workflow.initial_state.get('image_bytes', b''))} bytes"
                )

                # Use a message that will route to plant recognition
                logger.info(
                    "Starting workflow with message: 'I have a plant image to identify'"
                )
                logger.info(f"Context store before workflow: {ctx.store}")

                # Test if the router agent is working by trying a simple message first
                logger.info("Testing router with simple message...")
                test_response = await agent_workflow.run("help", ctx=ctx)
                logger.info(f"Router test response: {test_response}")

                response = await agent_workflow.run(
                    "I have a plant image to identify", ctx=ctx
                )

                logger.info(f"Workflow response: {response}")
                logger.info(f"Context store after workflow: {ctx.store}")
            else:
                # Run the workflow with just the user message (no image)
                response = await agent_workflow.run(user_message, ctx=ctx)
            print(f"Agent: {response}")

    # Run the async main function
    asyncio.run(main())
