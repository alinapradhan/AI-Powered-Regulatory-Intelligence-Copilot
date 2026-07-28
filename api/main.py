"""
FastAPI application. Wires up all modules with shared knowledge
stores and exposes the four core endpoints.

Run locally with:  uvicorn api.main:app --reload
(No deployment required — this just defines the app.)
"""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from api.schemas import (
    AskRequest, AskResponse, MapRequest, MapResultItem,
    ReportRequest, ViolationRequest, ViolationItem,
)
from core.audit_log import AuditLog
from core.llm_client import LLMClient
from knowledge.graph_store import GraphStore
from knowledge.ingestion.chunker import chunk_document
from knowledge.ingestion.fetch_sources import SourceFetcher
from knowledge.metadata_store import DocumentRecord, MetadataStore
from knowledge.vector_store import VectorStore
from modules.compliance_mapping.mapper import ComplianceMapper, InternalControl
from modules.explainer.qa_engine import RegulationExplainer
from modules.report_generator.builder import ReportBuilder
from modules.violation_detector.rules_engine import default_rules
from modules.violation_detector.scanner import ViolationDetector

app = FastAPI(title="Regulatory Intelligence Copilot", version="0.1.0")

# --- Shared infrastructure -------------------------------------------------
audit_log = AuditLog()
llm_client = LLMClient()
vector_store = VectorStore()
graph_store = GraphStore()
metadata_store = MetadataStore()

# --- Bootstrap sample knowledge base ---------------------------------------
_fetcher = SourceFetcher()
for raw_doc in _fetcher.fetch_all_sample():
    chunks = chunk_document(
        text=raw_doc.text, doc_id=raw_doc.doc_id, jurisdiction=raw_doc.jurisdiction,
        regulator=raw_doc.regulator, effective_date=raw_doc.effective_date,
    )
    vector_store.add(chunks)
    metadata_store.upsert_document(DocumentRecord(
        doc_id=raw_doc.doc_id, title=raw_doc.title, jurisdiction=raw_doc.jurisdiction,
        regulator=raw_doc.regulator, effective_date=raw_doc.effective_date, source_url=raw_doc.source_url,
    ))

# --- Modules -----------------------------------------------------------------
explainer = RegulationExplainer(vector_store, llm_client, audit_log)
mapper = ComplianceMapper(vector_store, graph_store, audit_log)
report_builder = ReportBuilder(llm_client, audit_log)
rules_engine = default_rules()
violation_detector = ViolationDetector(rules_engine, llm_client, audit_log)

# Register a couple of sample internal controls so mapping has something to match.
mapper.register_control(
    InternalControl("ctrl-001", "Affiliate Transaction Monitoring", "Tracks exposure to affiliates against Reg W limits", "Treasury"),
    addresses_categories=["affiliate_transactions"],
)
mapper.register_control(
    InternalControl("ctrl-002", "Capital Adequacy Reporting", "Monthly CET1/Tier1/leverage ratio calculation and reporting", "Finance"),
    addresses_categories=["capital_adequacy"],
)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    result = explainer.answer(req.question, jurisdiction=req.jurisdiction)
    return AskResponse(**asdict(result))


@app.post("/map-requirements", response_model=list[MapResultItem])
def map_requirements(req: MapRequest):
    doc = metadata_store.get_document(req.doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{req.doc_id}' not found")
    results = mapper.map_document(req.doc_id, jurisdiction=req.jurisdiction)
    return [MapResultItem(**asdict(r)) for r in results]


@app.post("/generate-report")
def generate_report(req: ReportRequest):
    mapping_results = []
    for doc_id in req.doc_ids:
        mapping_results.extend(mapper.map_document(doc_id, jurisdiction=req.jurisdiction))

    violations = violation_detector.scan(
        policy_text=req.policy_text,
        policy_facts=req.policy_facts,
        applicable_regs=req.doc_ids,
    ) if req.policy_text else []

    report_md = report_builder.build(
        title=req.title,
        jurisdiction=req.jurisdiction,
        regulations=req.doc_ids,
        mapping_results=mapping_results,
        violations=violations,
    )
    return {"report_markdown": report_md}


@app.post("/detect-violations", response_model=list[ViolationItem])
def detect_violations(req: ViolationRequest):
    violations = violation_detector.scan(
        policy_text=req.policy_text,
        policy_facts=req.policy_facts,
        applicable_regs=req.applicable_regs,
    )
    return [ViolationItem(**asdict(v)) for v in violations]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks_indexed": vector_store.size(),
        "jurisdictions": sorted(vector_store.all_jurisdictions()),
    }
