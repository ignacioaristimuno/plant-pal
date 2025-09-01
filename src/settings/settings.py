"""Application settings module."""

import yaml
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and YAML config."""

    # Required API keys (from environment variables)
    openai_api_key: str = Field(..., description="OpenAI API key")
    tavily_api_key: str | None = Field(None, description="Tavily API key")

    # Model configurations (from YAML)
    openai_text_model: str = "gpt-4.1-mini"
    openai_vision_model: str = "gpt-4.1"

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_model_config()

    def _load_model_config(self):
        """Load model configurations from YAML file."""
        config_path = Path("config/models.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                self.openai_text_model = config.get(
                    "openai_text_model", self.openai_text_model
                )
                self.openai_vision_model = config.get(
                    "openai_vision_model", self.openai_vision_model
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()
