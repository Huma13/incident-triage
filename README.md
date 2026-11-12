# Production Incident Triage and Runbook Assistant

UE24AM342AA5 Mini Project 08. Multi-agent service that takes a PostgreSQL alert plus on-call note, retrieves documentation, proposes a cause class and severity with citations, and routes or escalates. It never executes remediation.

Team: Huma (PES2UG24AM066), Neeraj (PES2UG24AM046), Jaswanth (PES2UG24AM068)

## Quick start (macOS)
```bash
git clone <repo-url> incident-triage && cd incident-triage
cp .env.example .env        # fill LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_ID
docker compose up --build -d
curl localhost:8000/health
```

## Submit an incident
```bash
curl -X POST localhost:8000/api/v1/runs -H 'content-type: application/json' \
  -d @evaluation/case_4_1.json
curl localhost:8000/api/v1/runs/<run_id>
```

## Run tests
```bash
docker compose run --rm api pytest
```

## Layout
See `docs/EVAL1_corpus_confirmation.md` for the corpus and the section 4.1 reference case.

## Status
- [x] Stage 0: skeleton, contract, queue, quarantine
- [ ] Stage 1: ingestion (Chroma + BM25)
- [ ] Stage 3: LangGraph agents
- [ ] Stages 4-8: see implementation guide
