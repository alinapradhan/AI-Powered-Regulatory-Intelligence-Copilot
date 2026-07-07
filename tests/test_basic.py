"""
Basic end-to-end tests that don't require a real ANTHROPIC_API_KEY
(they exercise the stub LLM path) so the pipeline's plumbing —
ingestion, retrieval, mapping, rules, reporting — can be verified
without network access. Run with: pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.audit_log import AuditLog
from core.llm_client import LLMClient
from knowledge.graph_store import GraphStore
from knowledge.ingestion.chunker import chunk_document
from knowledge.ingestion.fetch_sources import SourceFetcher
from knowledge.vector_store import VectorStore
from modules.compliance_mapping.mapper import ComplianceMapper, InternalControl
from modules.explainer.qa_engine import RegulationExplainer
from modules.report_generator.builder import ReportBuilder
from modules.violation_detector.rules_engine import default_rules
from modules.violation_detector.scanner import ViolationDetector
from orchestration.router import Intent, classify_intent


def build_test_environment(tmp_path):
    audit_log = AuditLog(path=str(tmp_path / "audit.jsonl"))
    llm_client = LLMClient(api_key=None)  # forces stub mode
    vector_store = VectorStore()
    graph_store = GraphStore()

    for raw_doc in SourceFetcher().fetch_all_sample():
        chunks = chunk_document(raw_doc.text, raw_doc.doc_id, raw_doc.jurisdiction, raw_doc.regulator)
        vector_store.add(chunks)

    mapper = ComplianceMapper(vector_store, graph_store, audit_log)
    mapper.register_control(
        InternalControl("ctrl-001", "Affiliate Monitoring", "desc", "Treasury"),
        addresses_categories=["affiliate_transactions"],
    )

    explainer = RegulationExplainer(vector_store, llm_client, audit_log)
    report_builder = ReportBuilder(llm_client, audit_log)
    violation_detector = ViolationDetector(default_rules(), llm_client, audit_log)

    return {
        "vector_store": vector_store, "mapper": mapper, "explainer": explainer,
        "report_builder": report_builder, "violation_detector": violation_detector,
    }


def test_ingestion_populates_vector_store(tmp_path):
    env = build_test_environment(tmp_path)
    assert env["vector_store"].size() > 0
    assert "US-Fed" in env["vector_store"].all_jurisdictions()


def test_explainer_returns_sources(tmp_path):
    env = build_test_environment(tmp_path)
    result = env["explainer"].answer("What is the affiliate transaction limit?", jurisdiction="US-Fed")
    assert isinstance(result.answer, str)
    assert isinstance(result.sources, list)


def test_mapper_finds_coverage(tmp_path):
    env = build_test_environment(tmp_path)
    results = env["mapper"].map_document("reg-w-2024", jurisdiction="US-Fed")
    assert len(results) > 0
    coverages = {r.coverage for r in results}
    assert coverages.issubset({"covered", "partial", "gap"})


def test_rules_engine_flags_violation(tmp_path):
    env = build_test_environment(tmp_path)
    violations = env["violation_detector"].scan(
        policy_text="Sample policy text.",
        policy_facts={"affiliate_single_pct": 15.0},  # exceeds 10% limit
        applicable_regs=["reg-w-2024"],
    )
    rule_violations = [v for v in violations if v.source == "rule"]
    assert any(v.rule_id == "REG-W-SINGLE-AFFILIATE-LIMIT" for v in rule_violations)


def test_rules_engine_passes_when_compliant(tmp_path):
    env = build_test_environment(tmp_path)
    violations = env["violation_detector"].scan(
        policy_text="Sample policy text.",
        policy_facts={"affiliate_single_pct": 5.0},
        applicable_regs=["reg-w-2024"],
    )
    rule_violations = [v for v in violations if v.source == "rule"]
    assert not any(v.rule_id == "REG-W-SINGLE-AFFILIATE-LIMIT" for v in rule_violations)


def test_report_builder_produces_markdown(tmp_path):
    env = build_test_environment(tmp_path)
    mapping_results = env["mapper"].map_document("reg-w-2024", jurisdiction="US-Fed")
    report = env["report_builder"].build(
        title="Test Report", jurisdiction="US-Fed", regulations=["reg-w-2024"],
        mapping_results=mapping_results, violations=[],
    )
    assert "# Test Report" in report
    assert "Compliance Coverage" in report


def test_router_classifies_intent():
    assert classify_intent("What is Regulation W?") == Intent.EXPLAIN
    assert classify_intent("Map this document to our controls") == Intent.MAP
    assert classify_intent("Generate a report on capital adequacy") == Intent.REPORT
    assert classify_intent("Scan for issues in this policy") == Intent.VIOLATION
