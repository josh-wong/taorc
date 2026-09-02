`dedupe_lines.py`:

```python
#!/usr/bin/env python3
"""Print a file's lines with duplicate lines removed, keeping the first occurrence."""

import argparse
import sys
from collections.abc import Iterable, Iterator

PROGRAM_NAME = "dedupe_lines.py"


def unique_lines(
    lines: Iterable[str], *, case_insensitive: bool = False
) -> Iterator[str]:
    """Yield lines in their original order, skipping repeats of an earlier line.

    Each line is yielded with the casing of its first occurrence, so with
    case_insensitive=True the input ["Foo\\n", "foo\\n"] yields ["Foo\\n"].
    """
    seen_keys = set()
    for line in lines:
        key = line.lower() if case_insensitive else line
        if key in seen_keys:
            continue
        seen_keys.add(key)
        yield line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Print a file's lines with duplicate lines removed.",
    )
    parser.add_argument("path", help="file to read")
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="treat lines that differ only in case as duplicates",
    )
    args = parser.parse_args(argv)

    try:
        # Iterating the open file streams the input, so a huge file costs memory
        # only for the set of distinct lines.
        with open(args.path, encoding="utf-8") as input_file:
            for line in unique_lines(
                input_file, case_insensitive=args.case_insensitive
            ):
                # write() rather than print(): lines already carry their own
                # newline, and a final line without one should stay that way.
                sys.stdout.write(line)
    except OSError as error:
        print(
            f"{PROGRAM_NAME}: {args.path}: {error.strerror or error}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Behavior:

```
$ printf 'a\nB\nb\na\n' > f.txt
$ python dedupe_lines.py f.txt
a
B
b
$ python dedupe_lines.py --case-insensitive f.txt
a
B
$ python dedupe_lines.py missing.txt; echo "exit=$?"
dedupe_lines.py: missing.txt: No such file or directory
exit=1
```

**Notes on choices**

- `unique_lines` takes any iterable of strings rather than a path, so it is testable without touching the filesystem and the file handling stays in `main`.
- The docstring states the corner case that a caller can't infer from the signature — which casing survives when two lines match case-insensitively — with a worked input and output rather than a description.
- Catching `OSError` rather than `FileNotFoundError` also covers a path that is a directory or unreadable, and `strerror` gives the same wording the OS uses.

**What I deliberately did not do**

- No `BrokenPipeError` special case. Piping to `head` will print `dedupe_lines.py: f.txt: Broken pipe` and exit 1 instead of exiting quietly. Say the word if that matters and I'll add the two-line handler.
- No handling for non-UTF-8 input; a `UnicodeDecodeError` will traceback rather than print a clean message. Add `errors="surrogateescape"` if you need byte-preserving passthrough.