import json
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
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
    cloud_native: bool = Field(
        default=False,
        description=(
            "If true, use AWS Bedrock with DeepSeek for journal analysis instead "
            "of an OpenAI-compatible provider. Requires valid AWS credentials and "
            "network access to Bedrock."
        ),
    )

    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL database username.",
    )
    postgres_password: str = Field(
        description="PostgreSQL database password.",
    )
    postgres_db: str = Field(
        default="journaldb",
        description="PostgreSQL database name.",
    )
    postgres_host: str = Field(
        default="postgres",
        description="PostgreSQL database host.",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL database port.",
    )

    database_url: str = Field(
        default="",
        description="PostgreSQL connection URL (computed from POSTGRES_* variables).",
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
        default="",
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

    @field_validator("database_url", mode="before")
    @classmethod
    def build_database_url(cls, v, info):
        """Build DATABASE_URL from individual POSTGRES_* components if not provided."""
        if v:
            return v

        data = info.data
        cloud_native = data.get("cloud_native", False)

        host = data.get("postgres_host")
        port = data.get("postgres_port", 5432)
        db = data.get("postgres_db")

        if not all([host, db]):
            raise ValueError(
                "Cannot build database_url: missing POSTGRES_HOST and POSTGRES_DB."
            )

        if cloud_native:
            raw_secret = data.get("postgres_password")
            if not raw_secret:
                raise ValueError(
                    "CLOUD_NATIVE=true requires POSTGRES_PASSWORD to be set. "
                    "Expected ECS to inject the Secrets Manager value as a JSON string."
                )

            try:
                secret = json.loads(raw_secret)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"CLOUD_NATIVE=true expects POSTGRES_PASSWORD to be a JSON string "
                    f"injected by ECS Secrets Manager, but got an unparseable value: {e}"
                ) from e

            if "password" not in secret:
                raise ValueError(
                    f"Parsed secret does not contain a 'password' key. "
                    f"Found keys: {list(secret.keys())}"
                )

            user = secret.get("username", data.get("postgres_user"))
            password = secret["password"]
        else:
            user = data.get("postgres_user")
            password = data.get("postgres_password")

            if not all([user, password]):
                raise ValueError(
                    "Cannot build database_url: missing POSTGRES_USER or POSTGRES_PASSWORD."
                )

        encoded_password = quote_plus(password)
        return f"postgresql://{user}:{encoded_password}@{host}:{port}/{db}"


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
