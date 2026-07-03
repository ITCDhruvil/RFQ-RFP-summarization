import json
import logging
import time
from typing import Any

from django.conf import settings
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from apps.core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class OpenAIService:
    """Reusable OpenAI client with retries, timeouts, and JSON responses."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ServiceError(
                "OPENAI_API_KEY is not configured.",
                code="openai_not_configured",
                status_code=503,
            )
        self._client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        self.model = settings.OPENAI_MODEL

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        last_error: Exception | None = None

        for attempt in range(settings.OPENAI_MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                content = response.choices[0].message.content or "{}"
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                    "model": self.model,
                }
                return json.loads(content), usage

            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                wait = min(2**attempt, 30)
                logger.warning(
                    "openai_retry attempt=%s error=%s wait=%s",
                    attempt + 1,
                    type(exc).__name__,
                    wait,
                )
                time.sleep(wait)
            except json.JSONDecodeError as exc:
                raise ServiceError(
                    "OpenAI returned invalid JSON.",
                    code="openai_invalid_json",
                    status_code=502,
                ) from exc

        raise ServiceError(
            f"OpenAI request failed after retries: {last_error}",
            code="openai_request_failed",
            status_code=502,
        ) from last_error

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        """Batch embed texts for Chroma indexing / retrieval."""
        if not texts:
            return [], {"total_tokens": 0, "model": settings.OPENAI_EMBEDDING_MODEL}

        model = settings.OPENAI_EMBEDDING_MODEL
        batch_size = 100
        all_embeddings: list[list[float]] = []
        total_tokens = 0
        last_error: Exception | None = None

        max_chars = settings.OPENAI_EMBEDDING_MAX_CHARS

        def _truncate_for_embedding(text: str) -> str:
            if len(text) <= max_chars:
                return text
            return text[:max_chars]

        for start in range(0, len(texts), batch_size):
            batch = [_truncate_for_embedding(t) for t in texts[start : start + batch_size]]
            for attempt in range(settings.OPENAI_MAX_RETRIES + 1):
                try:
                    response = self._client.embeddings.create(
                        model=model,
                        input=batch,
                    )
                    ordered = sorted(response.data, key=lambda x: x.index)
                    all_embeddings.extend([row.embedding for row in ordered])
                    if response.usage:
                        total_tokens += response.usage.total_tokens or 0
                    break
                except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                    last_error = exc
                    time.sleep(min(2**attempt, 30))
            else:
                raise ServiceError(
                    f"OpenAI embedding failed: {last_error}",
                    code="openai_embedding_failed",
                    status_code=502,
                ) from last_error

        usage = {
            "total_tokens": total_tokens,
            "model": model,
            "embedding_count": len(texts),
        }
        return all_embeddings, usage
