import os
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional
    import asyncpg
    import asyncio
    import json
    from pathlib import Path

    app = FastAPI(title="Enterprise Email Summarizer (RAG + OpenAI)")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PG_CONN = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/emaildb")

    class EmailRequest(BaseModel):
        subject: str
        body: str
        top_k: Optional[int] = 5

    class EmailResponse(BaseModel):
        summary: str
        actions: List[str]

    async def get_pg_conn():
        return await asyncpg.connect(PG_CONN)

    async def retrieve_similar(conn, text, k=5):
        # Uses pgvector cosine similarity. Expects table 'emails' with column 'embedding' vector(1536)
        rows = await conn.fetch("""
            SELECT id, subject, body, summary, actions, created_at 
            FROM emails 
            ORDER BY embedding <#> $1
            LIMIT $2;
        """, text, k)
        return [dict(r) for r in rows]

    async def call_openai_chat(prompt: str):
        # Uses OpenAI REST via requests to avoid blocking loop for users without SDK; here we try simple pattern
        import requests, os, time
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.2
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def extract_from_openai(resp_json):
        try:
            text = resp_json['choices'][0]['message']['content'].strip()
        except Exception:
            text = str(resp_json)
        # try JSON parse
        import json as _json
        try:
            parsed = _json.loads(text)
            return parsed.get('summary', text), parsed.get('actions', [])
        except Exception:
            # fallback: heuristics
            parts = text.split('\n\n')
            summary = parts[0]
            actions = []
            for line in parts[1:]:
                for l in line.split('\n'):
                    l = l.strip()
                    if l and (l[0] in ['-','*'] or l.lower().startswith('action')):
                        actions.append(l.lstrip('-* ').strip())
            return summary, actions

    @app.post('/summarize', response_model=EmailResponse)
    async def summarize(req: EmailRequest):
        # Connect to DB, retrieve similar emails (raw text stored as embeddings input), then call OpenAI for final summary
        try:
            conn = await get_pg_conn()
            sim = await conn.fetch("""
                SELECT id, subject, body, summary, actions, created_at 
                FROM emails
                ORDER BY embedding <#> $1
                LIMIT $2;
            """, req.body, req.top_k)
            similar = [dict(r) for r in sim]
            # Compose prompt for RAG
            prompt = """You are an assistant that summarizes the following email and extracts action items. Use the examples in 'context_examples' to inform style.

Context examples:\n"""
            for s in similar:
                prompt += f"Example subject: {s['subject']}\nExample body: {s['body']}\nExample summary: {s['summary']}\nExample actions: {s['actions']}\n\n"""
            prompt += f"\nEmail Subject: {req.subject}\nEmail Body: {req.body}\n\nRespond in JSON: {{ \"summary\": \"...\", \"actions\": [\"...\"] }}"

            # Call OpenAI
            resp = await asyncio.get_event_loop().run_in_executor(None, lambda: call_openai_chat(prompt))
            summary, actions = extract_from_openai(resp)
            await conn.close()
            return EmailResponse(summary=summary, actions=actions)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
