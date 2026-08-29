```python
#!/usr/bin/env python3
"""
dedupe_lines.py

Print lines from a file with exact duplicates removed, preserving order.

Usage:
    python dedupe_lines.py input.txt
    python dedupe_lines.py --case-insensitive input.txt
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, Set


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print file lines with duplicate lines removed, "
            "keeping the first occurrence and preserving order."
        )
    )
    parser.add_argument(
        "input_path",
        help="Path to the input text file.",
    )
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help=(
            "Treat lines differing only in letter case as duplicates. "
            "The first occurrence's original casing is printed."
        ),
    )
    return parser.parse_args(list(argv))


def dedupe_lines(
    lines: Iterable[str],
    case_insensitive: bool,
) -> Iterable[str]:
    seen_keys: Set[str] = set()

    for line in lines:
        key = line.lower() if case_insensitive else line
        if key in seen_keys:
            continue
        seen_keys.add(key)
        yield line


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    input_path = Path(args.input_path)

    if not input_path.is_file():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with input_path.open("r", encoding="utf-8") as input_file:
            for line in dedupe_lines(
                lines=input_file,
                case_insensitive=args.case_insensitive,
            ):
                # Lines already include their newline characters.
                sys.stdout.write(line)
    except OSError as error:
        print(f"Error: could not read file {input_path}: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```