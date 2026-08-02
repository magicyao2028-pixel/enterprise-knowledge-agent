from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import KnowledgeAgent
from .corpus import load_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a local enterprise knowledge corpus with citations.")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--corpus", type=Path, default=Path("data/knowledge.json"), help="Knowledge JSON file")
    parser.add_argument("--top-k", type=int, default=3, help="Maximum number of retrieved documents")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON answer")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    answer = KnowledgeAgent(load_documents(args.corpus), top_k=args.top_k).ask(args.query)
    rendered = json.dumps(answer, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Answer written to {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
