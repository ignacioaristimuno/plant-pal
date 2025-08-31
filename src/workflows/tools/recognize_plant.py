import logging
from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import (
    Context,
    InputRequiredEvent,
    HumanResponseEvent,
)

from src.llm.client import vlm_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PLANT_RECOGNITION_PROMPT = """What type of plant is this?
Be concise, and describe a bit of its peculiarities and care requirements.

The user message is: "{user_message}"
"""


async def recognize_plant(ctx: Context) -> str:
    """Recognize the plant in the image."""
    logger.info(f"Context state keys: {list(ctx.state.keys())}")
    logger.info(f"Context state: {ctx.state}")

    if "image_bytes" not in ctx.state:
        logger.error("No image_bytes found in context state")
        return "No image found in context. Please provide an image."

    img_bytes = ctx.state["image_bytes"]

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

    async with ctx.store.edit_state() as ctx_state:
        ctx_state["plant_recognition"]["recognition"] = response.content
    return f"Plant recognized successfully."
