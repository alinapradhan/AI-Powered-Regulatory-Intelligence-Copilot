# Regulatory Intelligence Copilot

A Python backend for a bank compliance copilot: explains regulations,
maps them to internal controls, generates reports, and flags
violations. Runs fully in-memory/SQLite with zero external
infrastructure — good for prototyping and testing the architecture
before wiring in real data sources.

## Install 

```bash
pip install -r requirements.txt --break-system-packages
```

## Configure (optional)

Set an API key to get real LLM completions instead of stub text:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Without it, everything still runs — `core/llm_client.py` returns a
clearly-marked stub response so you can test the full pipeline
offline.

## Run the API

```bash
uvicorn api.main:app --reload
```

Then try:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the affiliate transaction limit?", "jurisdiction": "US-Fed"}'

curl -X POST http://localhost:8000/map-requirements \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "reg-w-2024", "jurisdiction": "US-Fed"}'

curl -X POST http://localhost:8000/detect-violations \
  -H "Content-Type: application/json" \
  -d '{"policy_text": "Our affiliate exposure policy.", "policy_facts": {"affiliate_single_pct": 15.0}, "applicable_regs": ["reg-w-2024"]}'

curl -X POST http://localhost:8000/generate-report \
  -H "Content-Type: application/json" \
  -d '{"title": "Q3 Compliance Report", "jurisdiction": "US-Fed", "doc_ids": ["reg-w-2024"]}'
```

## Run tests

```bash
pytest tests/ -v
```

## Structure

```
api/                    FastAPI routes + request/response schemas
orchestration/router.py  Intent classification and module dispatch
modules/
  explainer/              RAG-based Q&A over regulations
  compliance_mapping/      Maps obligations to internal controls
  report_generator/       Assembles markdown compliance reports
  violation_detector/     Rules engine + LLM qualitative review
knowledge/
  ingestion/              Fetches, chunks, and embeds regulatory text
  vector_store.py         In-memory semantic search
  graph_store.py          Obligation/control relationship graph
  metadata_store.py       SQLite store for document metadata
core/
  llm_client.py           Anthropic API wrapper (with offline stub)
  audit_log.py            Logs every answer/mapping/report/violation
  config.py               Central settings
tests/                    Pytest suite (runs without an API key)
```

## Design notes

- **Vector search is dependency-free.** `knowledge/ingestion/embedder.py`
  uses a hashed bag-of-words vector so the whole system runs without
  calling an external embedding API. Swap `embed_text` for a real
  embedding model call when you have production infrastructure.
- **Rules engine is the authoritative gate for violations.**
  `modules/violation_detector/rules_engine.py` handles explicit
  numeric/threshold checks; the LLM only adds qualitative findings on
  top, in `modules/violation_detector/scanner.py`.
- **Everything is audited.** `core/audit_log.py` writes a JSONL trail
  of every request, its sources, and the model used — needed to make
  this usable as compliance evidence rather than just a chat answer.
- **Sample data included.** `knowledge/ingestion/fetch_sources.py`
  ships with three sample regulations (Reg W, Basel III, FCA Consumer
  Duty) so you can run the whole system immediately. Replace
  `SourceFetcher` methods with real regulator API/feed calls for
  production use.
