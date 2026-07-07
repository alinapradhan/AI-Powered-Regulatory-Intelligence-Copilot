"""
Regulation explainer: answers plain-language questions about
regulations using retrieval-augmented generation over the vector
store, and logs every answer with its sources for audit purposes.
"""

from dataclasses import dataclass

from core.audit_log import AuditLog, make_entry
from core.llm_client import LLMClient
from knowledge.vector_store import VectorStore
from modules.explainer.prompts import SYSTEM_PROMPT, build_qa_prompt


@dataclass
class RegulationAnswer:
    answer: str
    sources: list[dict]
    confidence: float
    jurisdiction: str


class RegulationExplainer:
    def __init__(self, vector_store: VectorStore, llm_client: LLMClient, audit_log: AuditLog | None = None):
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.audit_log = audit_log or AuditLog()

    def answer(self, question: str, jurisdiction: str | None = None) -> RegulationAnswer:
        chunks = self.vector_store.search(question, jurisdiction=jurisdiction)
        prompt = build_qa_prompt(question, chunks)
        response = self.llm_client.complete(prompt, system=SYSTEM_PROMPT)

        sources = [
            {
                "chunk_id": c.chunk.chunk_id,
                "section": c.chunk.section,
                "regulator": c.chunk.regulator,
                "jurisdiction": c.chunk.jurisdiction,
                "score": round(c.score, 3),
            }
            for c in chunks
        ]

        result = RegulationAnswer(
            answer=response.text,
            sources=sources,
            confidence=response.confidence if chunks else 0.0,
            jurisdiction=jurisdiction or "unspecified",
        )

        self.audit_log.record(make_entry(
            module="explainer",
            request_summary=question,
            output_summary=result.answer[:300],
            sources=sources,
            model="stub" if response.confidence == 0.0 and not chunks else "configured",
            confidence=result.confidence,
        ))

        return result
