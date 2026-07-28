"""
Thin wrapper around the Anthropic API.

Keeping this isolated means every module calls `LLMClient.complete(...)`
instead of touching the SDK directly, so swapping models, adding
retries, or mocking in tests only requires changes here.
"""

from dataclasses import dataclass

from core.config import settings

try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


@dataclass
class LLMResponse:
    text: str
    confidence: float  # heuristic, since the API doesn't return one natively
    raw: dict | None = None


class LLMClient:
    """
    Wraps calls to Claude. Falls back to a deterministic stub response
    if the SDK or API key isn't available, so the rest of the system
    (routing, retrieval, report assembly) can still be exercised and
    tested without network access.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.model_name
        self._client = None
        if _SDK_AVAILABLE and self.api_key:
            self._client = anthropic.Anthropic(api_key=self.api_key)

    def complete(self, prompt: str, system: str | None = None, max_tokens: int | None = None) -> LLMResponse:
        if self._client is None:
            return self._stub_response(prompt)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens or settings.max_tokens,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return LLMResponse(text=text, confidence=0.8, raw=response.model_dump() if hasattr(response, "model_dump") else None)

    def _stub_response(self, prompt: str) -> LLMResponse:
        """No API key / SDK configured — return a clearly-marked placeholder."""
        return LLMResponse(
            text=(
                "[STUB RESPONSE — no ANTHROPIC_API_KEY configured]\n"
                f"Prompt received ({len(prompt)} chars). Configure core.config.settings.anthropic_api_key "
                "or set the ANTHROPIC_API_KEY environment variable to get real completions."
            ),
            confidence=0.0,
        )
