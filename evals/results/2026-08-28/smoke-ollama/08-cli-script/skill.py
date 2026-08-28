```python
#!/usr/bin/env python3
"""Remove duplicate lines from a file while preserving order."""

import argparse
import sys


def parse_arguments():
    """Parse command-line arguments and validate input file exists."""
    parser = argparse.ArgumentParser(
        description="Remove duplicate lines from an input file."
    )
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Treat lines differing only in case as duplicates"
    )

    args = parser.parse_args()

    if not args.input_file:
        print("Error: No input file specified.", file=sys.stderr)
        sys.exit(1)

    return args


def load_lines(file_path, case_insensitive):
    """Load and yield lines from the input file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                yield line.rstrip("\n")
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)


def dedupe_lines(lines, case_insensitive):
    """Remove duplicate lines while preserving order."""
    seen = set()
    if case_insensitive:
        seen_case = set()

    for line in lines:
        key = line.lower() if case_insensitive else line
        if key not in seen and (key not in seen_case or not case_insensitive):
            yield line
            seen.add(key)
            if case_insensitive:
                seen_case.add(key)


def main():
    """Entry point for the script."""
    args = parse_arguments()

    lines = load_lines(args.input_file, args.case_insensitive)
    deduped = dedupe_lines(lines, args.case_insensitive)

    for line in deduped:
        print(line)


if __name__ == "__main__":
    main()
```