Write a command-line script `dedupe_lines.py` that:

- Takes one positional argument, an input file path.
- Prints the file's lines to stdout with exact duplicate lines removed,
  keeping the first occurrence and preserving order.
- Takes an optional `--case-insensitive` flag that treats lines differing
  only in case as duplicates (printing the first occurrence's original
  casing).
- Exits with a clear error message and non-zero status if the file doesn't
  exist.

Use the standard library only (`argparse` for the CLI).
