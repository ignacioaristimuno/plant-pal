from llama_index.core.llms import ChatMessage as LlamaChatMessage
from llama_index.core.workflow import Context

from src.llm.client import vlm_client
from src.settings.logger import custom_logger


# Set up logger
logger = custom_logger("PlantRecognitionAgent")

# Prompt
PLANT_RECOGNITION_PROMPT = """
## Role
You are a plant recognition agent.

You should analyze the image and provide a concise answer of what type of plant is this.

## Instructions
- Be concise. 
- Mention the plant name (both common name and botanical name).
- Make sure you mention the specific plant, not a broader term (e.g. "Aglaonema Silver Bay" instead of just "Aglaonema").
- Briefly mention other similar plants that may be confused with the one in the image.
- The response in the following language: {language}.
"""


# Tool implementation
async def recognize_plant(ctx: Context) -> str:
    """Internal implementation of plant recognition."""
    
    # Get data from context
    image_bytes = await ctx.store.get("image_bytes")
    state = await ctx.store.get("state") or {}
    language = state.get("language", "en")
    
    if image_bytes is None:
        logger.error("No image_bytes found in context")
        return "No image found. Please provide an image."
    
    # Prepare the prompt with language instruction
    prompt_text = PLANT_RECOGNITION_PROMPT.format(
        language=language,
    )

    # Send request to vision model
    response = vlm_client.chat(
        messages=[
            LlamaChatMessage(
                role="user",
                content=[
                    {
                        "block_type": "text",
                        "text": prompt_text,
                    },
                    {
                        "block_type": "image",
                        "image": image_bytes,
                    },
                ],
            )
        ]
    )

    return response.message.content
