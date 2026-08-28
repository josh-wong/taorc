```python
#!/usr/bin/env python3
"""Deduplicate lines from a file, keeping the first occurrence."""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Remove duplicate lines from a file, keeping the first occurrence.'
    )
    
    parser.add_argument('input_file', help='Input file path')
    parser.add_argument('--case-insensitive', action='store_true', 
                        help='Treat lines differing only in case as duplicates')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Read and process lines
    seen = set()
    output_lines = []
    
    with open(args.input_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip trailing newline but preserve the rest of the line
            line_content = line.rstrip('\n').rstrip('\r')
            
            if args.case_insensitive:
                key = line_content.lower()
            else:
                key = line_content
            
            if key not in seen:
                seen.add(key)
                output_lines.append(line_content)
    
    # Print all unique lines to stdout
    for line in output_lines:
        print(line, end='')


if __name__ == '__main__':
    main()
```