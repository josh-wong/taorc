```python
#!/usr/bin/env python3
"""
Print file lines with exact duplicates removed, preserving first occurrence.

Behavior:
- Lines are compared exactly by default.
- With --case-insensitive, lines are compared case-insensitively, but the
  first occurrence's original casing is printed.
- Order of first occurrences is preserved.
- Exits non-zero with a clear error message if the file does not exist
  or cannot be read.
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, Set


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print file lines with duplicates removed, preserving order."
    )
    parser.add_argument(
        "input_path",
        help="Path to the input text file.",
    )
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Treat lines differing only in case as duplicates.",
    )
    return parser.parse_args(list(argv))


def iter_unique_lines(
    lines: Iterable[str],
    case_insensitive: bool,
) -> Iterable[str]:
    """
    Yield unique lines from the given iterable, preserving first occurrence.

    On empty input, yields nothing.
    Never raises for duplicates; only propagates exceptions from the input
    iterator.
    """
    seen_keys: Set[str] = set()

    for line in lines:
        line_key = line.lower() if case_insensitive else line
        if line_key in seen_keys:
            continue
        seen_keys.add(line_key)
        yield line


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    input_path = Path(args.input_path)

    if not input_path.is_file():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with input_path.open("r", encoding="utf-8") as input_file:
            for unique_line in iter_unique_lines(
                input_file,
                case_insensitive=args.case_insensitive,
            ):
                # Lines already include their newline terminators.
                sys.stdout.write(unique_line)
    except OSError as error:
        print(f"Error: could not read file {input_path}: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```