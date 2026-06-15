from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values are loaded in this order (later sources override earlier ones):
      1. Defaults defined on the fields below.
      2. A ``.env`` file in the current working directory.
      3. Process environment variables.

    Environment variables are matched case-insensitively, so ``DATABASE_URL``
    in ``.env`` populates ``database_url`` on this model.
    """

    database_url: str = Field(
        description="PostgreSQL connection URL (e.g. postgresql://user:pass@host:5432/db).",
    )
    cloud_native: bool = Field(
        default=False,
        description=(
            "If true, use AWS Bedrock with DeepSeek for journal analysis instead "
            "of an OpenAI-compatible provider. Requires valid AWS credentials and "
            "network access to Bedrock."
        ),
    )
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock (if cloud_native=true).",
    )
    bedrock_model_id: str = Field(
        default="deepseek.r1-v1:0",
        description="Bedrock model ID to use for journal analysis in cloud-native mode.",
    )
    openai_api_key: str = Field(
        description=(
            "API key for any OpenAI-compatible provider. Task 4 uses this to "
            "construct an AsyncOpenAI client; during Tasks 1-3 any non-empty "
            "placeholder works."
        ),
    )
    openai_base_url: str = Field(
        default="https://models.inference.ai.azure.com",
        description="Base URL for the OpenAI-compatible provider.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Model name passed to chat.completions.create().",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """FastAPI dependency that returns a cached ``Settings`` instance.

    Tests can override this with::

        app.dependency_overrides[get_settings] = lambda: Settings(
            database_url="...",
            openai_api_key="...",
        )
    """
    return Settings()  # type: ignore[call-arg]
