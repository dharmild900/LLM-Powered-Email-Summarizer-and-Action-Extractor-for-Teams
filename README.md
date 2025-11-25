# Enterprise Email Summarizer (RAG + OpenAI + pgvector)

This repository contains a production-style example of an email summarization and action extraction service using Retrieval-Augmented Generation (RAG). It includes:
- FastAPI backend with RAG pipeline
- Ingestion script that uses OpenAI embeddings (text-embedding-3-large) and stores embeddings in Postgres (pgvector)
- React frontend demo
- Docker Compose to run Postgres (with pgvector), backend, and frontend
- 5,000-record synthetic dataset for development and testing (`data/emails_5000.jsonl`)

## Architecture
1. Ingest emails -> compute embeddings -> store in Postgres 'emails' table with `vector` column.
2. On summarize request, retrieve top-K similar emails using pgvector similarity, build a prompt with examples, and call OpenAI Chat Completion to produce a concise summary + actions.
3. Frontend sends email subject/body, backend returns summary and actions.

## Quickstart (local)
1. Copy the repository and set `OPENAI_API_KEY` environment variable (do **not** commit it):
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
2. Start local infra:
   ```bash
   docker compose up --build
   ```
3. In a new shell, run the ingestion to populate the DB (wait until Postgres is ready):
   ```bash
   docker compose exec backend python app/scripts/ingest.py
   ```
4. Open frontend at http://localhost:3000

## Important notes
- The ingest script calls the OpenAI Embeddings API and will consume credits. Use sparingly and consider creating embeddings offline or caching them.
- Postgres must have the `pgvector` extension available. The compose file tries to preload it; on some systems you may need to install `postgresql-15-pgvector` or adapt the image.
- Do **not** store your OpenAI API key in the repository. Use environment variables or secret managers.
- This project is meant as a realistic template. For production consider adding:
  - Authentication & authorization (JWT/OAuth)
  - Rate limiting, retries, and backoff for OpenAI requests
  - Monitoring, metrics, and observability
  - CI/CD for ingestion and deployment
  - Unit and integration tests

## Files of interest
- `data/emails_5000.jsonl` - synthetic dataset (5,000 records)
- `backend/app/main.py` - FastAPI app (RAG + OpenAI)
- `backend/scripts/ingest.py` - ingestion script (embeddings)
- `docker-compose.yml` - infra
