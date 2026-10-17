# CLAUDE.md — Session Handoff

Context for future Claude Code sessions working in this repo.

## What this project is

A collection of FFF (Fused Filament Fabrication) 3D printing profiles, authored/tuned by
James Morris. Currently targets the **Prusa CORE One+** using **PrusaSlicer**. Profiles are
published as small, individually importable PrusaSlicer config bundles (one filament each).

- GitHub remote: https://github.com/xjamesmorris/fff-profiles
- Default branch: `main`
- Latest release: **v1.1.0** (2026-10-17, tag on `cc5e7cc`) — 3DXTech CarbonX PEKK-A+CF
  HT0.6 profile (+ per-profile readme) and `docs/CoreOne_custom_filament.md`.
- Previous: **v1.0.0** (2026-07-23) — first release; extraction tooling + the first
  published profile (3DXTech 3DXLABS EMI-ABS).
- Unreleased on `main` since v1.1.0 (2026-10-17, through `34372fc`): pre-commit validation
  suite (`scripts/validate.py`, `.githooks/`, `make check`/`hooks`), EMI-ABS printer-side
  setup docs + readme, author's `README__<profile>.md` naming for profile readmes.
- Tags use semver (`vMAJOR.MINOR.PATCH`), annotated (`vX.Y.Z — summary`), each with a
  matching GitHub release (`gh release create`) whose notes follow the v1.0.0 layout.

## Repository layout

- `README.md` — usage (import, adapting to other printers), LLM-usage note, contributing, license.
- `profiles/<Vendor>/{filament,process}/` — published, generated `.ini` bundles (the
  distributables). Filename convention:
  `<Base>__<Printer>_<Slicer>.ini` (no spaces; printer+slicer encoded in the name),
  e.g. `profiles/3DXTech/filament/3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`.
- `docs/` — user-facing setup guides. `CoreOne_custom_filament.md`: creating a custom
  filament on the printer so a non-built-in `filament_type` (e.g. `PEKK-A`, `EMI-ABS`)
  doesn't trigger a wrong-filament warning, with a worked example per such profile. Each
  of those profiles also has a `README__<profile>.md` beside its `.ini`. Printer-side
  values come from the author's slicer profile plus author choices (EMI-ABS: base ABS,
  max chamber 75 °C, filtration on, confirmed 2026-10-17); don't invent them.
- `scripts/extract.py` — GPLv3 tool that splits the master bundle into per-profile files.
- `scripts/validate.py` — GPLv3 pre-commit validator (report-only): profile layout/syntax/
  required keys/inherits cycles/condition syntax, non-built-in `filament_type` covered by
  docs, filament_vendor vs directory, Markdown links/anchors/backticked paths/fences/orphan
  profile readmes (`README__<profile>.md`), no master bundle or `manifest.json` tracked, `manifest.example.json`
  shape. `--check-system-presets` verifies external parents against Prusa's latest
  published bundle (PrusaSlicer-settings-prusa-fff, resolved via `index.idx`). The Core
  One built-in filament list (`BUILTIN_FILAMENT_TYPES`) comes from Prusa-Firmware-Buddy
  `src/common/filament_presets.cpp`; update it if the firmware adds materials.
- `.githooks/pre-commit` — exports the index to a temp dir and runs `validate.py` + the
  offline tests on exactly what's staged. Enabled per clone with `make hooks`
  (`core.hooksPath`); errors block, warnings don't.
- `tests/` — `test_extract.py` and `test_validate.py` (stdlib `unittest`) +
  `fixtures/sample_bundle.ini`. Validator tests build throwaway repo snapshots in temp dirs.
- `manifest.example.json` — template listing which presets to publish.
- `Makefile` — `test`, `test-net`, `validate`, `validate-net`, `check` (validate + test),
  `hooks`, `list`, `publish` targets.
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
5. **Exception: hand-supplied profiles.** The author may hand over a finalized `.ini`
   based on a PrusaSlicer export. Copy it into `profiles/` **verbatim** (verify with `cmp`) and
   do NOT add it to `manifest.json`. Currently:
   `profiles/3DXTech/filament/CARBONX_PEKK-A+CF_HT0.6__PrusaCOREOne_Prusaslicer.ini` (preset
   `3DXTech PEKK-A+CF @COREONE HT0.6 experimental`, inherits system preset
   `Fiberon PPS-CF @COREONE HT0.6`), copied verbatim from the author's finalized
   `~/stuff/src/misc/3DXTech_PEKK-A+CF_COREONE_HT0.6.ini`. To update it, re-copy the
   author's new file; don't regenerate it from a bundle. `README__CARBONX_PEKK-A+CF_HT0.6__PrusaCOREOne_Prusaslicer.md` beside it
   points users to the printer-side `PEKK-A` custom filament settings in `docs/`.

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

- Commit messages end with the `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` trailer.
- Only commit/push when the author explicitly asks.
- **After every push, update this handoff (`CLAUDE.md`) to reflect the new state, then
  commit and push that update.** (Standing instruction from the author.)
- `make check` (validate + offline tests) must pass before committing; the pre-commit hook
  enforces it once `make hooks` has been run in the clone. `make test-net` / `make
  validate-net` additionally hit Prusa's GitHub (pristine bundle parse + parent-preset check).
- Never "fix" a validator finding by editing profile values; report it to the author.
- **The repo lives in OneDrive.** Operations that delete and recreate files (rebase,
  checkout, reset) can make OneDrive leave conflict copies named `<name> 2`. On
  2026-10-17 it renamed `.githooks/` to `.githooks 2/` during a rebase. That commit picked
  up the wrong path, and the hook silently didn't run. After such operations, run
  `find . -path ./.git -prune -o -name '* [0-9]*' -print` and check `ls .githooks`.

## Likely next steps / TODO

- **Sync EMI-ABS vendor back to PrusaSlicer (author):** the published file's
  `filament_vendor` was changed from Generic to 3DXTech at the author's direction
  (2026-10-17; metadata only, no technical values touched). The author's live PrusaSlicer
  preset and master bundle still say Generic. Update them in PrusaSlicer and re-export
  before the next `make publish`, or regenerating will revert it.
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
- Publish more filaments. Published so far: 3DXTech 3DXLABS EMI-ABS (generated) and
  3DXTech PEKK-A+CF HT0.6 (hand-supplied, experimental/uncalibrated). The two other EMI-ABS
  variants were intentionally held back per the author, and so was the paired print profile
  `0.30mm High Temperature @COREONE HT0.6 - PEKK-A` (filament only for now).
- Consider paired custom **process** profiles per filament (manifest already supports it).
- Add CI (GitHub Actions) to run `make check` (and optionally `make validate-net`) on push.
