"""Claude wrapper. Everything that calls the LLM goes through `LLMClient`."""

from functools import lru_cache
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """LLM call failed. The message never includes request content or credentials."""


class LLMClient(Protocol):
    def parse(self, system: str, user: str, schema: type[T]) -> T: ...


@lru_cache
def _client(api_key: str) -> anthropic.Anthropic:
    s = get_settings()
    return anthropic.Anthropic(
        api_key=api_key, timeout=s.llm_timeout_sec, max_retries=s.llm_max_retries
    )


class AnthropicLLM:
    def parse(self, system: str, user: str, schema: type[T]) -> T:
        s = get_settings()
        if s.anthropic_api_key is None or not s.anthropic_api_key.get_secret_value():
            raise LLMError("ANTHROPIC_API_KEY is not set")
        try:
            response = _client(s.anthropic_api_key.get_secret_value()).messages.parse(
                model=s.llm_model,
                max_tokens=s.llm_max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
        except anthropic.APIError as exc:
            raise LLMError(f"api error: {type(exc).__name__}") from exc
        except ValueError as exc:  # truncated or invalid JSON (pydantic ValidationError)
            raise LLMError("invalid structured output") from exc
        if response.stop_reason != "end_turn" or response.parsed_output is None:
            raise LLMError(f"unexpected stop_reason: {response.stop_reason}")
        return response.parsed_output


def get_llm() -> LLMClient:
    return AnthropicLLM()
