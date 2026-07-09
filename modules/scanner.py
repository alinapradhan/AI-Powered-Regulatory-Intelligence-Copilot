"""
Violation detector: combines the deterministic rules engine with an
LLM-based qualitative review of policy text, then reconciles the two
so the rules engine's findings are always the authoritative gate for
anything it has an explicit rule for.
"""

from dataclasses import dataclass

from core.audit_log import AuditLog, make_entry
from core.llm_client import LLMClient
from modules.violation_detector.rules_engine import RuleHit, RulesEngine


@dataclass
class Violation:
    source: str          # "rule" | "llm"
    rule_id: str | None
    severity: str
    description: str
    evidence: str


LLM_REVIEW_SYSTEM_PROMPT = (
    "You are a compliance risk reviewer. Given a policy document excerpt and a list of "
    "applicable regulations, identify potential gaps or violations that are NOT already "
    "covered by explicit numeric rule checks. Focus on qualitative gaps: missing "
    "procedures, unclear ownership, absent escalation paths, stale references. "
    "For each finding, state the severity (low/medium/high/critical) and the evidence "
    "from the text. Do not invent numeric thresholds; only comment on what is present or "
    "absent in the text itself."
)


class ViolationDetector:
    def __init__(self, rules_engine: RulesEngine, llm_client: LLMClient, audit_log: AuditLog | None = None):
        self.rules_engine = rules_engine
        self.llm_client = llm_client
        self.audit_log = audit_log or AuditLog()

    def scan(self, policy_text: str, policy_facts: dict, applicable_regs: list[str]) -> list[Violation]:
        rule_hits = self.rules_engine.check(policy_facts)
        violations = [self._from_rule_hit(hit) for hit in rule_hits]

        llm_findings = self._llm_review(policy_text, applicable_regs)
        violations.extend(llm_findings)

        self.audit_log.record(make_entry(
            module="violation_detector",
            request_summary=f"scan policy against {applicable_regs}",
            output_summary=f"{len(rule_hits)} rule violations, {len(llm_findings)} qualitative flags",
        ))

        return violations

    def _from_rule_hit(self, hit: RuleHit) -> Violation:
        return Violation(
            source="rule",
            rule_id=hit.rule_id,
            severity=hit.severity,
            description=hit.description,
            evidence=hit.evidence,
        )

    def _llm_review(self, policy_text: str, applicable_regs: list[str]) -> list[Violation]:
        prompt = (
            f"Applicable regulations: {', '.join(applicable_regs)}\n\n"
            f"Policy excerpt:\n{policy_text}\n\n"
            "List qualitative gaps or potential violations as:\n"
            "SEVERITY | DESCRIPTION | EVIDENCE"
        )
        response = self.llm_client.complete(prompt, system=LLM_REVIEW_SYSTEM_PROMPT)

        findings = []
        for line in response.text.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3 and parts[0].lower() in ("low", "medium", "high", "critical"):
                findings.append(Violation(
                    source="llm", rule_id=None,
                    severity=parts[0].lower(), description=parts[1], evidence=parts[2],
                ))
        return findings
