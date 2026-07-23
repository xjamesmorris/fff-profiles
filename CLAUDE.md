# CLAUDE.md — Session Handoff

Context for future Claude Code sessions working in this repo.

## What this project is

A collection of FFF (Fused Filament Fabrication) 3D printing profiles, authored/tuned by
James Morris. Currently targets the **Prusa CORE One+** using **PrusaSlicer**. Profiles are
published as small, individually importable PrusaSlicer config bundles (one filament each).

- GitHub remote: https://github.com/xjamesmorris/fff-profiles
- Default branch: `main`
- Latest release: **v1.0.0** (2026-07-23) — first release; extraction tooling + the first
  published profile (3DXTech 3DXLABS EMI-ABS). Tags use semver (`vMAJOR.MINOR.PATCH`).

## Repository layout

- `README.md` — usage (import, adapting to other printers), LLM-usage note, contributing, license.
- `profiles/<Vendor>/{filament,process}/` — published, generated `.ini` bundles (the
  distributables). Filename convention:
  `<Base>__<Printer>_<Slicer>.ini` (no spaces; printer+slicer encoded in the name),
  e.g. `profiles/3DXTech/filament/3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`.
- `scripts/extract.py` — GPLv3 tool that splits the master bundle into per-profile files.
- `tests/` — `test_extract.py` (stdlib `unittest`) + `fixtures/sample_bundle.ini`.
- `manifest.example.json` — template listing which presets to publish.
- `Makefile` — `test`, `test-net`, `list`, `publish` targets.
- `LICENSE` (CC BY-SA 4.0), `LICENSE-CODE` (GPLv3).

## How publishing works

1. The author maintains a **master config bundle in PrusaSlicer**, exported to a local
   `.ini` (default path `../PrusaSlicer_config_bundle.ini`). This master is **local-only —
   never committed** (it contains many experimental/`- Copy` presets). `.gitignore` blocks
   `*config_bundle*.ini` and the real `manifest.json`.
2. `manifest.json` (copied from the example) lists which filaments/processes to publish. Each
   entry: `name` (exact preset name), `vendor`, optional `base` (filename base; derived if
   omitted), optional paired `print`/`printer`, optional `printer_label`/`slicer_label`
   overrides. Manifest-level `printer_label`/`slicer_label` default to `PrusaCOREOne` /
   `Prusaslicer`. Output path: `<out_root>/<vendor>/<filament|process>/<base>__<printer>_<slicer>.ini`.
3. `make publish` runs `scripts/extract.py`, which for each filament walks its `inherits`
   chain: ancestors that are *also user presets in the bundle* are included; ancestors NOT
   in the bundle are assumed to be PrusaSlicer **system presets** and left as references
   (a `note:` is printed for each — review these, since a *dangling* parent looks the same
   as a system one). The `[presets]` block (UI selection state) is dropped.
4. Output lands under `profiles/<Vendor>/<filament|process>/…`; those ARE committed.

## Key decisions (do not silently reverse)

- **Distribution: per-profile config bundles** under `profiles/<Vendor>/{filament,process}/`,
  imported via `File → Import → Import Config Bundle…`. Not one big bundle. Filenames encode
  printer+slicer and contain no spaces (e.g. `3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`).
- **Master bundle stays local/private**; only curated per-filament outputs are published.
- **Tooling is stdlib-only Python 3** (no third-party deps). Keep it that way.
- **Dual licensing:** profiles + docs → CC BY-SA 4.0 (`LICENSE`); code → GPLv3
  (`LICENSE-CODE`). CC is a poor fit for software, hence GPLv3 for scripts.
- **LLM-usage boundary:** LLMs handle admin, docs, and *tooling that only selects/copies
  presets* — never authoring, tuning, or flattening profile values. Keep the README's
  disclosure accurate. Do not have the LLM edit technical profile values.

## Conventions

- Commit messages end with the `Co-Authored-By: Claude Opus 4.8` trailer.
- Only commit/push when the author explicitly asks.
- **After every push, update this handoff (`CLAUDE.md`) to reflect the new state, then
  commit and push that update.** (Standing instruction from the author.)
- `make test` (offline) must pass before committing tooling changes. `make test-net`
  additionally validates the parser against a pristine bundle from Prusa's GitHub.

## Likely next steps / TODO

- **Profile validation lint (requested):** add a `scripts/validate.py` (+ tests) that
  checks profile language/structure/quality — e.g. resolvable `inherits`, no dangling
  parents, sane/consistent compatibility conditions, required keys present — to run
  *before incorporating changes* (candidate for a pre-commit hook / CI).
- **OrcaSlicer notes doc (requested):** a brief Markdown file expanding the README's
  "Calibration workflow" section — the author calibrated in OrcaSlicer (built-in tooling)
  then finished in PrusaSlicer. Document the CORE One gotchas: pressure advance is
  configured differently between the slicers, and OrcaSlicer needs custom G-code for the
  heatbreak (cooling) temperature and the filtration fan (if installed).
- **Slicer translation tool (requested):** a tool to port profiles between OrcaSlicer
  (and similar) and PrusaSlicer — in and out. Note the formats differ substantially:
  OrcaSlicer/Bambu use per-preset JSON with its own key names and inheritance (`from`,
  `inherits`), vs. PrusaSlicer's INI config bundles; a key-name mapping + unit/semantic
  reconciliation layer will be the bulk of the work (see the gotchas above).
- Publish more filaments (only 3DXTech 3DXLABS EMI-ABS is published so far; the two other
  EMI-ABS variants were intentionally held back per the author).
- Consider paired custom **process** profiles per filament (manifest already supports it).
- Add CI (GitHub Actions) to run `make test` on push.
