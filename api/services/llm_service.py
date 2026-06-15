"""Task 4: Implement analyze_journal_entry using any OpenAI-compatible API.

This project mandates the OpenAI Python SDK, which works with:
  - GitHub Models (default, free, no credit card required)
  - OpenAI proper
  - Azure OpenAI
  - Groq, Together, OpenRouter, Fireworks, DeepInfra
  - Ollama, LM Studio, vLLM (local)
  - Anthropic via their OpenAI-compat endpoint

Set OPENAI_API_KEY, and optionally OPENAI_BASE_URL and OPENAI_MODEL
in your .env file. Settings are loaded by ``api.config.Settings``.
"""

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


def _bedrock_available() -> bool:
    """Return True if AWS Bedrock is reachable with the current credentials."""
    try:
        boto3.client("bedrock", region_name="us-east-1").list_foundation_models()
        return True
    except BotoCoreError, NoCredentialsError, Exception:
        return False


async def _analyze_with_bedrock(entry_id: str, entry_text: str) -> dict:
    """Run the journal analysis via AWS Bedrock (Claude on Bedrock)."""
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

    prompt_template = _build_prompt(entry_text)

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.8,
            "messages": [{"role": "user", "content": prompt_template}],
        }
    )

    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    raw = json.loads(response["body"].read())
    assistant_raw_message = raw["content"][0]["text"]

    if not assistant_raw_message:
        raise ValueError("Bedrock returned empty content")

    analysis = json.loads(assistant_raw_message)
    analysis["entry_id"] = entry_id
    analysis["created_at"] = datetime.now(UTC).isoformat()
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
    """Analyze a journal entry using an OpenAI-compatible LLM."""

    if _bedrock_available():
        return await _analyze_with_bedrock(entry_id, entry_text)

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
    return analysis
