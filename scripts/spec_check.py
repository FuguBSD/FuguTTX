#!/usr/bin/env python3
"""Cross-reference check for the Markdown documents.

The check enforces three rules:

1. Each relative link must point to a file that exists.
2. Each anchor must match a heading in its target document.
3. `spec/index.md` must list each specification document.

The script uses the standard library only.
Exit status 0 means the checks pass.
Exit status 1 means at least one check fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ["CLAUDE.md", "spec", "docs"]

FENCE_RE = re.compile(r"^(```|~~~)", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for entry in SCAN:
        path = ROOT / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def strip_code_fences(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def slugify(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug, flags=re.UNICODE)
    return slug.replace(" ", "-")


def heading_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for match in HEADING_RE.finditer(strip_code_fences(text)):
        base = slugify(match.group(1))
        n = counts.get(base, 0)
        counts[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
    return slugs


def check_links(files: list[Path]) -> list[str]:
    errors: list[str] = []
    slug_cache: dict[Path, set[str]] = {}

    def slugs_for(path: Path) -> set[str]:
        if path not in slug_cache:
            slug_cache[path] = heading_slugs(path.read_text(encoding="utf-8"))
        return slug_cache[path]

    for source in files:
        text = strip_code_fences(source.read_text(encoding="utf-8"))
        rel_source = source.relative_to(ROOT)
        for match in LINK_RE.finditer(text):
            target = match.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            path_part, _, fragment = target.partition("#")
            if path_part:
                resolved = (source.parent / path_part).resolve()
                if not resolved.exists():
                    errors.append(f"{rel_source}: broken link: {target}")
                    continue
            else:
                resolved = source
            if fragment and resolved.suffix == ".md" and fragment not in slugs_for(resolved):
                errors.append(f"{rel_source}: broken anchor: {target}")
    return errors


def check_index_coverage() -> list[str]:
    index = ROOT / "spec" / "index.md"
    if not index.exists():
        return ["spec/index.md does not exist"]
    text = strip_code_fences(index.read_text(encoding="utf-8"))
    linked = set()
    for match in LINK_RE.finditer(text):
        path_part = match.group(1).partition("#")[0]
        if path_part:
            linked.add((index.parent / path_part).resolve())
    errors: list[str] = []
    for doc in sorted((ROOT / "spec").glob("*.md")):
        if doc.name == "index.md":
            continue
        if doc.resolve() not in linked:
            errors.append(f"spec/index.md does not list spec/{doc.name}")
    return errors


def main() -> int:
    files = markdown_files()
    errors = check_links(files) + check_index_coverage()
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"spec-check: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"spec-check: {len(files)} documents pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
