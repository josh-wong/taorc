## `dedupe_lines.py`

```python
#!/usr/bin/env python3
"""Print a file's lines with duplicate lines removed, keeping the first
occurrence and preserving the original order.
"""

import argparse
import os
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="dedupe_lines.py",
        description="Print a file's lines with duplicate lines removed, "
                    "keeping the first occurrence and preserving order.",
    )
    parser.add_argument(
        "input",
        metavar="FILE",
        help="path to the input file",
    )
    parser.add_argument(
        "-i", "--case-insensitive",
        action="store_true",
        help="treat lines that differ only in case as duplicates "
             "(the first occurrence's original casing is printed)",
    )
    return parser.parse_args(argv)


def fail(message, status=1):
    print(f"dedupe_lines.py: error: {message}", file=sys.stderr)
    sys.exit(status)


def dedupe(lines, case_insensitive=False, out=sys.stdout):
    """Write each first-seen line from `lines` to `out`.

    `lines` is an iterable of strings that may include trailing newlines;
    the newline is stripped for comparison and re-added on output.
    """
    seen = set()
    for line in lines:
        text = line.rstrip("\n")
        key = text.casefold() if case_insensitive else text
        if key in seen:
            continue
        seen.add(key)
        print(text, file=out)


def main(argv=None):
    args = parse_args(argv)
    path = args.input

    try:
        # Universal newlines mode: \r\n and \r are normalised to \n.
        with open(path, "r", encoding="utf-8") as f:
            dedupe(f, case_insensitive=args.case_insensitive)
    except FileNotFoundError:
        fail(f"file not found: {path}")
    except IsADirectoryError:
        fail(f"is a directory, not a file: {path}")
    except PermissionError:
        fail(f"permission denied: {path}")
    except UnicodeDecodeError:
        fail(f"file is not valid UTF-8 text: {path}")
    except OSError as exc:
        fail(f"could not read {path}: {exc.strerror or exc}")
    except BrokenPipeError:
        # e.g. piped into `head`; suppress the interpreter's shutdown warning.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Behaviour

```console
$ cat sample.txt
Apple
banana
apple
Banana
Apple
cherry

$ python3 dedupe_lines.py sample.txt
Apple
banana
apple
Banana
cherry

$ python3 dedupe_lines.py --case-insensitive sample.txt
Apple
banana
cherry

$ python3 dedupe_lines.py missing.txt
dedupe_lines.py: error: file not found: missing.txt
$ echo $?
1
```

### Notes

- Comparison is on the line's content with the trailing newline stripped, so
  `"foo\n"` and a final `"foo"` (no newline) count as duplicates; everything
  else — including leading/trailing spaces — must match exactly.
- Case-insensitive matching uses `str.casefold()`, which handles non-ASCII
  correctly (e.g. `STRASSE` / `straße`), while the printed text keeps the
  first occurrence's original casing.
- Output is streamed line by line, so only the set of distinct keys is held in
  memory rather than the whole file.
- Missing files, directories, unreadable files, and non-UTF-8 input all exit
  with status 1 and a message on stderr; malformed command lines exit with
  argparse's usual status 2.