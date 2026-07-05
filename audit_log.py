"""
Audit logging.

Banks need to show *why* the copilot said what it said. Every
answer, mapping, report, or violation flag should be logged with
its sources, model, and timestamp so it can be reviewed later.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core.config import settings


@dataclass
class AuditEntry:
    timestamp: float
    module: str                 # "explainer" | "mapping" | "report" | "violation"
    request_summary: str
    output_summary: str
    sources: list[dict] = field(default_factory=list)
    model: str = ""
    confidence: float = 0.0


class AuditLog:
    def __init__(self, path: str | None = None):
        self.path = Path(path or settings.audit_log_path)

    def record(self, entry: AuditEntry) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def read_all(self) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(AuditEntry(**json.loads(line)))
        return entries


def make_entry(module: str, request_summary: str, output_summary: str,
               sources: list[dict] | None = None, model: str = "", confidence: float = 0.0) -> AuditEntry:
    return AuditEntry(
        timestamp=time.time(),
        module=module,
        request_summary=request_summary,
        output_summary=output_summary,
        sources=sources or [],
        model=model,
        confidence=confidence,
    )
