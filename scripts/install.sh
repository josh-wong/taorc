#!/usr/bin/env bash
# taorc installer -- see v1-design-doc.md §6.3 and §9 item 8.
#
# Places the taorc managed block (templates/agent-block.md, wrapped in
# <!-- taorc:begin/end --> markers) into every instructions file an installed
# harness reads, plus a copy of the skill directory for harnesses that read
# SKILL.md directly. Never touches anything outside the markers in a file
# that already exists, so it is safe to run against a project's own
# AGENTS.md / CLAUDE.md.
#
# Written in POSIX-ish bash + awk, not Python: this is the "curl | bash"
# path, and requiring a Python interpreter on every machine that runs it
# would work against that promise. Tested against bash 3.2 (macOS's default
# /bin/bash), so no associative arrays or other bash-4-only features.
#
# Usage:
#   install.sh [--project | --global] [--dir PATH] [--source PATH]
#               [--agents LIST] [--detect] [--uninstall] [--help]
#
#   --project        Install into the current project (default). Combine
#                     with --dir to target a different project directory.
#   --global          Install into $HOME instead of a project.
#   --dir PATH        Target directory for --project (default: $PWD).
#   --source PATH     A local taorc checkout to install from, instead of
#                     downloading one. Mainly for testing and offline use.
#   --agents LIST     Comma-separated subset of: claude, copilot, cursor,
#   --agents=LIST     cline, windsurf, gemini, agents. Default: all.
#   --detect          Only refresh adapters that are already installed;
#                     never create a new one.
#   --uninstall       Remove the taorc managed block from every adapter and
#                     delete the skill directory copies. Leaves any content
#                     outside the markers untouched.
#   --help            Show this message.
#
# Environment:
#   TAORC_REF         Branch, tag, or commit SHA to download when --source
#                     is not given, such as v1.0.0. Default: main. Fetch
#                     this script from the same ref you pin, or a newer
#                     installer runs against older files.

set -euo pipefail

REPO_SLUG="josh-wong/taorc"
ALL_AGENTS="claude copilot cursor cline windsurf gemini agents"

usage() {
    # Not derived from $0 (e.g. via sed): the documented install method is
    # `curl ... | bash`, where $0 is "bash", not this file's path, so
    # anything reading $0 as a file silently breaks for that exact flow.
    cat <<'EOF'
taorc installer -- see v1-design-doc.md §6.3 and §9 item 8.

Places the taorc managed block (templates/agent-block.md, wrapped in
<!-- taorc:begin/end --> markers) into every instructions file an installed
harness reads, plus a copy of the skill directory for harnesses that read
SKILL.md directly. Never touches anything outside the markers in a file
that already exists, so it is safe to run against a project's own
AGENTS.md / CLAUDE.md.

Usage:
  install.sh [--project | --global] [--dir PATH] [--source PATH]
              [--agents LIST] [--detect] [--uninstall] [--help]

  --project        Install into the current project (default). Combine
                    with --dir to target a different project directory.
  --global          Install into $HOME instead of a project.
  --dir PATH        Target directory for --project (default: $PWD).
  --source PATH     A local taorc checkout to install from, instead of
                    downloading one. Mainly for testing and offline use.
  --agents LIST     Comma-separated subset of: claude, copilot, cursor,
  --agents=LIST     cline, windsurf, gemini, agents. Default: all.
  --detect          Only refresh adapters that are already installed;
                    never create a new one.
  --uninstall       Remove the taorc managed block from every adapter and
                    delete the skill directory copies. Leaves any content
                    outside the markers untouched.
  --help            Show this message.

Environment:
  TAORC_REF         Branch, tag, or commit SHA to download when --source
                    is not given, such as v1.0.0. Default: main. Fetch
                    this script from the same ref you pin, or a newer
                    installer runs against older files.
EOF
}

log() {
    printf 'taorc-install: %s\n' "$1"
}

die() {
    printf 'taorc-install: error: %s\n' "$1" >&2
    exit 1
}

# ---- argument parsing ------------------------------------------------

SCOPE="project"
TARGET_DIR=""
SOURCE_DIR=""
AGENTS_LIST="$ALL_AGENTS"
DETECT=0
UNINSTALL=0

