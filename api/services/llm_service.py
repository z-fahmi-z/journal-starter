import json
from datetime import UTC, datetime

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError
from openai import AsyncOpenAI

from api.config import get_settings


def _default_client() -> AsyncOpenAI:
    """Construct the real OpenAI client from application settings.

    Called lazily from ``analyze_journal_entry`` so tests can inject a
    ``MockAsyncOpenAI`` without ever triggering this code path.
    """
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def _is_cloud_native() -> bool:
    """Return True if cloud-native mode is enabled (use Bedrock with DeepSeek)."""
    settings = get_settings()
    return getattr(settings, "cloud_native", False)


def _bedrock_available() -> bool:
    """Return True if AWS Bedrock is reachable with the current credentials."""
    if not _is_cloud_native():
        return False

    try:
        boto3.client("bedrock", region_name=get_settings().aws_region).list_foundation_models()
        return True
    except BotoCoreError, NoCredentialsError, Exception:
        return False


async def _analyze_with_bedrock(entry_id: str, entry_text: str) -> dict:
    """Run the journal analysis via AWS Bedrock (DeepSeek model on Bedrock)."""
    settings = get_settings()
    bedrock = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    prompt_template = _build_prompt(entry_text)

    # DeepSeek model on Bedrock uses a different API format
    # Using the converse API format which works with DeepSeek models
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": [{"text": prompt_template}]}],
            "inferenceConfig": {
                "maxTokens": 1024,
                "temperature": 0.8,
            },
        }
    )

    response = bedrock.invoke_model(
        modelId=settings.bedrock_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    raw = json.loads(response["body"].read())

    # Extract the response text based on DeepSeek's response format
    assistant_raw_message = (
        raw.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    )

    if not assistant_raw_message:
        raise ValueError("Bedrock returned empty content")

    analysis = json.loads(assistant_raw_message)
    analysis["entry_id"] = entry_id
    analysis["created_at"] = datetime.now(UTC).isoformat()
    analysis["model"] = "bedrock-deepseek"
    return analysis


async def _analyze_with_openai(
    entry_id: str, entry_text: str, client: AsyncOpenAI | None = None
) -> dict:
    """Run the journal analysis via OpenAI-compatible endpoint (for local development)."""
    if client is None:
        client = _default_client()

    settings = get_settings()
    model = settings.openai_model or "gpt-4o-mini"

    response = await client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=[{"role": "user", "content": _build_prompt(entry_text)}],
    )
    assistant_raw_message = response.choices[0].message.content

    if assistant_raw_message is None:
        raise ValueError("Model returned empty content")

    analysis = json.loads(assistant_raw_message)
    analysis["entry_id"] = entry_id
    analysis["created_at"] = datetime.now(UTC).isoformat()
    analysis["model"] = "openai-compatible"
    return analysis


def _build_prompt(entry_text: str) -> str:
    """Shared prompt used by both the OpenAI and Bedrock paths."""
    return f"""
    # You are a helpful assistant that analyzes journal entries with these parameters
    # Args:
        entry_text: Combined work + struggle + intention text.
    # User Input:
        entry_text: {entry_text}
    # Output format JSON response:
    {{
        "sentiment": str,   # "positive" | "negative" | "neutral"
        "summary":   str,
        "topics":    list[str],
    }}
    # Rules:
    - Do not include any text outside the JSON response.
    - No emojis, markdown formatting, or explanations.
    - Do not miss any JSON output keys mentioned above.
    """


async def analyze_journal_entry(
    entry_id: str,
    entry_text: str,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Analyze a journal entry using either Bedrock (DeepSeek) or OpenAI-compatible LLM."""

    if _is_cloud_native():
        # Cloud-native mode: Use AWS Bedrock with DeepSeek
        if not _bedrock_available():
            raise RuntimeError("Cannot reach AWS Bedrock service.")
        return await _analyze_with_bedrock(entry_id, entry_text)
    # Local development mode: Use OpenAI-compatible endpoint
    return await _analyze_with_openai(entry_id, entry_text, client)
