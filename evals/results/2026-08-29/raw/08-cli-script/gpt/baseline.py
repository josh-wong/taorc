```python
#!/usr/bin/env python3
import argparse
import os
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print file lines with exact duplicates removed, "
                    "preserving order and keeping the first occurrence."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input text file."
    )
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Treat lines differing only in case as duplicates."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.input_file

    if not os.path.isfile(path):
        sys.stderr.write(f"Error: file not found: {path}\n")
        return 1

    seen = set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                key = line.lower() if args.case_insensitive else line
                if key in seen:
                    continue
                seen.add(key)
                # Print exactly as in the file (including newline)
                sys.stdout.write(line)
    except OSError as e:
        sys.stderr.write(f"Error reading file '{path}': {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```