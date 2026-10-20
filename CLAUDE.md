# CLAUDE.md — Session Handoff

Context for future Claude Code sessions working in this repo.

## What this project is

A collection of FFF (Fused Filament Fabrication) 3D printing profiles, authored/tuned by
James Morris. Currently targets the **Prusa CORE One+** using **PrusaSlicer**. Profiles are
published as small, individually importable PrusaSlicer config bundles (one filament each).

- GitHub remote: https://github.com/xjamesmorris/fff-profiles
- Default branch: `main`
- Latest release: **v1.2.0** (2026-10-18, tag on `4778e89`) — 8 new filament profiles
  (see TODO "Publish more filaments"), EMI-ABS/PET printer-side docs + readmes, EMI-ABS
  vendor 3DXTech, pre-commit validation suite, and the repo as source of truth
  (`scripts/sync.py`).
- Previous: **v1.1.0** (2026-10-17, tag on `cc5e7cc`) — 3DXTech CarbonX PEKK-A+CF HT0.6
  profile (+ per-profile readme) and `docs/CoreOne_custom_filament.md`. **v1.0.0**
  (2026-07-23) — first release; extraction tooling + 3DXTech 3DXLABS EMI-ABS.
- Unreleased on `main` since v1.2.0 (2026-10-19, through `b9b39fa`): `install` removed from
  `sync.py` (nothing writes into PrusaSlicer); both PETG-CF profiles withdrawn for
  recalibration. Validator is clean (0 errors, 0 warnings).
- Tags use semver (`vMAJOR.MINOR.PATCH`), annotated (`vX.Y.Z — summary`), each with a
  matching GitHub release (`gh release create`) whose notes follow the v1.0.0 layout.

## Repository layout

- `README.md` — usage (import, adapting to other printers), LLM-usage note, contributing, license.
- `profiles/<Vendor>/{filament,process}/` — published `.ini` bundles (the distributables
  and the source of truth). Filename convention:
  `<Base>__<Printer>_<Slicer>.ini` (no spaces; printer+slicer encoded in the name),
  e.g. `profiles/3DXTech/filament/3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`.
- `docs/` — user-facing setup guides. `CoreOne_custom_filament.md`: creating a custom
  filament on the printer so a non-built-in `filament_type` (e.g. `PEKK-A`, `EMI-ABS`, `PET`)
  doesn't trigger a wrong-filament warning, with a worked example per such profile. Each
  of those profiles also has a `README__<profile>.md` beside its `.ini`. Printer-side
  values come from the author's slicer profile plus author choices (EMI-ABS: base ABS,
  max chamber 75 °C, filtration on, confirmed 2026-10-17; PET: transcribed from photos of the
  author's printer screens, 2026-10-17 — those differ from the slicer profile on nozzle
  290 vs 320 °C and nominal chamber 45 vs 55 °C, and the screens show no Base Preset or
  Heatbreak field); don't invent them.
- `scripts/sync.py` — GPLv3 tool that compares `profiles/` with PrusaSlicer's user preset
  dir and copies one way, PrusaSlicer → repo (`status`, `pull`, `add`). It never writes to
  PrusaSlicer. See "How publishing works".
- `scripts/extract.py` — GPLv3 tool that splits a master bundle into per-profile files.
  Legacy since the repo became the source of truth; `sync.py add` reuses its chain logic.
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
- `tests/` — `test_extract.py`, `test_validate.py`, `test_sync.py` (stdlib `unittest`) +
  `fixtures/sample_bundle.ini`. Validator and sync tests build throwaway repo snapshots
  (and, for sync, a fake PrusaSlicer config dir) in temp dirs.
- `manifest.example.json` — legacy template for `extract.py`.
- `Makefile` — `test`, `test-net`, `validate`, `validate-net`, `check` (validate + test),
  `hooks`, `status`, `pull`, and legacy `list`, `publish` targets.
- `LICENSE` (CC BY-SA 4.0), `LICENSE-CODE` (GPLv3).

## How publishing works

**The repo's `profiles/` tree is the source of truth** (author's decision, 2026-10-18). The
author edits profiles here or in PrusaSlicer. `scripts/sync.py` copies PrusaSlicer → repo
only; **nothing writes into PrusaSlicer's directory** (author's decision, 2026-10-19, so
known-working presets there are never affected). The author loads repo profiles into
PrusaSlicer by hand (File → Import → Import Config Bundle).

1. A repo profile is a small config bundle: `[filament:Name]` + `key = value` lines (some
   carry leading `#` comments, e.g. the hand-supplied PEKK-A+CF file). PrusaSlicer keeps
   the same lines in `<config>/filament/Name.ini` (macOS:
   `~/Library/Application Support/PrusaSlicer/`) under a `# generated by PrusaSlicer …`
   comment. Comparisons ignore comment and blank lines.
   `CARBONX_PEKK-A+CF_HT0.6__…ini` was hand-supplied (copied verbatim from the author's
   `~/stuff/src/misc/3DXTech_PEKK-A+CF_COREONE_HT0.6.ini`); it's now an ordinary repo file.
   Its preset name `3DXTech PEKK-A+CF @COREONE HT0.6 experimental` is canonical (author,
   2026-10-18). The author's older live preset `3DXTech PEKK-A+CF @COREONE HT0.6` (no
   "experimental") is a separate preset; importing the repo file adds it alongside.
