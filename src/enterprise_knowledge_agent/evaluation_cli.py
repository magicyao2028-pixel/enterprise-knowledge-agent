from __future__ import annotations

import argparse
from pathlib import Path

from .evaluation import write_evaluation_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval, abstention and safety on a reviewed query set.")
    parser.add_argument("--corpus", type=Path, default=Path("data/knowledge.json"))
    parser.add_argument("--queries", type=Path, default=Path("data/evaluation_queries.json"))
    parser.add_argument("--json-output", type=Path, default=Path("reports/retrieval_evaluation.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("reports/retrieval_evaluation.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = write_evaluation_report(
        args.corpus,
        args.queries,
        args.json_output,
        args.markdown_output,
    )
    summary = report["summary"]
    print(
        f"Evaluation complete: {summary['passed_cases']}/{summary['case_count']} cases passed; "
        f"top-1 accuracy {summary['top1_accuracy']:.0%}."
    )


if __name__ == "__main__":
    main()
