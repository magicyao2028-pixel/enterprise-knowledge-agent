from __future__ import annotations

import argparse
from pathlib import Path

from .trial import write_trial_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline reviewer trial and evidence checks.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--json-output", type=Path, default=Path("reports/trial_report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("reports/trial_report.md"))
    args = parser.parse_args()
    report = write_trial_report(args.root, args.json_output, args.markdown_output)
    print(f"Trial {'passed' if report['overall_passed'] else 'failed'}: {args.json_output}")
    raise SystemExit(0 if report["overall_passed"] else 1)


if __name__ == "__main__":
    main()
