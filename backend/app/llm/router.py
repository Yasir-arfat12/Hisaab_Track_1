import asyncio
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

import httpx
import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.providers.openai_compat import (
    ProviderSpec,
    build_provider_specs,
    call_openai_compatible,
)
from app.models.cache import LlmCache

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMCallResult[T: BaseModel]:
    data: T
    provider: str
    model: str
    from_cache: bool


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.split())


def compute_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(_normalize_prompt(prompt).encode("utf-8")).hexdigest()


def _parse_retry_after(header_value: str | None, default_seconds: int = 60) -> int:
    if not header_value:
        return default_seconds
    try:
        parsed = int(header_value.strip())
        return max(1, parsed)
    except ValueError:
        return default_seconds


class LLMRouter:
    """Provider-agnostic LLM router with failover, Retry-After cooldowns, and DB cache."""

    def __init__(
        self,
        *,
        specs: list[ProviderSpec] | None = None,
        max_concurrent: int | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._specs = specs
        self._semaphore = asyncio.Semaphore(
            max_concurrent if max_concurrent is not None else settings.LLM_MAX_CONCURRENT
        )
        self._cooldowns: dict[str, datetime] = {}
        self._now = now_fn or (lambda: datetime.now(UTC))

    def get_specs(self) -> list[ProviderSpec]:
        return self._specs if self._specs is not None else build_provider_specs()

    def is_in_cooldown(self, spec_id: str) -> bool:
        until = self._cooldowns.get(spec_id)
        if until is None:
            return False
        return until > self._now()

    def set_cooldown(self, spec_id: str, seconds: int) -> None:
        self._cooldowns[spec_id] = self._now() + timedelta(seconds=seconds)

    async def _cache_lookup(
        self,
        db: AsyncSession | None,
        prompt_hash: str,
        schema: type[T],
    ) -> LLMCallResult[T] | None:
        if db is None:
            return None
        now = self._now()
        res = await db.execute(
            select(LlmCache).where(
                LlmCache.prompt_hash == prompt_hash,
                LlmCache.expires_at > now,
            )
        )
        cached = res.scalar_one_or_none()
        if cached is None:
            return None
        try:
            parsed = schema.model_validate_json(cached.response_json)
        except ValidationError:
            return None
        return LLMCallResult(
            data=parsed,
            provider=cached.provider,
            model=cached.model,
            from_cache=True,
        )

    async def _cache_store(
        self,
        db: AsyncSession | None,
        prompt_hash: str,
        provider: str,
        model: str,
        raw_json: str,
        tokens_used: int | None,
    ) -> None:
        if db is None:
            return
        now = self._now()
        expires_at = now + timedelta(seconds=settings.LLM_CACHE_TTL_SECONDS)
        existing = (
            await db.execute(select(LlmCache).where(LlmCache.prompt_hash == prompt_hash))
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                LlmCache(
                    id=uuid4(),
                    prompt_hash=prompt_hash,
                    provider=provider,
                    model=model,
                    response_json=raw_json,
                    tokens_used=tokens_used,
                    created_at=now,
                    expires_at=expires_at,
                )
            )
        else:
            existing.provider = provider
            existing.model = model
            existing.response_json = raw_json
            existing.tokens_used = tokens_used
            existing.created_at = now
            existing.expires_at = expires_at
        await db.commit()

    async def call_json(
        self,
        prompt: str,
        schema: type[T],
        *,
        db: AsyncSession | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> LLMCallResult[T] | None:
        """
        Try cached result, then iterate through configured providers in order.
        Returns None if all providers fail, time out, or are cooling down.
        """
        prompt_hash = compute_prompt_hash(prompt)
        cached = await self._cache_lookup(db, prompt_hash, schema)
        if cached is not None:
            logger.info("llm.cache_hit", provider=cached.provider, model=cached.model)
            return cached

        async with self._semaphore:
            for spec in self.get_specs():
                if not spec.api_key:
                    continue
                if self.is_in_cooldown(spec.spec_id):
                    logger.info("llm.skip_cooldown", spec_id=spec.spec_id)
                    continue

                try:
                    raw, tokens_used = await call_openai_compatible(
                        spec, prompt, http_client=http_client
                    )
                    parsed = schema.model_validate_json(raw)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    if status_code in (429, 503):
                        retry_after = _parse_retry_after(
                            exc.response.headers.get("Retry-After")
                        )
                        self.set_cooldown(spec.spec_id, retry_after)
                        logger.warning(
                            "llm.provider_cooldown",
                            spec_id=spec.spec_id,
                            status_code=status_code,
                            retry_after=retry_after,
                        )
                    else:
                        logger.warning(
                            "llm.provider_http_error",
                            spec_id=spec.spec_id,
                            status_code=status_code,
                        )
                    continue
                except (httpx.TimeoutException, httpx.HTTPError) as exc:
                    logger.warning(
                        "llm.provider_network_error",
                        spec_id=spec.spec_id,
                        error=str(exc),
                    )
                    continue
                except (ValidationError, ValueError, KeyError) as exc:
                    logger.warning(
                        "llm.schema_validation_failed",
                        spec_id=spec.spec_id,
                        error=str(exc),
                    )
                    continue

                await self._cache_store(
                    db, prompt_hash, spec.provider, spec.model, raw, tokens_used
                )
                return LLMCallResult(
                    data=parsed,
                    provider=spec.provider,
                    model=spec.model,
                    from_cache=False,
                )

        return None
