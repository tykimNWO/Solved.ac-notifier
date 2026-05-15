#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.rating.class_fetcher import fetch_class_problem_groups, save_class_problem_groups


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch solved.ac CLASS problem lists into src/data/classProblems.json")
    parser.add_argument(
        "--class",
        dest="classes",
        type=int,
        action="append",
        help="CLASS level to fetch. Can be repeated. Defaults to 1..10.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "src" / "data" / "classProblems.json"),
        help="Output cache path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    class_levels = args.classes or list(range(1, 11))
    groups = fetch_class_problem_groups(class_levels)
    save_class_problem_groups(groups, args.output)
    total = sum(len(group.get("problems", [])) for group in groups)
    print(f"Saved {len(groups)} CLASS groups / {total} problems to {args.output}")


if __name__ == "__main__":
    main()
