import json
from datetime import UTC, datetime

import boto3
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


async def _analyze_with_bedrock(entry_id: str, entry_text: str) -> dict:
    """Run the journal analysis via AWS Bedrock (DeepSeek model on Bedrock)."""
    settings = get_settings()
    bedrock = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    prompt_template = _build_prompt(entry_text)

    # DeepSeek on Bedrock expects the standard Bedrock converse API format
    # but with specific structure for the messages
    body = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt_template,  # Simple string, not a list with text objects
                }
            ],
            "max_tokens": 1024,  # Note: snake_case, not camelCase
            "temperature": 0.8,
        }
    )

    response = bedrock.invoke_model(
        modelId=settings.bedrock_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    raw = json.loads(response["body"].read())

    # DeepSeek response format on Bedrock
    # The response typically has a "choices" array with the completion
    assistant_raw_message = raw.get("choices", [{}])[0].get("message", {}).get("content", "")

    if not assistant_raw_message:
        raise ValueError("Bedrock returned empty content")

    analysis = json.loads(assistant_raw_message)
    analysis["entry_id"] = entry_id
    analysis["created_at"] = datetime.now(UTC).isoformat()
    analysis["model"] = settings.bedrock_model_id
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
    analysis["model"] = model
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
    if _is_cloud_native():
        return await _analyze_with_bedrock(entry_id, entry_text)
    return await _analyze_with_openai(entry_id, entry_text, client)
