from src.settings.settings import get_settings
from llama_index.llms.openai import OpenAI


# Load application settings (API keys, model names, etc.)
settings = get_settings()


llm_client = OpenAI(
    model=settings.openai_text_model,
    api_key=settings.openai_api_key,
    reasoning={"effort": "minimal"},
    verbosity="low",
    streaming=False,
)


vlm_client = OpenAI(
    model=settings.openai_vision_model,
    api_key=settings.openai_api_key,
    streaming=False,
)
