```python
#!/usr/bin/env python3
"""
Print file lines with exact duplicates removed, preserving the first occurrence.

Behavior:
- Lines are compared exactly by default.
- With --case-insensitive, lines are considered duplicates if they differ
  only in case; the first occurrence's original casing is printed.
- If the input file does not exist or cannot be opened, an error message
  is printed to stderr and the program exits with a non-zero status.
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, Set


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print file lines with duplicate lines removed."
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
    Yield lines from `lines`, skipping duplicates.

    - If `case_insensitive` is False, duplicates are lines that are exactly equal.
    - If `case_insensitive` is True, duplicates are lines whose lowercase
      representations are equal.
    - The first occurrence of each unique line is yielded, preserving order.
    """
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
            for unique_line in iter_unique_lines(
                input_file,
                case_insensitive=args.case_insensitive,
            ):
                # Lines already include their newline terminators.
                sys.stdout.write(unique_line)
    except OSError as open_error:
        print(f"Error: could not read file {input_path}: {open_error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```