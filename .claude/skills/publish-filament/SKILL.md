---
name: publish-filament
description: Publish one or more filament profiles from the local PrusaSlicer master config bundle into the repo's filaments/ directory. Use when the author wants to extract, package, or release a filament (optionally with a paired process/printer) from their bundle, or regenerate filaments/*.ini.
---

# Publishing a filament profile

This repo distributes PrusaSlicer profiles as small, individually importable config
bundles under `filaments/`, generated from the author's master bundle by
`scripts/extract.py`. Use this workflow to publish or update one.

## Guardrails (read first)

- **Never author, tune, or flatten profile values.** The tooling only *selects and
  copies* presets verbatim. Editing temperatures/speeds/flow etc. is the human author's
  job — doing so would break the project's LLM-usage disclosure (see README).
- **The master bundle is local-only and never committed** (`.gitignore` blocks
  `*config_bundle*.ini`). Default path: `../PrusaSlicer_config_bundle.ini`.
- Only commit/push when the author explicitly asks.

## Steps

1. **Find the exact preset name(s).** Names contain spaces/`@`, so list them:
   ```sh
   make list                       # or: python3 scripts/extract.py --source <bundle> --list
   ```
   Ignore scratch presets (`- Copy`, `Calibration`, `simple`, `OLD …`) unless asked.

2. **Add entries to `manifest.json`** (copy from `manifest.example.json` if absent). Each
   filament entry: `name` (required), optional `slug`, `print` (paired process), `printer`.

3. **Generate:**
   ```sh
   make publish                    # runs extract.py against manifest.json
   ```

4. **Review the output and any notes.** Each `note: references parent not in bundle …`
   means an ancestor wasn't found and is assumed to be a PrusaSlicer *system* preset. Verify
   that's true — a genuine system preset (e.g. `Generic PETG @COREONE`) is fine, but an
   unexpected name may be a **dangling parent** (a deleted user preset) that makes the export
   incomplete. Fix the master bundle if so.

5. **Sanity-check the file**: it should contain the filament section (plus any included
   parents/print/printer) and **no `[presets]` block**. If you can, import it into
   PrusaSlicer via `File → Import → Import Config Bundle…` to confirm it loads clean.

6. **Run the tests** before committing tooling changes: `make test` (offline). Optionally
   `make test-net` to validate the parser against a pristine bundle from Prusa's GitHub.

7. Commit `filaments/*.ini` (and `manifest`-related changes) **only when asked**, with the
   `Co-Authored-By: Claude Opus 4.8` trailer.
