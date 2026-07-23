# CLAUDE.md — Session Handoff

Context for future Claude Code sessions working in this repo.

## What this project is

A collection of FFF (Fused Filament Fabrication) 3D printing profiles, authored/tuned by
James Morris. Currently targets the **Prusa CORE One+** using **PrusaSlicer**. Profiles are
published as small, individually importable PrusaSlicer config bundles (one filament each).

- GitHub remote: https://github.com/xjamesmorris/fff-profiles
- Default branch: `main`

## Repository layout

- `README.md` — usage (import, adapting to other printers), LLM-usage note, contributing, license.
- `filaments/` — published, generated per-filament `.ini` bundles (the distributables).
- `scripts/extract.py` — GPLv3 tool that splits the master bundle into per-filament files.
- `tests/` — `test_extract.py` (stdlib `unittest`) + `fixtures/sample_bundle.ini`.
- `manifest.example.json` — template listing which presets to publish.
- `Makefile` — `test`, `test-net`, `list`, `publish` targets.
- `LICENSE` (CC BY-SA 4.0), `LICENSE-CODE` (GPLv3).

## How publishing works

1. The author maintains a **master config bundle in PrusaSlicer**, exported to a local
   `.ini` (default path `../PrusaSlicer_config_bundle.ini`). This master is **local-only —
   never committed** (it contains many experimental/`- Copy` presets). `.gitignore` blocks
   `*config_bundle*.ini` and the real `manifest.json`.
2. `manifest.json` (copied from the example) lists which filaments to publish, each with an
   optional paired print (process) and/or printer preset.
3. `make publish` runs `scripts/extract.py`, which for each filament walks its `inherits`
   chain: ancestors that are *also user presets in the bundle* are included; ancestors NOT
   in the bundle are assumed to be PrusaSlicer **system presets** and left as references
   (a `note:` is printed for each — review these, since a *dangling* parent looks the same
   as a system one). The `[presets]` block (UI selection state) is dropped.
4. Output lands in `filaments/*.ini`; those ARE committed.

## Key decisions (do not silently reverse)

- **Distribution: per-filament config bundles** in `filaments/`, imported via
  `File → Import → Import Config Bundle…`. Not one big bundle.
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
- `make test` (offline) must pass before committing tooling changes. `make test-net`
  additionally validates the parser against a pristine bundle from Prusa's GitHub.

## Likely next steps / TODO

- **Profile validation lint (requested):** add a `scripts/validate.py` (+ tests) that
  checks profile language/structure/quality — e.g. resolvable `inherits`, no dangling
  parents, sane/consistent compatibility conditions, required keys present — to run
  *before incorporating changes* (candidate for a pre-commit hook / CI).
- **Slicer translation tool (requested):** a tool to port profiles between OrcaSlicer
  (and similar) and PrusaSlicer — in and out. Note the formats differ substantially:
  OrcaSlicer/Bambu use per-preset JSON with its own key names and inheritance (`from`,
  `inherits`), vs. PrusaSlicer's INI config bundles; a key-name mapping + unit/semantic
  reconciliation layer will be the bulk of the work.
- Populate `manifest.json` and publish the first real filament(s).
- Consider paired custom **process** profiles per filament (manifest already supports it).
- Add CI (GitHub Actions) to run `make test` on push.
