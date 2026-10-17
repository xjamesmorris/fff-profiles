#!/usr/bin/env python3
# validate.py — check the repo's published profiles, docs, and hygiene before committing.
# Copyright (C) 2026 James Morris
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""
Validate the repository before committing: published profiles, Markdown docs, the
manifest template, and repo hygiene. Run by the pre-commit hook (`make hooks`).

Scope: this tool only *reports*. It never edits profiles or judges tuned values
(temperatures, speeds, flow, ...) — fixing a profile stays with the human author.

Findings are `error` (blocks the commit) or `warning` (printed, doesn't block;
`--strict` makes warnings fail too). Checks:

  profiles/**/*.ini
    layout        path is profiles/<Vendor>/<filament|process>/<Base>__<Printer>_<Slicer>.ini
    syntax        UTF-8; every line is a [section], `key = value`, blank, or a comment;
                  no duplicate keys or presets; no [presets] block; known section kinds
    content       filament/ files hold a [filament]; process/ files hold a [print] and no
                  [filament]; required keys present (filament_type)
    inherits      no cycles; parents not in the file are assumed to be system presets
                  (verified against Prusa's published bundle with --check-system-presets)
    conditions    compatible_*_condition: balanced (), [], quotes and /regex/ literals;
                  a PrusaCOREOne file should target COREONE
    printer-side  a filament_type that isn't a Core One built-in must be mentioned in the
                  docs (the printer needs a matching custom filament)
    vendor        filament_vendor matches the vendor directory
  *.md
    links         relative links and #anchors resolve
    paths         backticked repo paths (`profiles/...`, `docs/...`) exist
    fences        code fences are closed
    orphans       a profile readme is named README__<name>.md and has a matching <name>.ini
  repo
    hygiene       no master bundle (*config_bundle*.ini) or manifest.json tracked
    manifest      manifest.example.json is valid and well-formed

Usage:
  python3 scripts/validate.py                       # validate the working tree
  python3 scripts/validate.py --root DIR            # validate a snapshot (pre-commit)
  python3 scripts/validate.py --strict              # warnings fail too
  python3 scripts/validate.py --check-system-presets  # also verify parents online
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract  # noqa: E402

# Filament names the Core One firmware ships (Prusa-Firmware-Buddy
# src/common/filament_presets.cpp, v6.9.x). Any other filament_type needs a custom
# filament on the printer — see docs/CoreOne_custom_filament.md.
BUILTIN_FILAMENT_TYPES = {
    "PLA", "PETG", "ASA", "PC", "PVB", "ABS", "HIPS", "PP", "FLEX", "PA", "PPS", "PPA",
}

KNOWN_KINDS = {"filament", "print", "printer", "physical_printer", "sla_print", "sla_material"}
CATEGORY_KIND = {"filament": "filament", "process": "print"}
FORBIDDEN_TRACKED = ["*config_bundle*.ini", "manifest.json"]
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
PROFILE_README_PREFIX = "README__"

PRUSA_SETTINGS_URL = ("https://raw.githubusercontent.com/prusa3d/"
                      "PrusaSlicer-settings-prusa-fff/main/PrusaResearch/")

FILENAME_RE = re.compile(r"^(?P<base>[0-9A-Za-z_.+\-]+?)__(?P<printer>[0-9A-Za-z.+\-]+)_"
                         r"(?P<slicer>[0-9A-Za-z.+\-]+)\.ini$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*) =(?: .*)?$")
HEADER_RE = re.compile(r"^\[([^:\]]+)(?::(.*))?\]\s*$")


@dataclass
class Finding:
    path: str
    line: int | None
    level: str     # 'error' | 'warning'
    check: str
    message: str

    def __str__(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"{loc}: {self.level}: [{self.check}] {self.message}"


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def error(self, path, check, message, line=None):
        self.findings.append(Finding(str(path), line, "error", check, message))

    def warning(self, path, check, message, line=None):
        self.findings.append(Finding(str(path), line, "warning", check, message))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.level == "warning"]


# --------------------------------------------------------------------------- files

def repo_files(root: Path) -> list[Path]:
    """Files to validate, relative to root. Inside a git checkout: tracked + untracked,
    minus ignored. Otherwise (e.g. a pre-commit snapshot): everything on disk."""
    if (root / ".git").exists():
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True, text=True, check=True).stdout
        return sorted({Path(p) for p in out.split("\0") if p and (root / p).is_file()})
    return sorted(p.relative_to(root) for p in root.rglob("*")
                  if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts))


