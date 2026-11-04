# AI TA Intelligence — Phase 1

Text-first RAG pipeline for Purdue ECE lab courses. Parses lab manuals, chunks them, creates embeddings, and stores everything in **Supabase Postgres + pgvector** for semantic retrieval.

## Architecture

```
Lab 5 PDF → parser → chunker → embedding model → Supabase pgvector

Student question → query embedding → pgvector similarity search → top-k chunks → (optional LLM) → answer
```

## Setup

### 1. Supabase Project

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → Database** and copy the **direct connection string** (URI tab)
3. It will look like: `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres`
4. If your password has special characters, percent-encode them (e.g. `!` → `%21`)

### 2. Database Setup

Go to **SQL Editor** in the Supabase dashboard and run the contents of `supabase_setup.sql`. This creates:
- `vector` extension
- `documents` table
- `chunks` table (with `vector(384)` embedding column)
- HNSW index for cosine similarity
- `match_chunks` function

Or run it programmatically:
```bash
python scripts/init_db.py
```

### 3. Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
OPENAI_API_KEY=           # optional — leave blank to use local embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
TOP_K=5
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Ingest Lab 5

Place the Lab 5 PDF at `data/lab5_manual.pdf`, then:

```bash
python scripts/ingest_lab5.py
```

Expected output:
```
Loading: lab5_manual.pdf
Pages parsed: 12
Chunks created: 46
Embedded 46 texts in 5.1s (local/all-MiniLM-L6-v2)
Rows inserted: 46
Lab lab_5 ingestion complete.
```

### 6. Test Retrieval

```bash
python -m src.retrieve "What is the RC time constant?"
```

Or run the full test suite:
```bash
python scripts/test_retrieval.py
```

## Inspecting Data in Supabase

Your team can view the data directly in the Supabase dashboard:

1. Go to **Table Editor** in the left sidebar
2. Select `documents` to see ingested labs
3. Select `chunks` to see all chunks with their section, page, content, and metadata
4. The `embedding` column stores the 384-dimensional vectors

You can also run SQL queries in the **SQL Editor**:
```sql
SELECT section, page_start, content FROM chunks WHERE lab_id = 'lab_5' ORDER BY chunk_index;
```

## Embedding Model

- **Default (no API key):** `all-MiniLM-L6-v2` — 384-dimensional, runs locally
- **With OpenAI key:** `text-embedding-3-small` — 1536-dimensional

If switching models, update `EMBEDDING_DIMENSION` in `.env` and the `vector()` dimension in the database schema, then re-ingest.

## Project Structure

```
ai-ta-intelligence/
├── data/
│   └── lab5_manual.pdf
├── src/
│   ├── config.py          # Environment + settings
│   ├── db.py              # Postgres connection
│   ├── parser.py          # PDF text extraction
│   ├── chunking.py        # Heading-aware chunking
│   ├── embeddings.py      # Embedding provider abstraction
│   ├── ingest.py          # Full ingestion pipeline
│   └── retrieve.py        # Semantic search + CLI
├── scripts/
│   ├── init_db.py         # Create tables programmatically
│   ├── ingest_lab5.py     # Ingest Lab 5
│   └── test_retrieval.py  # 10 retrieval test queries
├── supabase_setup.sql     # SQL to run in Supabase dashboard
├── requirements.txt
├── .env.example
└── .gitignore
```
