import logging
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from src.llm.client import vlm_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PLANT_RECOGNITION_PROMPT = """What type of plant is this?
Be concise, and describe a bit of its peculiarities and care requirements.

The user message is: "{user_message}"
"""


async def _recognize_plant_impl(ctx: Context) -> str:
    """Internal implementation of plant recognition."""
    logger.info("Plant recognition tool called")
    
    # Get image bytes from context store
    img_bytes = await ctx.store.get("image_bytes")
    
    if img_bytes is None:
        logger.error("No image_bytes found in context store")
        return "No image found in context. Please provide an image."

    # Log the image bytes info
    logger.info(f"Image type: {type(img_bytes)}")
    logger.info(f"Image bytes length: {len(img_bytes)}")
    logger.info(f"First 50 bytes: {img_bytes[:50]}")

    # Send request to vision model
    response = vlm_client.chat(
        messages=[
            ChatMessage(
                role="user",
                content=[
                    {
                        "block_type": "text",
                        "text": PLANT_RECOGNITION_PROMPT.format(
                            user_message="Please analyze this plant image"
                        ),
                    },
                    {
                        "block_type": "image",
                        "image": img_bytes,
                    },
                ],
            )
        ]
    )

    # Store the recognition result in context store
    await ctx.store.set("plant_recognition_result", response.message.content)
    return response.message.content


# Create the FunctionTool
recognize_plant = FunctionTool.from_defaults(
    async_fn=_recognize_plant_impl,
    name="recognize_plant",
    description="Identify a plant from an image that has been provided in the context. Use this tool when you need to analyze and identify a plant species from an image.",
)
