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

Output layout (see the manifest below):

    <out_root>/<vendor>/<category>/<base>__<printer_label>_<slicer_label>.ini
    e.g. profiles/3DXTech/filament/3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini

Usage:
  python3 scripts/extract.py --list                     # show presets in the bundle
  python3 scripts/extract.py --manifest manifest.json    # publish everything listed
  python3 scripts/extract.py --source B --filament "Name" --vendor V [--base B] \
      [--print P] [--printer PR] [--printer-label L] [--slicer-label L] [--out-root DIR]

Manifest format (JSON):
  {
    "source":        "../PrusaSlicer_config_bundle.ini",  # overridable by --source
    "out_root":      "profiles",                           # default "profiles"
    "printer_label": "PrusaCOREOne",                       # default, per-entry overridable
    "slicer_label":  "Prusaslicer",                        # default, per-entry overridable
    "filaments": [
      { "name":   "3DXTech 3DXLABS EMI-ABS",   # exact preset name in the bundle
        "vendor": "3DXTech",                     # -> profiles/3DXTech/filament/...
        "base":   "3DXLABS_EMI-ABS",             # optional; derived from name if omitted
        "print":   null,                          # optional paired process preset
        "printer": null }                         # optional paired printer preset
    ],
    "processes": [                                 # optional: standalone process profiles
      { "name": "0.20mm STRUCTURAL @COREONE 0.4", "vendor": "Generic", "base": "0.20mm_STRUCTURAL" }
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

DEFAULT_OUT_ROOT = "profiles"
DEFAULT_PRINTER_LABEL = "PrusaCOREOne"
DEFAULT_SLICER_LABEL = "Prusaslicer"


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
    for parent in parents_of(section):
        resolve_chain(kind, parent, idx, collected, external)
    collected[key] = section


def collect(sections: list[Section], roots: list[tuple[str, str]]) -> tuple[list[Section], list[str]]:
    """Resolve every root (kind, name) and its in-bundle ancestors.

    Returns (sections-to-emit ordered printer->print->filament, ancestors-first, warnings).
    Raises KeyError if a requested root is missing from the bundle.
    """
    idx = index(sections)
    for kind, name in roots:
        if (kind, name) not in idx:
            raise KeyError(f"{kind} preset not found in bundle: {name!r}")

    collected: dict[tuple[str, str], Section] = {}
    external: set[str] = set()
    for kind, name in roots:
        resolve_chain(kind, name, idx, collected, external)

    order = {"printer": 0, "print": 1, "filament": 2}
    emitted = sorted(collected.values(), key=lambda s: order.get(s.kind, 9))
    warnings = [
        f"references parent not in bundle (assuming PrusaSlicer system preset): {ext!r}"
        for ext in sorted(external)
    ]
    return emitted, warnings


def build_output(sections, filament, print_preset=None, printer=None):
    """Resolve a filament (+ optional paired print/printer) into emittable sections."""
    roots: list[tuple[str, str]] = [("filament", filament)]
    if print_preset:
        roots.append(("print", print_preset))
    if printer:
        roots.append(("printer", printer))
    return collect(sections, roots)


def build_process_output(sections, print_preset, printer=None):
    """Resolve a standalone process (print) preset (+ optional printer)."""
    roots: list[tuple[str, str]] = [("print", print_preset)]
    if printer:
        roots.append(("printer", printer))
    return collect(sections, roots)


def sanitize_label(label: str) -> str:
    """A filename label with no spaces or separators that would confuse the scheme."""
    return re.sub(r"[^0-9A-Za-z.+\-]", "", label.replace(" ", ""))


def derive_base(name: str, vendor: str) -> str:
    """Derive a spaceless filename base from a preset name, dropping a leading vendor
    token and any `@printer…` compatibility suffix. Prefer an explicit `base` for control."""
    s = name
    if vendor and s.lower().startswith(vendor.lower()):
        s = s[len(vendor):].lstrip(" -_")
    s = re.sub(r"\s*@.*$", "", s)         # strip "@COREONE …" suffix
    s = re.sub(r"\s+", "_", s.strip())    # spaces -> underscores
    s = re.sub(r"[^0-9A-Za-z_.+\-]", "", s)
    return s


def build_filename(base: str, printer_label: str, slicer_label: str) -> str:
    return f"{base}__{sanitize_label(printer_label)}_{sanitize_label(slicer_label)}.ini"


def output_path(out_root, vendor: str, category: str, filename: str) -> Path:
    return Path(out_root) / vendor / category / filename


def render(sections: list[Section]) -> str:
    """Render sections as a PrusaSlicer-importable config bundle (no [presets] block)."""
    out: list[str] = []
    for s in sections:
        out.append(s.header)
        out.extend(s.body)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def write_output(emitted: list[Section], warnings: list[str], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(emitted), encoding="utf-8")
    kinds = ", ".join(
        f"{sum(1 for s in emitted if s.kind == k)} {k}"
        for k in ("filament", "print", "printer")
        if any(s.kind == k for s in emitted)
    )
    print(f"wrote {path}  ({kinds})")
    for w in warnings:
        print(f"  note: {w}")
    return path


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


def publish(sections, manifest, out_root=None) -> list[Path]:
    """Run a manifest: write every filament and process entry to its computed path."""
    root = out_root or manifest.get("out_root", DEFAULT_OUT_ROOT)
    pl = manifest.get("printer_label", DEFAULT_PRINTER_LABEL)
    sl = manifest.get("slicer_label", DEFAULT_SLICER_LABEL)
    written: list[Path] = []

    for e in manifest.get("filaments", []):
        emitted, warnings = build_output(sections, e["name"], e.get("print"), e.get("printer"))
        base = e.get("base") or derive_base(e["name"], e.get("vendor", ""))
        fn = build_filename(base, e.get("printer_label", pl), e.get("slicer_label", sl))
        written.append(write_output(emitted, warnings,
                                    output_path(root, e["vendor"], "filament", fn)))

    for e in manifest.get("processes", []):
        emitted, warnings = build_process_output(sections, e["name"], e.get("printer"))
        base = e.get("base") or derive_base(e["name"], e.get("vendor", ""))
        fn = build_filename(base, e.get("printer_label", pl), e.get("slicer_label", sl))
        written.append(write_output(emitted, warnings,
                                    output_path(root, e["vendor"], "process", fn)))

    if not written:
        sys.exit("manifest has no 'filaments' or 'processes' entries")
    return written


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help="path to the config bundle .ini")
    ap.add_argument("--manifest", help="path to a JSON manifest (batch mode)")
    ap.add_argument("--filament", help="single filament preset name to extract")
    ap.add_argument("--vendor", help="vendor directory (single mode)")
    ap.add_argument("--base", help="filename base (single mode; derived if omitted)")
    ap.add_argument("--print", dest="print_preset", help="paired print (process) preset name")
    ap.add_argument("--printer", help="paired printer preset name")
    ap.add_argument("--printer-label", default=DEFAULT_PRINTER_LABEL, help="printer token in filename")
    ap.add_argument("--slicer-label", default=DEFAULT_SLICER_LABEL, help="slicer token in filename")
    ap.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="output root (default: profiles)")
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
        if not args.vendor:
            ap.error("--filament requires --vendor")
        emitted, warnings = build_output(sections, args.filament, args.print_preset, args.printer)
        base = args.base or derive_base(args.filament, args.vendor)
        fn = build_filename(base, args.printer_label, args.slicer_label)
        write_output(emitted, warnings, output_path(args.out_root, args.vendor, "filament", fn))
        return 0

    if manifest:
        publish(sections, manifest, args.out_root if args.out_root != DEFAULT_OUT_ROOT else None)
        return 0

    ap.error("nothing to do: pass --list, --filament, or --manifest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
