"""
Assembles structured compliance reports from mapping results and
violation scans, rendered through the markdown template. Keeping
report assembly separate from the LLM means the numbers and findings
in the report are always exactly what the mapper/detector produced —
no risk of the LLM silently altering a figure while "summarizing".
"""

import time
from pathlib import Path

from core.audit_log import AuditLog, make_entry
from core.llm_client import LLMClient
from modules.compliance_mapping.mapper import MappingResult
from modules.violation_detector.scanner import Violation

TEMPLATE_PATH = Path(__file__).parent / "templates" / "report_template.md"

SUMMARY_SYSTEM_PROMPT = (
    "You write concise executive summaries for bank compliance reports. "
    "Use only the facts given to you. Do not invent figures. Keep it to 3-5 sentences."
)


class ReportBuilder:
    def __init__(self, llm_client: LLMClient, audit_log: AuditLog | None = None):
        self.llm_client = llm_client
        self.audit_log = audit_log or AuditLog()

    def build(
        self,
        title: str,
        jurisdiction: str,
        regulations: list[str],
        mapping_results: list[MappingResult],
        violations: list[Violation],
    ) -> str:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        coverage_section = self._render_coverage(mapping_results)
        violations_section = self._render_violations(violations)
        summary = self._generate_summary(mapping_results, violations, jurisdiction)
        sources_section = self._render_sources(mapping_results)

        report = template.format(
            title=title,
            jurisdiction=jurisdiction,
            generated_at=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            regulations=", ".join(regulations),
            summary=summary,
            coverage_section=coverage_section,
            violations_section=violations_section,
            sources_section=sources_section,
        )

        self.audit_log.record(make_entry(
            module="report_generator",
            request_summary=f"build report: {title}",
            output_summary=f"{len(mapping_results)} obligations, {len(violations)} violations",
        ))

        return report

    def _render_coverage(self, mapping_results: list[MappingResult]) -> str:
        if not mapping_results:
            return "_No obligations mapped._"
        covered = sum(1 for r in mapping_results if r.coverage == "covered")
        partial = sum(1 for r in mapping_results if r.coverage == "partial")
        gaps = sum(1 for r in mapping_results if r.coverage == "gap")

        lines = [f"- **Covered:** {covered}", f"- **Partial:** {partial}", f"- **Gaps:** {gaps}", "", "| Obligation | Categories | Coverage |", "|---|---|---|"]
        for r in mapping_results:
            lines.append(f"| {r.obligation_section} | {', '.join(r.categories)} | {r.coverage} |")
        return "\n".join(lines)

    def _render_violations(self, violations: list[Violation]) -> str:
        if not violations:
            return "_No violations identified._"
        lines = ["| Severity | Source | Description | Evidence |", "|---|---|---|---|"]
        for v in sorted(violations, key=lambda x: x.severity):
            lines.append(f"| {v.severity} | {v.source} | {v.description} | {v.evidence} |")
        return "\n".join(lines)

    def _render_sources(self, mapping_results: list[MappingResult]) -> str:
        if not mapping_results:
            return "_None._"
        ids = sorted({r.obligation_id for r in mapping_results})
        return "\n".join(f"- {i}" for i in ids)

    def _generate_summary(self, mapping_results: list[MappingResult], violations: list[Violation], jurisdiction: str) -> str:
        facts = (
            f"Jurisdiction: {jurisdiction}. "
            f"Obligations mapped: {len(mapping_results)}. "
            f"Gaps: {sum(1 for r in mapping_results if r.coverage == 'gap')}. "
            f"Violations found: {len(violations)} "
            f"(critical: {sum(1 for v in violations if v.severity == 'critical')})."
        )
        response = self.llm_client.complete(
            f"Write an executive summary using only these facts: {facts}",
            system=SUMMARY_SYSTEM_PROMPT,
        )
        return response.text
