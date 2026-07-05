"""
Structured metadata store: jurisdictions, regulators, effective dates,
document versions. Backed by SQLite here so it's a real persistent
store with zero setup (stdlib only). Swap for Postgres in production
by changing only the connection string / driver.
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class DocumentRecord:
    doc_id: str
    title: str
    jurisdiction: str
    regulator: str
    effective_date: str | None
    source_url: str | None


class MetadataStore:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                regulator TEXT NOT NULL,
                effective_date TEXT,
                source_url TEXT
            )
        """)
        self.conn.commit()

    def upsert_document(self, record: DocumentRecord) -> None:
        self.conn.execute("""
            INSERT INTO documents (doc_id, title, jurisdiction, regulator, effective_date, source_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                title=excluded.title,
                jurisdiction=excluded.jurisdiction,
                regulator=excluded.regulator,
                effective_date=excluded.effective_date,
                source_url=excluded.source_url
        """, (record.doc_id, record.title, record.jurisdiction, record.regulator,
              record.effective_date, record.source_url))
        self.conn.commit()

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        row = self.conn.execute(
            "SELECT doc_id, title, jurisdiction, regulator, effective_date, source_url "
            "FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        return DocumentRecord(*row) if row else None

    def list_by_jurisdiction(self, jurisdiction: str) -> list[DocumentRecord]:
        rows = self.conn.execute(
            "SELECT doc_id, title, jurisdiction, regulator, effective_date, source_url "
            "FROM documents WHERE jurisdiction = ?", (jurisdiction,)
        ).fetchall()
        return [DocumentRecord(*row) for row in rows]

    def all_documents(self) -> list[DocumentRecord]:
        rows = self.conn.execute(
            "SELECT doc_id, title, jurisdiction, regulator, effective_date, source_url FROM documents"
        ).fetchall()
        return [DocumentRecord(*row) for row in rows]
