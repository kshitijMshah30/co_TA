"""Ask co_TA from the terminal (from the Intelligence folder):

    python -m rag.cli "What does the time constant tell me?"
    python -m rag.cli --lab lab_5 --show-sources "How do I trigger the oscilloscope?"
"""

import argparse

from .config import Settings
from .pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the co_TA RAG pipeline a question.")
    parser.add_argument("question")
    parser.add_argument("--lab", default="lab_5")
    parser.add_argument("--show-sources", action="store_true")
    args = parser.parse_args()

    ans = Pipeline(Settings.from_env()).ask(args.lab, args.question)
    print(ans.reply)
    if args.show_sources:
        print("\nSources:")
        for s in ans.sources:
            print(f"  chunk {s.chunk_id}  p{s.page_start}-{s.page_end}  {s.type or 'untagged':18}  sim={s.similarity:.3f}")
    flags = [n for n in ("out_of_scope", "assessed_question_in_context", "escalate_to_ta", "emergency")
             if getattr(ans, n)]
    print(f"\n[{ans.llm_backend} | {ans.latency_ms} ms | flags: {', '.join(flags) or 'none'}]")


if __name__ == "__main__":
    main()
