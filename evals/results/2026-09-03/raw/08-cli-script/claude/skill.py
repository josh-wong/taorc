```python
#!/usr/bin/env python3
"""Print a file's lines with duplicates removed, keeping the first occurrence."""

import argparse
import sys


def unique_lines_in_order(lines, *, case_insensitive=False):
    """Yield each distinct line once, in the order it first appeared.

    Trailing newlines are stripped, so a final line with no newline still
    matches an identical earlier line. With case_insensitive set, "Foo" and
    "FOO" are duplicates and the first occurrence's casing is what's yielded.
    Empty input yields nothing.
    """
    seen_keys = set()
    for line in lines:
        line = line.rstrip("\n")
        # casefold rather than lower: it also folds cases lower() misses, e.g.
        # German "STRASSE" vs "Straße".
        key = line.casefold() if case_insensitive else line
        if key in seen_keys:
            continue
        seen_keys.add(key)
        yield line


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a file's lines with exact duplicates removed, "
        "keeping the first occurrence and preserving order.",
    )
    parser.add_argument("input_path", help="file to read; use - for stdin is not supported")
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="treat lines that differ only in case as duplicates",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.input_path, encoding="utf-8") as input_file:
            for line in unique_lines_in_order(
                input_file, case_insensitive=args.case_insensitive
            ):
                print(line)
    except OSError as error:
        reason = error.strerror or error
        print(f"{parser.prog}: {args.input_path}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Wait — that `input_path` help string describes a limitation instead of the argument. Fixing it:

```python
    parser.add_argument("input_path", help="file to read")
```

**Notes on a few choices**

- `unique_lines_in_order` is a generator, so the file streams rather than loading whole (`S3` — it does one job, and `main` handles I/O and CLI).
- `case_insensitive` is keyword-only at the call site, so the reader doesn't have to guess what a bare `True` means (`C17`).
- The two non-obvious decisions — stripping newlines before comparing, and `casefold` over `lower` — each get one line saying *why* (`C6`). The rest of the code says what it does on its own.
- `OSError` rather than `FileNotFoundError`: a path that's a directory or unreadable gets the same clear one-line message instead of a traceback. `error.strerror` keeps the message from repeating the path that's already in the string.

**What I deliberately left out**

- No `--output` flag, no stdin support, no `-` convention. Not asked for (`S6`).
- No handling for `UnicodeDecodeError`. The file is opened as UTF-8, so a Latin-1 file will raise a traceback rather than a clean message. The task scoped error handling to "file doesn't exist", so I didn't widen it — but it's the one rough edge if you expect arbitrary encodings. Say the word and I'll add `errors="surrogateescape"` or a second `except`.
- No tests, since none were requested. If you want them, the cases worth pinning are: empty file, all-unique, all-duplicate, case-differing pairs with and without the flag, and a final line lacking a newline.
- I found no `scripts/taorc_lint.py` under any of the standard skill roots, so the lint step was skipped rather than substituted with a guess.