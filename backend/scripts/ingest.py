import os, json, asyncio, asyncpg, requests, time
from pathlib import Path

OPENAI_KEY = os.getenv('OPENAI_API_KEY')
DATA_FILE = os.getenv('DATA_FILE', 'data/emails_5000.jsonl')
PG_CONN = os.getenv('DATABASE_URL', 'postgresql://postgres:example@db:5432/emaildb')

def get_embedding(text):
    # call OpenAI embeddings
    import requests, json, os
    url = 'https://api.openai.com/v1/embeddings'
    headers = {'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'}
    body = {'model': 'text-embedding-3-large', 'input': text}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()['data'][0]['embedding']

async def main():
    if not OPENAI_KEY:
        raise RuntimeError('OPENAI_API_KEY not set')
    p = Path(DATA_FILE)
    if not p.exists():
        raise RuntimeError(f'Data file {DATA_FILE} not found')
    conn = await asyncpg.connect(PG_CONN)
    # create extension and table (pgvector must be installed on server)
    await conn.execute("""CREATE EXTENSION IF NOT EXISTS vector;""")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id bigint primary key,
            subject text,
            body text,
            summary text,
            actions text[],
            priority text,
            created_at timestamp,
            embedding vector(1536)
        );
    """)
    idx = 0
    with p.open() as fh:
        for line in fh:
            idx += 1
            rec = json.loads(line)
            text = rec.get('subject','') + '\n' + rec.get('body','')
            emb = get_embedding(text)
            # insert
            await conn.execute("""
                INSERT INTO emails (id, subject, body, summary, actions, priority, created_at, embedding)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (id) DO NOTHING;
            """, rec['id'], rec['subject'], rec['body'], rec.get('summary',''), rec.get('actions',[]), rec.get('priority',''), rec.get('created_at'), emb)
            if idx % 100 == 0:
                print(f'Inserted {idx} records')
                time.sleep(0.1)
    await conn.close()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
