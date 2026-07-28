"""
Splits raw regulatory text into retrievable chunks, tagged with
metadata (jurisdiction, regulator, section, effective date).

Chunking by section rather than fixed character windows matters here:
citing "Reg Y, Section 12(b)" is far more useful to a compliance
officer than "chunk #47".
"""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str
    text: str
    section: str
    jurisdiction: str
    regulator: str
    effective_date: str | None = None
    metadata: dict = field(default_factory=dict)


SECTION_PATTERN = re.compile(r"(?:^|\n)(Section\s+[\dA-Za-z().]+)", re.IGNORECASE)


def chunk_document(
    text: str,
    doc_id: str,
    jurisdiction: str,
    regulator: str,
    effective_date: str | None = None,
    max_chunk_chars: int = 1200,
) -> list[Chunk]:
    """
    Splits on detected section headers when present; otherwise falls
    back to fixed-size windows so nothing is dropped.
    """
    matches = list(SECTION_PATTERN.finditer(text))
    chunks: list[Chunk] = []

    if matches:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_label = match.group(1).strip()
            section_text = text[start:end].strip()
            for sub_idx, sub_text in enumerate(_split_long(section_text, max_chunk_chars)):
                chunks.append(Chunk(
                    chunk_id=f"{doc_id}::{section_label}::{sub_idx}",
                    text=sub_text,
                    section=section_label,
                    jurisdiction=jurisdiction,
                    regulator=regulator,
                    effective_date=effective_date,
                ))
    else:
        for idx, sub_text in enumerate(_split_long(text, max_chunk_chars)):
            chunks.append(Chunk(
                chunk_id=f"{doc_id}::chunk::{idx}",
                text=sub_text,
                section=f"chunk-{idx}",
                jurisdiction=jurisdiction,
                regulator=regulator,
                effective_date=effective_date,
            ))

    return chunks


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]
