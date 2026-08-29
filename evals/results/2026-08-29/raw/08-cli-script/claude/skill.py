```python
#!/usr/bin/env python3
"""Print a file's lines with duplicate lines removed, keeping the first occurrence."""

import argparse
import sys


def unique_lines(lines, case_insensitive=False):
    """Yield lines in their original order, skipping ones already yielded.

    Each line is compared without its trailing newline, so a final line with no
    newline still matches an earlier identical line. With case_insensitive set,
    "Foo" and "FOO" collapse to whichever appeared first, with its own casing.
    """
    seen = set()
    for line in lines:
        text = line.rstrip("\n")
        # casefold rather than lower: it also folds ß/ss, Turkish İ, and similar.
        dedupe_key = text.casefold() if case_insensitive else text
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        yield text


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a file's lines with duplicate lines removed, "
        "keeping the first occurrence and preserving order."
    )
    parser.add_argument("input_path", help="file to read")
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="treat lines differing only in case as duplicates",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        with open(args.input_path, encoding="utf-8") as input_file:
            for line in unique_lines(input_file, args.case_insensitive):
                print(line)
    except OSError as err:
        print(f"error: cannot read {args.input_path}: {err.strerror}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Usage:

```
$ python dedupe_lines.py words.txt
$ python dedupe_lines.py --case-insensitive words.txt
$ python dedupe_lines.py missing.txt
error: cannot read missing.txt: No such file or directory
$ echo $?
1
```

Decisions worth flagging:

- **Catching `OSError`, not just `FileNotFoundError`.** A directory path or an unreadable file produces the same clear one-line message instead of a traceback, and `err.strerror` supplies the specific reason.
- **Comparing lines without their trailing newline.** A file whose last line has no newline would otherwise treat `"foo"` and `"foo\n"` as distinct. The cost is that output always ends in a newline even when the input did not — the same behavior as `sort -u` and `uniq`.
- **`casefold()` over `lower()`** for `--case-insensitive`, since it is the operation defined for caseless matching rather than for display.
- **Streaming the file** rather than reading it whole, so memory scales with the number of *distinct* lines rather than total lines.

What I left alone: `unique_lines` takes any iterable of strings and does no I/O, so it is directly testable, but you didn't ask for tests and I didn't add a test file. I also didn't add a `-o/--output` flag or stdin support (`-` as the path) — both are easy additions, but neither was in the spec.