while [ $# -gt 0 ]; do
    case "$1" in
        --project) SCOPE="project" ;;
        --global) SCOPE="global" ;;
        --dir)
            shift
            [ $# -gt 0 ] || die "--dir requires a path"
            TARGET_DIR="$1"
            ;;
        --source)
            shift
            [ $# -gt 0 ] || die "--source requires a path"
            SOURCE_DIR="$1"
            ;;
        --agents)
            shift
            [ $# -gt 0 ] || die "--agents requires a comma-separated list"
            AGENTS_LIST="$(printf '%s' "$1" | tr ',' ' ')"
            ;;
        --agents=*)
            AGENTS_LIST="$(printf '%s' "${1#--agents=}" | tr ',' ' ')"
            ;;
        --detect) DETECT=1 ;;
        --uninstall) UNINSTALL=1 ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            die "unrecognized argument: $1 (see --help)"
            ;;
    esac
    shift
done

for agent in $AGENTS_LIST; do
    case " $ALL_AGENTS " in
        *" $agent "*) ;;
        *) die "unknown --agents value '$agent' (choose from: $ALL_AGENTS)" ;;
    esac
done

# On Windows, a caller that doesn't itself run under MSYS (e.g. a Python
# subprocess) may hand this script a native "C:\..." path, since args bypass
# shell parsing and arrive with backslashes intact. Everything below (mkdir
# -p "$(dirname ...)", string prefix-stripping, etc.) assumes '/', so
# normalize any path-shaped argument once at the boundary. cygpath -u is the
# canonical MSYS/Cygwin converter and passes non-Windows-shaped paths (e.g.
# already-POSIX ones) through unchanged; on a non-Windows machine cygpath
# does not exist at all, so this is a no-op there.
normalize_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -u "$1"
    else
        printf '%s\n' "$1"
    fi
}

[ -n "$TARGET_DIR" ] && TARGET_DIR="$(normalize_path "$TARGET_DIR")"
[ -n "$SOURCE_DIR" ] && SOURCE_DIR="$(normalize_path "$SOURCE_DIR")"

if [ "$SCOPE" = "global" ]; then
    [ -n "$TARGET_DIR" ] && die "--dir cannot be combined with --global"
    TARGET_DIR="$HOME"
elif [ -z "$TARGET_DIR" ]; then
    TARGET_DIR="$PWD"
fi

[ -d "$TARGET_DIR" ] || die "target directory does not exist: $TARGET_DIR"

# ---- resolve the taorc source tree ------------------------------------

DOWNLOAD_DIR=""
WORK_DIR="$(mktemp -d)"
cleanup() {
    [ -n "$DOWNLOAD_DIR" ] && rm -rf "$DOWNLOAD_DIR"
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

if [ -z "$SOURCE_DIR" ]; then
    REF="${TAORC_REF:-main}"
    command -v curl >/dev/null 2>&1 || die "curl is required to download taorc (or pass --source)"
    command -v tar >/dev/null 2>&1 || die "tar is required to unpack taorc (or pass --source)"
    DOWNLOAD_DIR="$(mktemp -d)"
    # The ref-agnostic archive path, not refs/heads/, so a release tag or a
    # commit SHA resolves as well as a branch.
    ARCHIVE_URL="https://github.com/${REPO_SLUG}/archive/${REF}.tar.gz"
    log "downloading ${ARCHIVE_URL}"
    curl -fsSL "$ARCHIVE_URL" -o "$DOWNLOAD_DIR/taorc.tar.gz" \
        || die "failed to download $ARCHIVE_URL (check that TAORC_REF names an existing branch, tag, or commit; release tags start with v. Or pass --source for an offline install.)"
    tar -xzf "$DOWNLOAD_DIR/taorc.tar.gz" -C "$DOWNLOAD_DIR" \
        || die "tar exited $? while extracting the archive downloaded from $ARCHIVE_URL; see tar's error above (pass --source for an offline install)"
    SOURCE_DIR="$(find "$DOWNLOAD_DIR" -maxdepth 1 -type d -name 'taorc-*' | head -n1)"
    # Reachable even when tar succeeds: bsdtar, macOS's tar, exits 0 on an
    # empty download.
    [ -n "$SOURCE_DIR" ] \
        || die "no taorc source found in the archive downloaded from $ARCHIVE_URL (the download may be empty or not a taorc archive; pass --source for an offline install)"
fi

[ -f "$SOURCE_DIR/VERSION" ] || die "$SOURCE_DIR does not look like a taorc checkout (no VERSION file)"
[ -d "$SOURCE_DIR/skills/readable-code" ] || die "$SOURCE_DIR is missing skills/readable-code"

VERSION="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION")"
BEGIN_PREFIX="<!-- taorc:begin"
END_MARKER="<!-- taorc:end -->"

