import base64

from llama_index.core.schema import ImageDocument
from llama_index.core.workflow import Context

from src.settings.logger import custom_logger


# Set up logger
logger = custom_logger(__name__)


def create_image_document_from_base64(
    base64_string: str, image_id: str = "plant_image"
) -> ImageDocument:
    """
    Create an ImageDocument from a base64 encoded image string.

    Args:
        base64_string (str): The base64 encoded image string.
        image_id (str): The id of the image.

    Returns:
        ImageDocument: The ImageDocument.
    """
    # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
    if base64_string.startswith("data:"):
        base64_string = base64_string.split(",", 1)[1]

    # Decode base64 to bytes
    img_bytes = base64.b64decode(base64_string)

    # Create ImageDocument
    return ImageDocument(image=img_bytes, image_id=image_id)


async def run_workflow_with_base64_image(
    ctx: Context, workflow, base64_image: str, user_message: str = ""
):
    """
    Run the workflow with a base64 encoded image.

    Args:
        ctx (Context): The context.
        base64_image (str): The base64 encoded image string.
        user_message (str): The user message.

    Returns:
        str: The response from the workflow.
    """
    # Decode base64 to bytes for the workflow
    if base64_image.startswith("data:"):
        base64_image = base64_image.split(",", 1)[1]

    img_bytes = base64.b64decode(base64_image)

    # Store image bytes in context state
    logger.info(
        f"Storing image bytes in context state. Image size: {len(img_bytes)} bytes"
    )
    async with ctx.store.edit_state() as ctx_state:
        ctx_state["image_bytes"] = img_bytes
        logger.info(f"Context state after storing image: {ctx_state}")

    # Run the workflow
    if user_message:
        response = await workflow.run(user_message, ctx=ctx)
    else:
        response = await workflow.run("Please analyze this plant image", ctx=ctx)

    return response
