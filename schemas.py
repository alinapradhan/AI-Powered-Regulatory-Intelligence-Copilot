"""
Request/response schemas for the API layer.
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., description="Plain-language question about a regulation")
    jurisdiction: str | None = Field(None, description="e.g. 'US-Fed', 'UK-FCA'")


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
    jurisdiction: str


class MapRequest(BaseModel):
    doc_id: str
    jurisdiction: str | None = None


class MapResultItem(BaseModel):
    obligation_id: str
    obligation_section: str
    categories: list[str]
    mapped_controls: list[str]
    coverage: str


class ReportRequest(BaseModel):
    title: str
    jurisdiction: str
    doc_ids: list[str]
    policy_text: str = ""
    policy_facts: dict = {}


class ViolationRequest(BaseModel):
    policy_text: str
    policy_facts: dict
    applicable_regs: list[str]


class ViolationItem(BaseModel):
    source: str
    rule_id: str | None
    severity: str
    description: str
    evidence: str
