"""
Prompt templates for the regulation Q&A / explainer module.
Kept separate from qa_engine.py so prompt wording can be iterated
on without touching retrieval or orchestration logic.
"""

SYSTEM_PROMPT = (
    "You are a regulatory compliance assistant for a bank's compliance team. "
    "Answer questions strictly using the provided regulatory text excerpts. "
    "If the excerpts do not contain enough information to answer confidently, "
    "say so explicitly rather than guessing. Always reference which section "
    "each part of your answer comes from. Do not provide legal advice; frame "
    "answers as informational summaries of the regulatory text."
)


def build_qa_prompt(question: str, chunks: list) -> str:
    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"[{c.chunk.regulator} — {c.chunk.section} — jurisdiction: {c.chunk.jurisdiction}]\n{c.chunk.text}"
        )
    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no matching excerpts found)"

    return (
        f"Regulatory excerpts:\n\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the excerpts above. Cite the section "
        "for each claim. If excerpts are insufficient, state that clearly."
    )
