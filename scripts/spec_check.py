#!/usr/bin/env python3
"""Cross-reference check for the Markdown documents.

The check enforces these rules:

1. Each relative link must point to a file that exists.
2. Each anchor must match a heading or an HTML anchor in its target document.
3. `spec/index.md` must list each specification document.
4. Each unit anchor must sit in its own document, and must be unique.
5. The implementation register must list each unit, and only each unit.
6. Each register row must use the fixed state vocabulary.
7. Each rule definition must sit in the document of its unit.
8. Each unit or rule citation must resolve.
9. A specification document must not state a schedule phase (Phase N).
10. With `--drift <base>`: a change to a document with a `partial` or `done`
    unit must also change the register or a mapped code root.

The script uses the standard library only.
Exit status 0 means the checks pass.
Exit status 1 means at least one check fails.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ["CLAUDE.md", "spec", "docs", "plans"]

FENCE_RE = re.compile(r"^[ \t]*(```|~~~)", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)

DOC_CODES = {
    "harness.md": "HRN",
    "infrastructure.md": "IAC",
    "corpus.md": "COR",
    "training.md": "TRN",
    "evaluation.md": "EVL",
    "inference.md": "INF",
    "model.md": "MDL",
    "variants.md": "VAR",
    "repository.md": "REP",
    "agents.md": "AGT",
    "licensing.md": "LIC",
    "risks.md": "RSK",
}
CODE_ALT = "|".join(DOC_CODES.values())
ANCHOR_RE = re.compile(r'<a id="([a-z0-9-]+)"></a>')
UNIT_ID_RE = re.compile(
    r"^(hrn|iac|cor|trn|evl|inf|mdl|var|rep|agt|lic|rsk)(-[a-z][a-z0-9]*){1,2}$"
)
RULE_DEF_RE = re.compile(
    rf"^\s*(?:[-*]|\d+\.)\s+\*\*((?:{CODE_ALT})(?:-[A-Z][A-Z0-9]*){{1,2}}-[1-9][0-9]{{0,2}})\b",
    re.MULTILINE,
)
CITE_RE = re.compile(rf"\b(?:{CODE_ALT})(?:-[A-Z][A-Z0-9]*){{1,2}}(?:-[1-9][0-9]{{0,2}})?\b")
ROW_ID_RE = re.compile(r"^\[([A-Z0-9-]+)\]\(([^)\s]+)\)$")
PHASE_RE = re.compile(r"Phase [0-9]")
PHRASE_BANS = [
    re.compile(r"open design work"),
    re.compile(r"\b(previously|formerly|no longer)\b", re.IGNORECASE),
]
STATES = {"open", "partial", "done", "n-a"}
REGISTER_META_SECTIONS = {"States", "Update protocol", "Code roots", "Retired IDs"}


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
    stripped = strip_code_fences(text)
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for match in HEADING_RE.finditer(stripped):
        base = slugify(match.group(1))
        n = counts.get(base, 0)
        counts[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
    slugs.update(ANCHOR_RE.findall(stripped))
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
        if doc.name in {"index.md", "CLAUDE.md"}:
            continue
        if doc.resolve() not in linked:
            errors.append(f"spec/index.md does not list spec/{doc.name}")
    return errors


def collect_unit_anchors(files: list[Path]) -> tuple[dict[str, Path], list[str]]:
    """Map each unit anchor to its defining file. Enforce codes and uniqueness."""
    errors: list[str] = []
    units: dict[str, Path] = {}
    for source in files:
        text = strip_code_fences(source.read_text(encoding="utf-8"))
        rel_source = source.relative_to(ROOT)
        for anchor in ANCHOR_RE.findall(text):
            if not UNIT_ID_RE.match(anchor):
                continue
            code = anchor.split("-", 1)[0].upper()
            expected = DOC_CODES.get(source.name) if source.parent == ROOT / "spec" else None
            if expected != code:
                errors.append(f"{rel_source}: unit anchor in the wrong document: {anchor}")
                continue
            if anchor in units:
                errors.append(f"{rel_source}: duplicate unit anchor: {anchor}")
                continue
            units[anchor] = source
    return units, errors


def collect_rule_definitions(
    files: list[Path], units: dict[str, Path]
) -> tuple[set[str], list[str]]:
    """Collect rule IDs. A rule must sit in the document of its unit, once."""
    errors: list[str] = []
    rules: set[str] = set()
    for source in files:
        text = strip_code_fences(source.read_text(encoding="utf-8"))
        rel_source = source.relative_to(ROOT)
        for match in RULE_DEF_RE.finditer(text):
            rule_id = match.group(1)
            unit_id = rule_id.rsplit("-", 1)[0].lower()
            if units.get(unit_id) != source:
                errors.append(f"{rel_source}: rule outside the document of its unit: {rule_id}")
                continue
            if rule_id in rules:
                errors.append(f"{rel_source}: duplicate rule: {rule_id}")
                continue
            rules.add(rule_id)
    return rules, errors


class Register:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.retired: set[str] = set()
        self.code_roots: dict[str, list[str]] = {}


def parse_register(path: Path) -> tuple[Register, list[str]]:
    register = Register()
    if not path.exists():
        return register, ["spec/STATUS.md does not exist"]
    errors: list[str] = []
    section = ""
    for number, line in enumerate(
        strip_code_fences(path.read_text(encoding="utf-8")).splitlines(), 1
    ):
        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip())]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if not cells or all(set(cell) <= {"-"} for cell in cells):
            continue
        where = f"spec/STATUS.md:{number}"
        if section == "Retired IDs":
            if cells[0] != "ID":
                register.retired.add(cells[0])
            continue
        if section == "Code roots":
            if cells[0] != "Document" and len(cells) == 2:
                roots = [] if cells[1] == "—" else cells[1].split(",")
                register.code_roots[cells[0]] = [root.strip().strip("`") for root in roots]
            continue
        if section in REGISTER_META_SECTIONS or cells[0] == "ID":
            continue
        row_id = ROW_ID_RE.match(cells[0])
        if not row_id:
            errors.append(f"{where}: the ID cell must be one link to the unit anchor: {cells[0]}")
            continue
        if len(cells) != 4:
            errors.append(f"{where}: a register row must have four cells: {cells[0]}")
            continue
        register.rows.append(
            {
                "id": row_id.group(1),
                "target": row_id.group(2),
                "state": cells[2],
                "note": cells[3],
                "where": where,
            }
        )
    return register, errors


def check_register(register: Register, units: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    status = ROOT / "spec" / "STATUS.md"
    active: set[str] = set()
    for row in register.rows:
        where = row["where"]
        unit_id = row["id"].lower()
        if row["id"] in active:
            errors.append(f"{where}: duplicate register row: {row['id']}")
            continue
        active.add(row["id"])
        expected = f"{units[unit_id].name}#{unit_id}" if unit_id in units else None
        if row["target"] != expected:
            errors.append(f"{where}: the ID link must target the unit anchor: {row['id']}")
        if row["state"] not in STATES:
            errors.append(f"{where}: unknown state: {row['state']}")
            continue
        if row["state"] == "partial" and not row["note"]:
            errors.append(f"{where}: a partial row needs a note: {row['id']}")
        if row["state"] == "done":
            links = [
                link
                for link in LINK_RE.findall(row["note"])
                if not re.match(r"^[a-z][a-z0-9+.-]*:", link)
            ]
            if not links:
                errors.append(f"{where}: a done row needs an evidence link: {row['id']}")
            for link in links:
                resolved = (status.parent / link.partition("#")[0]).resolve()
                if not resolved.exists():
                    errors.append(f"{where}: broken evidence link: {link}")
    anchor_ids = {unit.upper() for unit in units}
    for missing in sorted(anchor_ids - active):
        errors.append(f"spec/STATUS.md: no register row for the unit: {missing}")
    for extra in sorted(active - anchor_ids):
        errors.append(f"spec/STATUS.md: a register row without a unit anchor: {extra}")
    for retired in sorted(register.retired & anchor_ids):
        errors.append(f"spec/STATUS.md: a retired ID still has an anchor: {retired}")
    for retired in sorted(register.retired & active):
        errors.append(f"spec/STATUS.md: a retired ID has an active row: {retired}")
    return errors


def check_citations(
    files: list[Path], units: dict[str, Path], rules: set[str], retired: set[str]
) -> list[str]:
    """Each unit or rule citation must resolve. docs/research is exempt."""
    errors: list[str] = []
    known = {unit.upper() for unit in units} | rules | retired
    for source in files:
        rel_source = source.relative_to(ROOT)
        parts = rel_source.parts
        in_scope = parts[0] in ("spec", "plans") or rel_source == Path("CLAUDE.md")
        if not in_scope:
            continue
        text = strip_code_fences(source.read_text(encoding="utf-8"))
        for token in CITE_RE.findall(text):
            if token not in known:
                errors.append(f"{rel_source}: unresolved citation: {token}")
    return errors


def check_phase_and_phrases(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        rel_source = source.relative_to(ROOT)
        if rel_source.parts[0] != "spec":
            continue
        text = strip_code_fences(source.read_text(encoding="utf-8"))
        if PHASE_RE.search(text):
            errors.append(f"{rel_source}: a document must not state a schedule phase (Phase N)")
        for ban in PHRASE_BANS:
            match = ban.search(text)
            if match:
                errors.append(f"{rel_source}: banned phrase: {match.group(0)}")
    return errors


def check_drift(base: str, register: Register, units: dict[str, Path]) -> list[str]:
    """A change to a document with a partial or done unit must co-change
    the register or a mapped code root."""
    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    changed = {line.strip() for line in diff.stdout.splitlines() if line.strip()}
    if "spec/STATUS.md" in changed:
        return []
    errors: list[str] = []
    for name in sorted(
        {
            units[row["id"].lower()].name
            for row in register.rows
            if row["state"] in {"partial", "done"} and row["id"].lower() in units
        }
    ):
        if f"spec/{name}" not in changed:
            continue
        roots = register.code_roots.get(name, [])
        if any(
            path == root.rstrip("/") or path.startswith(root.rstrip("/") + "/")
            for path in changed
            for root in roots
        ):
            continue
        implemented = [
            row["id"]
            for row in register.rows
            if row["state"] in {"partial", "done"}
            and units.get(row["id"].lower(), Path()).name == name
        ]
        errors.append(
            f"spec/{name}: the change must also update spec/STATUS.md or a code root; "
            f"implemented units: {', '.join(implemented)}"
        )
    return errors


def main() -> int:
    base = ""
    if "--drift" in sys.argv:
        flag = sys.argv.index("--drift")
        if flag + 1 >= len(sys.argv):
            print("--drift needs a base reference", file=sys.stderr)
            return 1
        base = sys.argv[flag + 1]
    files = markdown_files()
    errors = check_links(files) + check_index_coverage()
    units, unit_errors = collect_unit_anchors(files)
    errors += unit_errors
    rules, rule_errors = collect_rule_definitions(files, units)
    errors += rule_errors
    register, register_errors = parse_register(ROOT / "spec" / "STATUS.md")
    errors += register_errors
    errors += check_register(register, units)
    errors += check_citations(files, units, rules, register.retired)
    errors += check_phase_and_phrases(files)
    if base:
        errors += check_drift(base, register, units)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"spec-check: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"spec-check: {len(files)} documents pass, {len(units)} units, {len(rules)} rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
