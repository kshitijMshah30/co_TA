"""Run once the GPU LLM backend is reachable again. Hits the running API's
/health and /ask endpoints and checks for a real (non-mock) answer."""
import os
import sys

import httpx

API_BASE = os.environ.get("SMOKE_TEST_API_BASE", "http://localhost:8000")


def main():
    health = httpx.get(f"{API_BASE}/health", timeout=10)
    assert health.status_code == 200, f"/health failed: {health.status_code}"
    print("/health OK")

    resp = httpx.post(
        f"{API_BASE}/ask",
        json={"question": "What is the RC time constant?", "lab": "lab_5", "k": 5},
        timeout=30,
    )
    assert resp.status_code == 200, f"/ask failed: {resp.status_code} {resp.text}"
    data = resp.json()

    if data["answer"].startswith("[MOCK LLM RESPONSE]"):
        print(
            "WARNING: got a mock response. Set LLM_BACKEND=openai_compatible "
            "and point LLM_API_BASE at the GPU server before running this.",
            file=sys.stderr,
        )
        sys.exit(1)

    assert not data["below_threshold"], "Expected an in-scope answer with content"
    assert len(data["sources"]) > 0, "Expected at least one source"
    print("Answer:", data["answer"][:300])
    print("Sources:", data["sources"])
    print("Scores:", data["scores"])
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
