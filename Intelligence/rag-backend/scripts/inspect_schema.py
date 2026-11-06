"""
One-off inspection script: discovers tables/columns exposed via Supabase's
PostgREST API, then samples rows from a candidate chunks table.

Never prints SUPABASE_SERVICE_KEY. Read-only: no writes are performed.
"""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}


def get_openapi_spec():
    """PostgREST serves an OpenAPI doc at the REST root describing every
    exposed table/view and its columns."""
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {**HEADERS, "Accept": "application/openapi+json"}
    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sample_rows(table: str, limit: int = 5):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {**HEADERS, "Accept": "application/json"}
    params = {"select": "*", "limit": str(limit)}
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        return {"error": resp.status_code, "body": resp.text[:500]}
    return resp.json()


def main():
    print("=== Fetching OpenAPI schema from PostgREST ===")
    try:
        spec = get_openapi_spec()
    except httpx.HTTPStatusError as e:
        print(f"FAILED to fetch schema: HTTP {e.response.status_code}")
        print(e.response.text[:1000])
        sys.exit(1)

    definitions = spec.get("definitions", {})
    paths = spec.get("paths", {})

    print(f"\nExposed tables/views ({len(definitions)}):")
    for name in sorted(definitions.keys()):
        print(f"  - {name}")

    # Dump full column info per table
    print("\n=== Column details ===")
    table_info = {}
    for name, defn in definitions.items():
        props = defn.get("properties", {})
        cols = {}
        for col_name, col_def in props.items():
            cols[col_name] = {
                "type": col_def.get("type"),
                "format": col_def.get("format"),
                "description": col_def.get("description"),
            }
        table_info[name] = cols
        print(f"\n[{name}]")
        for col_name, col_meta in cols.items():
            print(f"  {col_name}: {col_meta}")

    # Save full spec for later reference (no secrets inside)
    out_path = os.path.join(os.path.dirname(__file__), "..", "scratch_schema_dump.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"definitions": definitions, "paths": list(paths.keys())}, f, indent=2)
    print(f"\nFull OpenAPI dump saved to {out_path}")

    # Try to guess the chunks table
    candidates = [n for n in definitions if any(
        kw in n.lower() for kw in ["chunk", "document", "embedding", "vector", "lab"]
    )]
    print(f"\n=== Candidate chunk-holding tables: {candidates} ===")

    for table in candidates:
        print(f"\n--- Sampling 5 rows from '{table}' ---")
        rows = sample_rows(table, 5)
        if isinstance(rows, dict) and "error" in rows:
            print(f"  ERROR: {rows}")
            continue
        for i, row in enumerate(rows):
            shape = {k: (type(v).__name__, len(v) if isinstance(v, (list, str)) else None) for k, v in row.items()}
            print(f"  row[{i}] keys/shape: {shape}")
        if rows:
            print(f"\n  Full first row (truncated embedding if present):")
            first = dict(rows[0])
            for k, v in first.items():
                if isinstance(v, list) and len(v) > 20:
                    first[k] = f"<vector len={len(v)}> first5={v[:5]}"
            print(json.dumps(first, indent=2, default=str))


if __name__ == "__main__":
    main()
