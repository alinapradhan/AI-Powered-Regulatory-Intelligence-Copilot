"""
Maps regulatory obligations to internal controls/policies, and
records the relationships in the graph store so gaps (obligations
with no mapped control) can be surfaced later by the violation
detector.
"""

from dataclasses import dataclass

from core.audit_log import AuditLog, make_entry
from knowledge.graph_store import Edge, GraphStore, Node
from knowledge.vector_store import VectorStore
from modules.compliance_mapping.taxonomy import categorize_by_keywords


@dataclass
class InternalControl:
    control_id: str
    name: str
    description: str
    owner: str


@dataclass
class MappingResult:
    obligation_id: str
    obligation_section: str
    categories: list[str]
    mapped_controls: list[str]
    coverage: str    # "covered" | "partial" | "gap"


class ComplianceMapper:
    def __init__(self, vector_store: VectorStore, graph_store: GraphStore, audit_log: AuditLog | None = None):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.audit_log = audit_log or AuditLog()

    def register_control(self, control: InternalControl, addresses_categories: list[str]) -> None:
        node = Node(
            node_id=control.control_id,
            node_type="control",
            label=control.name,
            metadata={"description": control.description, "owner": control.owner, "categories": addresses_categories},
        )
        self.graph_store.add_node(node)

    def map_document(self, doc_id: str, jurisdiction: str | None = None) -> list[MappingResult]:
        chunks = self.vector_store.search(query=doc_id, jurisdiction=jurisdiction, top_k=50, min_similarity=0.0)
        # Fall back: if searching by doc_id text doesn't work well, filter by chunk_id prefix instead.
        relevant = [c for c in chunks if c.chunk.chunk_id.startswith(doc_id)]
        if not relevant:
            relevant = chunks

        results = []
        for retrieved in relevant:
            chunk = retrieved.chunk
            categories = categorize_by_keywords(chunk.text)

            obligation_node_id = f"obligation::{chunk.chunk_id}"
            self.graph_store.add_node(Node(
                node_id=obligation_node_id,
                node_type="obligation",
                label=chunk.section,
                metadata={"jurisdiction": chunk.jurisdiction, "categories": categories},
            ))

            mapped_controls = self._find_matching_controls(categories)
            for control_id in mapped_controls:
                self.graph_store.add_edge(Edge(
                    source_id=obligation_node_id, target_id=control_id, relationship="maps_to"
                ))

            coverage = "covered" if len(mapped_controls) >= len(categories) and mapped_controls else (
                "partial" if mapped_controls else "gap"
            )

            results.append(MappingResult(
                obligation_id=obligation_node_id,
                obligation_section=chunk.section,
                categories=categories,
                mapped_controls=mapped_controls,
                coverage=coverage,
            ))

        self.audit_log.record(make_entry(
            module="mapping",
            request_summary=f"map_document({doc_id})",
            output_summary=f"{len(results)} obligations mapped, "
                            f"{sum(1 for r in results if r.coverage == 'gap')} gaps found",
        ))

        return results

    def _find_matching_controls(self, categories: list[str]) -> list[str]:
        matches = []
        for control_node in self.graph_store.find_by_type("control"):
            control_categories = control_node.metadata.get("categories", [])
            if set(categories) & set(control_categories):
                matches.append(control_node.node_id)
        return matches
