"""Test retrieval with realistic Lab 5 questions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieve import retrieve, print_results


TEST_QUESTIONS = [
    "What is the RC time constant?",
    "How do I charge a capacitor in an RC circuit?",
    "What is the difference between polarized and non-polarized capacitors?",
    "How do I use the oscilloscope to measure voltage?",
    "What is switch debouncing and why is it needed?",
    "How do capacitors in series and parallel combine?",
    "What viewing mode should I use on the oscilloscope for signals in seconds?",
    "What happens when a capacitor is fully charged?",
    "How do I discharge a capacitor?",
    "What is a pull-up and pull-down resistor?",
]


def main():
    print("=" * 60)
    print("Lab 5 Retrieval Test Suite")
    print("=" * 60)

    for q in TEST_QUESTIONS:
        results = retrieve(q, lab_id="lab_5", top_k=3)
        print_results(q, results)
        print("-" * 60)


if __name__ == "__main__":
    main()