def read_text(root: Path, rel: Path, report: Report) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        report.error(rel, "syntax", f"not valid UTF-8 ({e.reason} at byte {e.start})")
        return None


# ------------------------------------------------------------------------ profiles

@dataclass
class Profile:
    rel: Path
    vendor: str
    category: str
    printer_label: str
    sections: list[extract.Section]


def check_profile(root: Path, rel: Path, report: Report) -> Profile | None:
    parts = rel.parts
    vendor = category = printer_label = ""
    m = FILENAME_RE.match(rel.name)
    if len(parts) != 4 or parts[2] not in CATEGORY_KIND or not m:
        report.error(rel, "layout", "expected profiles/<Vendor>/<filament|process>/"
                                    "<Base>__<Printer>_<Slicer>.ini (no spaces)")
    else:
        vendor, category, printer_label = parts[1], parts[2], m["printer"]

    text = read_text(root, rel, report)
    if text is None:
        return None
    if text and not text.endswith("\n"):
        report.warning(rel, "syntax", "file doesn't end with a newline")

    # Line-level pass: syntax, duplicates, line numbers for later checks.
    seen_presets: dict[tuple[str, str], int] = {}
    keys: dict[str, int] = {}
    current = None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(("#", ";")):
            continue
        h = HEADER_RE.match(line)
        if h:
            kind, name = h.group(1), h.group(2) or ""
            current, keys = (kind, name), {}
            if kind == "presets":
                report.error(rel, "syntax", "[presets] block (UI selection state) must not be "
                                            "published", n)
            elif kind not in KNOWN_KINDS:
                report.error(rel, "syntax", f"unknown section kind [{kind}:...]", n)
            if (kind, name) in seen_presets:
                report.error(rel, "syntax", f"duplicate preset [{kind}:{name}] "
                                            f"(first at line {seen_presets[(kind, name)]})", n)
            seen_presets.setdefault((kind, name), n)
            continue
        k = KEY_RE.match(line)
        if not k:
            report.error(rel, "syntax", f"malformed line: {line[:60]!r}", n)
        elif current is None:
            report.error(rel, "syntax", "setting before the first [section]", n)
        elif k.group(1) in keys:
            report.error(rel, "syntax", f"duplicate key {k.group(1)!r} "
                                        f"(first at line {keys[k.group(1)]})", n)
        else:
            keys[k.group(1)] = n

    sections = [s for s in extract.parse_bundle(text) if s.name]
    profile = Profile(rel, vendor, category, printer_label, sections)
    line_of = {key: n for key, n in seen_presets.items()}

    if not sections:
        report.error(rel, "content", "no presets found")
        return profile
    if category:
        want = CATEGORY_KIND[category]
        if not any(s.kind == want for s in sections):
            report.error(rel, "content", f"a {category}/ profile must contain a [{want}:...] preset")
        if category == "process" and any(s.kind == "filament" for s in sections):
            report.error(rel, "content", "process/ profiles must not contain [filament:...] presets")

    for s in sections:
        at = line_of.get((s.kind, s.name))
        if s.kind == "filament":
            if not s.get("filament_type"):
                report.error(rel, "content", f"[filament:{s.name}] has no filament_type", at)
            fv = (s.get("filament_vendor") or "").strip('"')
            if vendor and fv and fv != vendor:
                report.warning(rel, "vendor", f"[filament:{s.name}] filament_vendor is {fv!r} "
                                              f"but the directory vendor is {vendor!r}", at)
        if not s.get("inherits") and s.kind in ("filament", "print"):
            report.warning(rel, "inherits", f"[{s.kind}:{s.name}] inherits nothing, so it must "
                                            "be a complete preset", at)
        if (s.get("compatible_printers") or "").strip('"'):
            report.warning(rel, "conditions", f"[{s.kind}:{s.name}] pins compatible_printers to "
                                              "named printers; prefer a condition", at)
        for key in ("compatible_printers_condition", "compatible_prints_condition"):
            cond = s.get(key)
            if cond:
                problem = condition_problem(cond.strip('"'))
                if problem:
                    report.error(rel, "conditions", f"[{s.kind}:{s.name}] {key}: {problem}", at)
        if printer_label == "PrusaCOREOne" and s.kind == "filament":
            cond = s.get("compatible_printers_condition") or ""
            if "COREONE" not in cond:
                report.warning(rel, "conditions", f"[filament:{s.name}] file targets PrusaCOREOne "
                                                  "but compatible_printers_condition doesn't "
                                                  "mention COREONE", at)

    check_inherits(profile, report, line_of)
    return profile