2. `make status` lists presets that differ (with changed keys and which side is newer) or
   are missing in PrusaSlicer. `sync.py status --diff` shows the lines.
3. `make install` was removed on 2026-10-19 at the author's request (it wrote into
   PrusaSlicer, with backups under `<config>/fff-profiles-backup/`; the one run, on
   2026-10-18 23:33, left a backup folder there). Don't reintroduce writing into
   PrusaSlicer; a test asserts no command touches the config dir.
4. `make pull` (PrusaSlicer → repo) replaces only the changed section's lines in the repo
   file, keeping its header comments and other sections. The author reviews `git diff`.
5. New profile: `python3 scripts/sync.py add "Exact Name" --vendor V --base B` reads
   PrusaSlicer's preset dir, includes user-preset parents (via `extract.collect`), notes
   system parents (verify with `make validate-net`), and writes
   `profiles/<V>/filament/<B>__PrusaCOREOne_Prusaslicer.ini`. It refuses to overwrite.
6. PrusaSlicer 2.9.6 writes `filament_flush_speed/volume` on every save; older-saved live
   presets lack them, so `status` can show those two keys. That's expected, not a tuning
   change.
7. **Legacy route** (still works, but regenerates from PrusaSlicer and would clobber repo
   edits): master bundle exported to `../PrusaSlicer_config_bundle.ini` (local-only, never
   committed; `.gitignore` blocks `*config_bundle*.ini` and `manifest.json`) +
   `manifest.json` + `make publish` (`extract.py`). The local `manifest.json` still lists
   the generated profiles from 2026-10-18 (PETG-CF entries removed 2026-10-19).

Whoever edits, technical values come from the author only. Claude runs `status`/`pull`/
`add` when asked, and never changes values itself.

## Key decisions (do not silently reverse)

- **Distribution: per-profile config bundles** under `profiles/<Vendor>/{filament,process}/`,
  imported via `File → Import → Import Config Bundle…`. Not one big bundle. Filenames encode
  printer+slicer and contain no spaces (e.g. `3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`).
- **Repo is the source of truth for published profiles** (2026-10-18); sync with
  PrusaSlicer via `scripts/sync.py`. The author's full PrusaSlicer setup (experiments,
  `- Copy` presets, master bundle) stays local/private.
- **Compatible printers condition:** the author sometimes leaves it blank to load presets
  for experiments. Blank is allowed; the validator keeps its non-blocking warning
  (author's choice, 2026-10-18). A named `compatible_printers` list also only warns, but it
  breaks the preset for anyone else, so point it out.
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

- **Validator gap (offered, not requested yet):** it doesn't catch an unterminated quoted
  value (e.g. notes ending `\"`) or a setting line deleted by a hand edit. Both happened in
  CarbonX PETG-CF on 2026-10-18 and were fixed at the author's request.
- **PETG-CF profiles withdrawn (2026-10-19, author: need recalibration):** 3DXTech CarbonX
  PETG-CF 0.4 and 3DXSTAT PETG-CF 0.4 were removed from `profiles/` after shipping in
  v1.2.0. Re-add with `sync.py add` once recalibrated (bases `CARBONX_PETG-CF_0.4`,
  `3DXSTAT_PETG-CF_0.4`).
- **Phaetus aeForce PET-GF annealing info (author has it):** add it to
  `profiles/Phaetus/filament/README__AEFORCE_PET-GF_HT0.6__PrusaCOREOne_Prusaslicer.md`
  (an "Annealing" section) exactly as the author supplies it. Not received yet.
- **Move to the PrusaSlicer 3 series (requested 2026-10-18):** it adds plugins and some
  initial calibration support. Check what changes for these profiles (preset format/keys,
  the sync tool's assumptions about the config dir and file layout, the system-preset
  check, docs that cite 2.9.6) and whether its calibration support can replace part of the
  OrcaSlicer step in the README's "Calibration workflow".
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
- Publish more filaments. Published so far (generated unless noted), vendor set in the
  author's live presets (2026-10-17) so regeneration keeps it:
  3DXTech: 3DXLABS EMI-ABS, ezPC-CF 0.6, HIPS HF0.4, PEKK-A+CF
  HT0.6 (hand-supplied, experimental/uncalibrated); Zyltech: ASA-GF HF0.4, ASA-CF HF0.6;
  Phaetus: aeForce PET-GF HT0.6 (needs the `PET` printer-side filament); PushPlastic:
  PC-PBT-CF 0.6. Selection rule used: user presets with notes and shrinkage values that
  differ from the Prusa parent (shrinkage = author finished dimensional calibration).
  Remaining candidates from that shortlist include the 3D-Fuel PCTG family. The two other
  EMI-ABS variants were intentionally held back per the author, and so was the paired print
  profile `0.30mm High Temperature @COREONE HT0.6 - PEKK-A` (filament only for now).
- Consider paired custom **process** profiles per filament (manifest already supports it).
- Add CI (GitHub Actions) to run `make check` (and optionally `make validate-net`) on push.
