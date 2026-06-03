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


async def analyze_journal_entry(
    entry_id: str,
    entry_text: str,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Analyze a journal entry using an OpenAI-compatible LLM.

    Args:
        entry_id: ID of the entry being analyzed (pass through to the result).
        entry_text: Combined work + struggle + intention text.
        client: OpenAI client. If None, a default one is constructed from
            application settings. Tests pass in a MockAsyncOpenAI here; production code
            in the router calls this with no ``client`` argument.

    Returns:
        A dict matching AnalysisResponse:
            {
                "entry_id":  str,
                "sentiment": str,   # "positive" | "negative" | "neutral"
                "summary":   str,
                "topics":    list[str],
            }

    TODO (Task 4):
      1. If ``client is None``, call ``_default_client()`` to construct one.
      2. Build a messages list that includes ``entry_text`` somewhere
         (the unit tests check that the entry text reaches the LLM).
      3. Call ``client.chat.completions.create(...)`` with a model name
         (use ``get_settings().openai_model`` — defaults to "gpt-4o-mini").
      4. Parse the assistant's JSON response with ``json.loads()``.
      5. Return a dict with ``entry_id``, ``sentiment``, ``summary``, ``topics``.
    """

    if client is None:
        client = _default_client()

    model = "gpt-5.4-nano"
    prompt_template = f"""
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

    response = await client.chat.completions.create(
        model=model, temperature=0.8, messages=[{"role": "user", "content": prompt_template}]
    )
    assistant_raw_message = response.choices[0].message.content

    if assistant_raw_message is None:
        raise ValueError("Model returned empty content")

    analysis = json.loads(assistant_raw_message)
    analysis["entry_id"] = entry_id
    analysis["created_at"] = datetime.now(UTC).isoformat()

    return analysis