def check_inherits(profile: Profile, report: Report, line_of) -> None:
    idx = extract.index(profile.sections)
    for s in profile.sections:
        path, node = [], (s.kind, s.name)
        while node in idx and node not in path:
            path.append(node)
            parents = extract.parents_of(idx[node])
            # Multi-parent inheritance is rare in user presets; follow the first.
            node = (node[0], parents[0]) if parents else None
        if node in path:
            chain = " -> ".join(n for _, n in path[path.index(node):] + [node])
            report.error(profile.rel, "inherits", f"inheritance cycle: {chain}",
                         line_of.get((s.kind, s.name)))
            return


def external_parents(profile: Profile) -> set[tuple[str, str]]:
    """(kind, name) parents referenced but not defined in the file (system presets)."""
    idx = extract.index(profile.sections)
    return {(s.kind, p) for s in profile.sections for p in extract.parents_of(s)
            if (s.kind, p) not in idx}


def condition_problem(cond: str) -> str | None:
    """Return a description of a structural problem in a PrusaSlicer condition, or None.
    Checks balance of (), [], "strings" and /regex/ literals after =~ or !~."""
    stack: list[str] = []
    pairs = {")": "(", "]": "["}
    i, n = 0, len(cond)
    while i < n:
        c = cond[i]
        if c == '"':
            j = cond.find('"', i + 1)
            if j < 0:
                return "unterminated string literal"
            i = j + 1
            continue
        if c in "=!" and cond[i + 1:i + 2] == "~":
            j = i + 2
            while j < n and cond[j] == " ":
                j += 1
            if j >= n or cond[j] != "/":
                return "expected /regex/ after =~ or !~"
            k = j + 1
            while k < n and cond[k] != "/":
                k += 2 if cond[k] == "\\" else 1
            if k >= n:
                return "unterminated /regex/"
            pattern = cond[j + 1:k]
            try:
                re.compile(pattern)
            except re.error as e:
                return f"invalid regex /{pattern}/: {e}"
            i = k + 1
            continue
        if c in "([":
            stack.append(c)
        elif c in ")]":
            if not stack or stack.pop() != pairs[c]:
                return f"unbalanced {c!r}"
        i += 1
    if stack:
        return f"unclosed {stack[-1]!r}"
    return None


# ---------------------------------------------------------------------------- docs

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
REPO_PATH_RE = re.compile(r"^(?:profiles|docs|scripts|tests)/[^\s<>*…|{}]+$")