BLOCK_FILE="$WORK_DIR/block.md"
{
    printf '%s v%s -->\n' "$BEGIN_PREFIX" "$VERSION"
    awk '
        { lines[NR] = $0 }
        END {
            first = 1
            last = NR
            while (first <= last && lines[first] == "") first++
            while (last >= first && lines[last] == "") last--
            for (i = first; i <= last; i++) print lines[i]
        }
    ' "$SOURCE_DIR/templates/agent-block.md"
    printf '%s\n' "$END_MARKER"
} > "$BLOCK_FILE"

CURSOR_FRONTMATTER_FILE="$WORK_DIR/cursor-frontmatter.txt"
cat > "$CURSOR_FRONTMATTER_FILE" <<'EOF'
---
description: Write, comment, and review code so the next reader understands it in the least time.
alwaysApply: true
---

EOF

COPILOT_INSTRUCTIONS_FRONTMATTER_FILE="$WORK_DIR/copilot-instructions-frontmatter.txt"
cat > "$COPILOT_INSTRUCTIONS_FRONTMATTER_FILE" <<'EOF'
---
applyTo: "**/*"
---

EOF

# ---- per-agent target lists --------------------------------------------

# Each line: kind:relative-path:frontmatter-file (frontmatter-file empty for none)
agent_targets() {
    case "$1" in
        claude)
            printf 'block:AGENTS.md:\n'
            printf 'block:CLAUDE.md:\n'
            printf 'skill:.claude/skills/readable-code:\n'
            ;;
        copilot)
            printf 'block:.github/copilot-instructions.md:\n'
            printf 'block:.github/instructions/readable-code.instructions.md:%s\n' "$COPILOT_INSTRUCTIONS_FRONTMATTER_FILE"
            printf 'skill:.github/skills/readable-code:\n'
            ;;
        cursor)
            printf 'block:.cursor/rules/readable-code.mdc:%s\n' "$CURSOR_FRONTMATTER_FILE"
            ;;
        cline)
            printf 'block:.clinerules/readable-code.md:\n'
            ;;
        windsurf)
            printf 'block:.windsurf/rules/readable-code.md:\n'
            printf 'block:AGENTS.md:\n'
            ;;
        gemini)
            printf 'block:GEMINI.md:\n'
            ;;
        agents)
            printf 'block:AGENTS.md:\n'
            ;;
        *)
            die "unknown agent: $1"
            ;;
    esac
}

TARGETS_FILE="$WORK_DIR/targets.txt"
: > "$TARGETS_FILE"
for agent in $AGENTS_LIST; do
    agent_targets "$agent" >> "$TARGETS_FILE"
done
sort -u -t: -k1,2 "$TARGETS_FILE" -o "$TARGETS_FILE"

# ---- apply / remove one managed block -----------------------------------

