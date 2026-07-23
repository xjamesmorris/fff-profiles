#!/usr/bin/env python3
# extract.py — split a PrusaSlicer config bundle into individual, importable profiles.
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
Split a PrusaSlicer *config bundle* (one .ini holding many named presets) into
small, self-contained bundles — typically one filament per file, optionally
paired with a print (process) preset and/or a printer preset.

Why a script instead of PrusaSlicer's "Export Config Bundle" checkboxes:

  * Presets store only the *diff* from their parent (`inherits = ...`). If you
    copy a single filament section by hand and it inherits from *another user
    preset in the bundle*, the exported file is incomplete. This tool walks the
    `inherits` chain and includes any ancestor that is itself a user preset in
    the bundle. Ancestors that are NOT in the bundle are assumed to be
    PrusaSlicer *system* presets and are left as references (resolved on import).

  * It is reproducible and reviewable: the same source + manifest always yields
    the same output files.

Scope: this tool only *selects and copies* presets verbatim. It never edits,
tunes, or flattens any technical values — that stays with the human author.

Usage:
  python3 scripts/extract.py --list                  # show presets in the bundle
  python3 scripts/extract.py --manifest manifest.json # extract everything listed
  python3 scripts/extract.py --source bundle.ini --filament "Name" [--print P] [--printer PR] [--out DIR]