def slugify(heading: str) -> str:
    """GitHub-style heading anchor."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)   # links -> text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def md_structure(text: str) -> tuple[list[tuple[int, str]], set[str], int | None]:
    """Return (prose lines with numbers, heading anchors, line of an unclosed fence)."""
    prose, anchors, counts = [], set(), {}
    fence, fence_line = None, None
    for n, line in enumerate(text.splitlines(), 1):
        f = FENCE_RE.match(line)
        if f:
            if fence is None:
                fence, fence_line = f.group(1), n
            elif f.group(1) == fence:
                fence = None
            continue
        if fence:
            continue
        prose.append((n, line))
        h = HEADING_RE.match(line)
        if h:
            slug = slugify(h.group(2))
            dup = counts.get(slug, 0)
            counts[slug] = dup + 1
            anchors.add(slug if dup == 0 else f"{slug}-{dup}")
    return prose, anchors, (fence_line if fence else None)


def check_markdown(root: Path, files: list[Path], report: Report) -> None:
    md_files = [f for f in files if f.suffix.lower() == ".md"]
    structures = {}
    for rel in md_files:
        text = read_text(root, rel, report)
        if text is not None:
            structures[rel] = md_structure(text)

    all_files = {f.as_posix() for f in files}
    all_dirs = {p.as_posix() for f in files for p in f.parents}

    for rel, (prose, anchors, unclosed) in structures.items():
        if unclosed:
            report.error(rel, "fences", "code fence is never closed", unclosed)
        for n, line in prose:
            for m in LINK_RE.finditer(line):
                target = m.group(1) or m.group(2)
                check_link(root, rel, target, n, anchors, structures, report)
            for m in CODE_SPAN_RE.finditer(line):
                span = m.group(1).strip()
                if REPO_PATH_RE.match(span) and span.rstrip("/") not in all_files | all_dirs:
                    report.error(rel, "paths", f"`{span}` doesn't exist in the repo", n)

        # A profile readme sits next to its .ini as README__<profile>.md.
        if rel.parts[0] == "profiles" and rel.name.lower() != "readme.md":
            if not rel.name.startswith(PROFILE_README_PREFIX):
                report.error(rel, "orphans", f"profile readmes are named "
                                             f"{PROFILE_README_PREFIX}<profile>.md")
            else:
                ini = rel.with_name(rel.name[len(PROFILE_README_PREFIX):]).with_suffix(".ini")
                if ini.as_posix() not in all_files:
                    report.error(rel, "orphans", f"no matching profile {ini.name}")


def check_link(root, rel, target, line, anchors, structures, report) -> None:
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
        return  # external URL / mailto — not checked offline
    path_part, _, anchor = target.partition("#")
    if not path_part:
        if anchor and anchor not in anchors:
            report.error(rel, "links", f"anchor #{anchor} not found in this file", line)
        return
    resolved = (root / rel.parent / path_part).resolve()
    try:
        dest = resolved.relative_to(root.resolve())
    except ValueError:
        return  # escapes the repo (e.g. GitHub-relative ../../issues) — not checkable
    if not resolved.exists():
        report.error(rel, "links", f"link target {path_part} doesn't exist", line)
        return
    if anchor and dest.suffix.lower() == ".md":
        target_anchors = structures.get(dest, (None, set(), None))[1]
        if anchor not in target_anchors:
            report.error(rel, "links", f"anchor #{anchor} not found in {dest.as_posix()}", line)


# ------------------------------------------------------------------ cross-checks

def check_printer_side_setup(root: Path, files, profiles: list[Profile], report: Report) -> None:
    """A non-built-in filament_type needs a custom filament on the printer; make sure the
    docs tell users so (the type must be mentioned in some Markdown file)."""
    docs_text = ""
    for f in files:
        if f.suffix.lower() == ".md" and f.name != "CLAUDE.md":
            try:
                docs_text += (root / f).read_text(encoding="utf-8") + "\n"
            except UnicodeDecodeError:
                pass
    for p in profiles:
        for s in p.sections:
            if s.kind != "filament":
                continue
            ftype = (s.get("filament_type") or "").strip('"')
            if ftype and ftype.upper() not in BUILTIN_FILAMENT_TYPES:
                if not re.search(rf"`{re.escape(ftype)}`", docs_text):
                    report.warning(p.rel, "printer-side",
                                   f"filament_type {ftype!r} isn't a Core One built-in, and no doc "
                                   f"mentions `{ftype}`; users need a matching custom filament on "
                                   "the printer (see docs/CoreOne_custom_filament.md)")


def check_hygiene(root: Path, report: Report) -> None:
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                             capture_output=True, text=True, check=True).stdout
        tracked = [p for p in out.split("\0") if p]
    else:
        tracked = [f.as_posix() for f in repo_files(root)]
    for path in tracked:
        for pattern in FORBIDDEN_TRACKED:
            if fnmatch.fnmatch(Path(path).name, pattern):
                report.error(path, "hygiene", f"must not be committed (matches {pattern}); "
                                              "it's local-only")


def check_manifest_example(root: Path, report: Report) -> None:
    rel = Path("manifest.example.json")
    if not (root / rel).exists():
        report.error(rel, "manifest", "missing")
        return
    try:
        data = json.loads((root / rel).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.error(rel, "manifest", f"invalid JSON: {e.msg}", e.lineno)
        return
    for key in ("source", "out_root"):
        if not isinstance(data.get(key), str):
            report.error(rel, "manifest", f"missing string field {key!r}")
    for listname in ("filaments", "processes"):
        entries = data.get(listname, [])
        if not isinstance(entries, list):
            report.error(rel, "manifest", f"{listname!r} must be a list")
            continue
        for i, e in enumerate(entries):
            if not (isinstance(e, dict) and e.get("name") and e.get("vendor")):
                report.error(rel, "manifest", f"{listname}[{i}] needs 'name' and 'vendor'")


# ---------------------------------------------------------------- system presets

def fetch_prusa_system_bundle(timeout: int = 30) -> tuple[str, str]:
    """Download the newest PrusaResearch vendor bundle. Returns (version, text)."""
    with urllib.request.urlopen(PRUSA_SETTINGS_URL + "index.idx", timeout=timeout) as r:
        idx = r.read().decode("utf-8")
    version = next(m.group(1) for line in idx.splitlines()
                   if (m := re.match(r"^(\d+\.\d+\.\d+)\b", line)))
    with urllib.request.urlopen(f"{PRUSA_SETTINGS_URL}{version}.ini", timeout=timeout) as r:
        return version, r.read().decode("utf-8")


def check_system_presets(profiles: list[Profile], report: Report, bundle_text: str,
                         version: str) -> None:
    system = extract.index(extract.parse_bundle(bundle_text))
    for p in profiles:
        for kind, name in sorted(external_parents(p)):
            if (kind, name) not in system:
                report.error(p.rel, "inherits", f"parent [{kind}:{name}] isn't a preset in Prusa's "
                                                f"system bundle {version} (dangling parent?)")


# ---------------------------------------------------------------------------- main

def validate(root: Path, system_bundle: tuple[str, str] | None = None) -> Report:
    report = Report()
    files = repo_files(root)
    profiles = []
    for rel in files:
        if rel.parts[0] == "profiles" and rel.suffix.lower() == ".ini":
            p = check_profile(root, rel, report)
            if p:
                profiles.append(p)
    check_markdown(root, files, report)
    check_printer_side_setup(root, files, profiles, report)
    check_hygiene(root, report)
    check_manifest_example(root, report)
    if system_bundle:
        check_system_presets(profiles, report, system_bundle[1], system_bundle[0])
    report.findings.sort(key=lambda f: (f.level != "error", f.path, f.line or 0))
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="repository root or snapshot to validate (default: this repo)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--check-system-presets", action="store_true",
                    help="download Prusa's system bundle and verify external parents exist")
    args = ap.parse_args(argv)

    bundle = None
    if args.check_system_presets:
        try:
            bundle = fetch_prusa_system_bundle()
        except Exception as e:
            print(f"error: couldn't fetch Prusa's system bundle: {e}", file=sys.stderr)
            return 2
    report = validate(Path(args.root), bundle)
    for f in report.findings:
        print(f)
    failed = report.errors or (args.strict and report.warnings)
    print(f"validate: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
          + (f"; system presets checked against PrusaResearch {bundle[0]}" if bundle else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
