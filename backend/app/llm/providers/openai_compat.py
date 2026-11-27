from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True)
class ProviderSpec:
    spec_id: str
    provider: str
    model: str
    base_url: str
    api_key: str


def build_provider_specs() -> list[ProviderSpec]:
    """Build the ordered provider chain from settings."""
    key_map = {
        "groq": (
            "https://api.groq.com/openai/v1/chat/completions",
            settings.GROQ_API_KEY.get_secret_value(),
        ),
        "gemini": (
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            settings.GEMINI_API_KEY.get_secret_value(),
        ),
        "mistral": (
            "https://api.mistral.ai/v1/chat/completions",
            settings.MISTRAL_API_KEY.get_secret_value(),
        ),
    }
    specs: list[ProviderSpec] = []
    for entry in settings.LLM_PROVIDERS:
        if ":" not in entry:
            continue
        provider, model = entry.split(":", 1)
        if provider not in key_map:
            continue
        base_url, api_key = key_map[provider]
        specs.append(
            ProviderSpec(
                spec_id=entry,
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        )
    return specs


async def call_openai_compatible(
    spec: ProviderSpec,
    prompt: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    timeout_seconds: float | None = None,
) -> tuple[str, int | None]:
    """Call an OpenAI-compatible chat completions endpoint and return (content, tokens_used)."""
    timeout = timeout_seconds if timeout_seconds is not None else float(settings.LLM_TIMEOUT_SECONDS)
    headers = {
        "Authorization": f"Bearer {spec.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": spec.model,
        "messages": [
            {"role": "system", "content": "Respond with strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    if http_client is not None:
        resp = await http_client.post(spec.base_url, json=payload, headers=headers, timeout=timeout)
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(spec.base_url, json=payload, headers=headers)

    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    tokens_used = usage.get("total_tokens")
    return str(content), int(tokens_used) if tokens_used is not None else None
