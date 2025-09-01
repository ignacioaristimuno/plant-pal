import asyncio
import base64
import logging

from llama_index.core.agent.workflow import (
    AgentWorkflow,
    AgentStream,
    AgentOutput,
    ToolCallResult,
    ToolCall,
)
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
        "image_bytes": None,
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
            if user_message == "":
                continue
            if user_message == "q":
                break

            elif user_message == "img":
                # Process the image immediately
                logger.info("Processing image request")

                # Store image in the context store
                logger.info("Storing image in context store")
                img_bytes = base64.b64decode(base64_image)
                await ctx.store.set("image_bytes", img_bytes)
                logger.info(f"Image stored in context store: {len(img_bytes)} bytes")

                # Use a message that will route to plant recognition
                logger.info(
                    "Starting workflow with message: 'I have a plant image to identify'"
                )

                # Remove 'await' here - run() returns a handler, not a coroutine
                handler = agent_workflow.run(
                    "I have a plant image to identify", ctx=ctx
                )

                current_agent = None
                async for event in handler.stream_events():
                    if (
                        hasattr(event, "current_agent_name")
                        and event.current_agent_name != current_agent
                    ):
                        current_agent = event.current_agent_name
                        print(f"\n{'='*50}")
                        print(f"🤖 Agent: {current_agent}")
                        print(f"{'='*50}\n")

                    if isinstance(event, AgentStream):
                        if event.delta:
                            print(event.delta, end="", flush=True)
                    elif isinstance(event, AgentOutput):
                        if event.response.content:
                            print("📤 Output:", event.response.content)
                        if event.tool_calls:
                            print(
                                "🛠️  Planning to use tools:",
                                [call.tool_name for call in event.tool_calls],
                            )
                    elif isinstance(event, ToolCallResult):
                        print(f"🔧 Tool Result ({event.tool_name}):")
                        print(f"  Arguments: {event.tool_kwargs}")
                        print(f"  Output: {event.tool_output}")
                    elif isinstance(event, ToolCall):
                        print(f"🔨 Calling Tool: {event.tool_name}")
                        print(f"  With arguments: {event.tool_kwargs}")

                # Get the final response
                response = await handler
                logger.info(f"Workflow response: {response}")
            else:
                # Run the workflow with just the user message (no image)
                handler = agent_workflow.run(user_message, ctx=ctx)

                current_agent = None
                async for event in handler.stream_events():
                    if (
                        hasattr(event, "current_agent_name")
                        and event.current_agent_name != current_agent
                    ):
                        current_agent = event.current_agent_name
                        print(f"\n{'='*50}")
                        print(f"🤖 Agent: {current_agent}")
                        print(f"{'='*50}\n")

                    if isinstance(event, AgentStream):
                        if event.delta:
                            print(event.delta, end="", flush=True)
                    elif isinstance(event, AgentOutput):
                        if event.response.content:
                            print("📤 Output:", event.response.content)
                        if event.tool_calls:
                            print(
                                "🛠️  Planning to use tools:",
                                [call.tool_name for call in event.tool_calls],
                            )
                    elif isinstance(event, ToolCallResult):
                        print(f"🔧 Tool Result ({event.tool_name}):")
                        print(f"  Arguments: {event.tool_kwargs}")
                        print(f"  Output: {event.tool_output}")
                    elif isinstance(event, ToolCall):
                        print(f"🔨 Calling Tool: {event.tool_name}")
                        print(f"  With arguments: {event.tool_kwargs}")

                # Get the final response
                response = await handler
                print(f"Agent: {response}")

    # Run the async main function
    asyncio.run(main())
