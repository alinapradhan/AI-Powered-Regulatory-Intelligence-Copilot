"""
Central configuration for the Regulatory Intelligence Copilot.

All modules import settings from here rather than reading
environment variables directly, so behavior stays consistent
and easy to override in tests.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # LLM
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model_name: str = "claude-sonnet-4-6"
    max_tokens: int = 1000

    # Retrieval
    top_k_chunks: int = 5
    min_similarity: float = 0.15

    # Violation detection
    severity_order: tuple = ("low", "medium", "high", "critical")

    # Audit
    audit_log_path: str = "audit_log.jsonl"

    # Jurisdictions supported out of the box (extend as needed)
    supported_jurisdictions: tuple = ("US-Fed", "US-OCC", "EU-ECB", "UK-FCA", "Basel")


settings = Settings()