apply_block() {
    target="$1"
    frontmatter_file="$2"

    if [ "$DETECT" = "1" ] && [ ! -f "$target" ]; then
        log "skip (not installed): $target"
        return
    fi

    mkdir -p "$(dirname "$target")"

    if [ ! -f "$target" ]; then
        if [ -n "$frontmatter_file" ]; then
            cat "$frontmatter_file" "$BLOCK_FILE" > "$target"
        else
            cp "$BLOCK_FILE" "$target"
        fi
        log "created $target"
        return
    fi

    has_begin=0
    grep -qF "$BEGIN_PREFIX" "$target" && has_begin=1
    has_end=0
    grep -qF "$END_MARKER" "$target" && has_end=1

    if [ "$has_begin" != "$has_end" ]; then
        die "$target: has a taorc managed-block begin marker without a matching end marker (or vice versa) -- fix the file by hand before running install.sh"
    fi

    if [ "$has_begin" = "1" ] && [ "$has_end" = "1" ]; then
        awk -v beginp="$BEGIN_PREFIX" -v endm="$END_MARKER" -v blockfile="$BLOCK_FILE" '
            BEGIN {
                block = ""
                while ((getline line < blockfile) > 0) block = block line "\n"
            }
            index($0, beginp) > 0 && inblock == 0 {
                printf "%s", block
                inblock = 1
                next
            }
            inblock && index($0, endm) > 0 { inblock = 0; next }
            inblock { next }
            { print }
        ' "$target" > "$target.taorc-tmp"
        mv "$target.taorc-tmp" "$target"
        log "updated $target"
    else
        if [ -s "$target" ]; then
            last_char="$(tail -c1 "$target" || true)"
            [ "$last_char" != "" ] && printf '\n' >> "$target"
        fi
        cat "$BLOCK_FILE" >> "$target"
        log "appended to $target"
    fi
}

remove_block() {
    target="$1"
    [ -f "$target" ] || return

    has_begin=0
    grep -qF "$BEGIN_PREFIX" "$target" && has_begin=1
    has_end=0
    grep -qF "$END_MARKER" "$target" && has_end=1

    if [ "$has_begin" = "0" ] && [ "$has_end" = "0" ]; then
        return
    fi
    if [ "$has_begin" != "$has_end" ]; then
        die "$target: has a taorc managed-block begin marker without a matching end marker (or vice versa) -- fix the file by hand before running --uninstall"
    fi

    awk -v beginp="$BEGIN_PREFIX" -v endm="$END_MARKER" '
        index($0, beginp) > 0 && inblock == 0 { inblock = 1; next }
        inblock && index($0, endm) > 0 { inblock = 0; next }
        inblock { next }
        { print }
    ' "$target" > "$target.taorc-tmp"
    mv "$target.taorc-tmp" "$target"

    if [ ! -s "$target" ] || [ -z "$(tr -d '[:space:]-' < "$target")" ]; then
        rm -f "$target"
        log "removed (now empty) $target"
    else
        log "removed taorc block from $target"
    fi
}

apply_skill_copy() {
    dest="$1"
    if [ "$UNINSTALL" = "1" ]; then
        if [ -d "$dest" ]; then
            rm -rf "$dest"
            log "removed $dest"
        fi
        return
    fi
    if [ "$DETECT" = "1" ] && [ ! -d "$dest" ]; then
        log "skip (not installed): $dest"
        return
    fi
    mkdir -p "$(dirname "$dest")"

    # Guard against --source and the install target overlapping (e.g. running
    # against a taorc checkout's own directory by mistake): resolve both to
    # absolute paths and refuse to rm -rf a dest that is the source tree or
    # sits inside it, rather than deleting part of what we're about to copy
    # from.
    dest_abs="$(cd "$(dirname "$dest")" && pwd)/$(basename "$dest")"
    source_abs="$(cd "$SOURCE_DIR" && pwd)"
    case "$dest_abs/" in
        "$source_abs"/*) die "refusing to remove $dest: it is inside --source ($SOURCE_DIR)" ;;
    esac

    rm -rf "$dest"
    cp -R "$SOURCE_DIR/skills/readable-code" "$dest"
    find "$dest" -name '__pycache__' -type d -prune -exec rm -rf {} +
    find "$dest" -name '.DS_Store' -delete
    log "installed $dest"
}

# ---- run ------------------------------------------------------------

while IFS=: read -r kind relpath frontmatter_file; do
    [ -n "$kind" ] || continue
    target="$TARGET_DIR/$relpath"
    case "$kind" in
        block)
            if [ "$UNINSTALL" = "1" ]; then
                remove_block "$target"
            else
                apply_block "$target" "$frontmatter_file"
            fi
            ;;
        skill)
            apply_skill_copy "$target"
            ;;
    esac
done < "$TARGETS_FILE"

if [ "$UNINSTALL" = "1" ]; then
    log "uninstall complete."
else
    log "install complete (v$VERSION, scope: $SCOPE, target: $TARGET_DIR)."
fi