Manifest format (JSON):
  {
    "source":  "../PrusaSlicer_config_bundle.ini",   # optional, overridable by --source
    "out_dir": "filaments",                            # optional, default "filaments"
    "filaments": [
      { "name": "3D-Fuel Pro PCTG @COREONE HF0.4 - JM",
        "slug": "3dfuel-pro-pctg",                     # optional; derived from name if omitted
        "print":   null,                                # optional paired process preset name
        "printer": null }                               # optional paired printer preset name
    ]
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Section:
    """One [type:name] block from a bundle. `kind` is 'presets' for the [presets] block."""
    kind: str            # 'filament' | 'print' | 'printer' | 'presets' | ...
    name: str            # preset name, or '' for [presets]
    body: list[str] = field(default_factory=list)  # value lines, verbatim, no header

    @property
    def header(self) -> str:
        return f"[{self.kind}]" if not self.name else f"[{self.kind}:{self.name}]"

    def get(self, key: str) -> str | None:
        prefix = key + " ="
        for line in self.body:
            if line.startswith(prefix) or line.rstrip() == key + " =":
                return line.split("=", 1)[1].strip()
        return None


def parse_bundle(text: str) -> list[Section]:
    """Parse a bundle into ordered Sections. Lines are [header], blank, or 'key = value'."""
    sections: list[Section] = []
    current: Section | None = None
    header_re = re.compile(r"^\[([^:\]]+)(?::(.*))?\]\s*$")
    for raw in text.splitlines():
        m = header_re.match(raw)
        if m:
            current = Section(kind=m.group(1), name=(m.group(2) or ""))
            sections.append(current)
        elif current is not None:
            current.body.append(raw)
        # lines before the first header (e.g. a leading comment) are ignored
    # Trim trailing blank lines from each body so re-emission is tidy.
    for s in sections:
        while s.body and s.body[-1].strip() == "":
            s.body.pop()
    return sections


def index(sections: list[Section]) -> dict[tuple[str, str], Section]:
    return {(s.kind, s.name): s for s in sections if s.name}


def parents_of(section: Section) -> list[str]:
    """Parent preset names from `inherits` (semicolon-separated for multi-material)."""
    val = section.get("inherits")
    if not val:
        return []
    return [p.strip() for p in val.split(";") if p.strip()]


def resolve_chain(
    kind: str,
    name: str,
    idx: dict[tuple[str, str], Section],
    collected: "dict[tuple[str, str], Section]",
    external: set[str],
) -> None:
    """Collect `kind:name` and all ancestors that are user presets in the bundle.

    Ancestors not present in the bundle are recorded in `external` (assumed to be
    PrusaSlicer system presets) and left as bare references.
    """
    key = (kind, name)
    if key in collected:
        return
    section = idx.get(key)
    if section is None:
        external.add(name)
        return
    # Collect ancestors first so they are emitted before descendants.
    for parent in parents_of(section):
        resolve_chain(kind, parent, idx, collected, external)
    collected[key] = section


def slugify(name: str) -> str:
    s = name.lower()
    s = s.replace("@", "at ").replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def build_output(
    sections: list[Section],
    filament: str,
    print_preset: str | None,
    printer: str | None,
) -> tuple[list[Section], list[str]]:
    """Return (ordered sections to emit, warnings)."""
    idx = index(sections)
    if ("filament", filament) not in idx:
        raise KeyError(f"filament preset not found in bundle: {filament!r}")

    collected: dict[tuple[str, str], Section] = {}
    external: set[str] = set()

    resolve_chain("filament", filament, idx, collected, external)
    if print_preset:
        if ("print", print_preset) not in idx:
            raise KeyError(f"print preset not found in bundle: {print_preset!r}")
        resolve_chain("print", print_preset, idx, collected, external)
    if printer:
        if ("printer", printer) not in idx:
            raise KeyError(f"printer preset not found in bundle: {printer!r}")
        resolve_chain("printer", printer, idx, collected, external)

    # Emit order: printer, print, filament — parents already precede children
    # within each kind because resolve_chain inserts ancestors first.
    order = {"printer": 0, "print": 1, "filament": 2}
    emitted = sorted(collected.values(), key=lambda s: order.get(s.kind, 9))

    warnings: list[str] = []
    for ext in sorted(external):
        warnings.append(
            f"references parent not in bundle (assuming PrusaSlicer system preset): {ext!r}"
        )
    return emitted, warnings


def render(sections: list[Section]) -> str:
    """Render sections as a PrusaSlicer-importable config bundle (no [presets] block)."""
    out: list[str] = []
    for s in sections:
        out.append(s.header)
        out.extend(s.body)
        out.append("")  # blank line between sections
    return "\n".join(out).rstrip("\n") + "\n"


def load_source(path: Path) -> list[Section]:
    if not path.exists():
        sys.exit(f"error: source bundle not found: {path}")
    return parse_bundle(path.read_text(encoding="utf-8"))


def cmd_list(sections: list[Section]) -> None:
    for kind in ("filament", "print", "printer"):
        names = sorted(s.name for s in sections if s.kind == kind)
        print(f"\n[{kind}]  ({len(names)})")
        for n in names:
            print(f"  {n}")


def extract_one(
    sections: list[Section],
    filament: str,
    print_preset: str | None,
    printer: str | None,
    out_dir: Path,
    slug: str | None,
) -> Path:
    emitted, warnings = build_output(sections, filament, print_preset, printer)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug or slugify(filament)}.ini"
    out_path.write_text(render(emitted), encoding="utf-8")
    kinds = ", ".join(f"{sum(1 for s in emitted if s.kind==k)} {k}" for k in ("filament", "print", "printer") if any(s.kind == k for s in emitted))
    print(f"wrote {out_path}  ({kinds})")
    for w in warnings:
        print(f"  note: {w}")
    return out_path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help="path to the config bundle .ini")
    ap.add_argument("--manifest", help="path to a JSON manifest (batch mode)")
    ap.add_argument("--filament", help="single filament preset name to extract")
    ap.add_argument("--print", dest="print_preset", help="paired print (process) preset name")
    ap.add_argument("--printer", help="paired printer preset name")
    ap.add_argument("--out", default="filaments", help="output directory (default: filaments)")
    ap.add_argument("--slug", help="output filename slug (single mode)")
    ap.add_argument("--list", action="store_true", help="list presets in the bundle and exit")
    args = ap.parse_args(argv)

    manifest = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    source = args.source or (manifest or {}).get("source")
    if not source:
        ap.error("no --source and no 'source' in manifest")
    sections = load_source(Path(source).expanduser())

    if args.list:
        cmd_list(sections)
        return 0

    if args.filament:
        extract_one(sections, args.filament, args.print_preset, args.printer,
                    Path(args.out), args.slug)
        return 0

    if manifest:
        out_dir = Path(args.out if args.out != "filaments" else manifest.get("out_dir", "filaments"))
        entries = manifest.get("filaments", [])
        if not entries:
            sys.exit("manifest has no 'filaments' entries")
        for e in entries:
            extract_one(sections, e["name"], e.get("print"), e.get("printer"),
                        out_dir, e.get("slug"))
        return 0

    ap.error("nothing to do: pass --list, --filament, or --manifest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
