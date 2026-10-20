---
name: publish-filament
description: Publish, update or sync filament (or process) profiles between the author's PrusaSlicer presets and the repo's profiles/ tree, which is the source of truth. Use when the author wants to add a new profile from PrusaSlicer, pull PrusaSlicer edits into the repo, or check which side differs.
---

# Publishing and syncing profiles

The repo's `profiles/<Vendor>/{filament,process}/*.ini` files are the **source of truth**.
Each is a small, importable PrusaSlicer config bundle; filenames encode printer+slicer and
contain no spaces, e.g. `profiles/3DXTech/filament/3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`.
`scripts/sync.py` compares the repo with PrusaSlicer's user preset directory and copies
from PrusaSlicer into the repo. It never writes to PrusaSlicer: the author loads repo
profiles there by hand (File → Import → Import Config Bundle), so working presets are
never changed. Don't write into PrusaSlicer's directory by any other means either.

## Guardrails (read first)

- **Never author, tune, or flatten profile values.** The tooling only copies preset lines
  verbatim. Editing temperatures/speeds/flow etc. is the human author's job, in the repo
  or in PrusaSlicer. Doing it yourself would break the README's LLM-usage disclosure.
- Report validator findings to the author rather than editing profile values.
- Only commit/push when the author explicitly asks.

## Commands

```sh
make status                 # which repo presets differ from / are missing in PrusaSlicer
python3 scripts/sync.py status --diff [PRESET|FILE ...]   # show the differing lines
make pull                   # PrusaSlicer -> repo, for presets already in the repo
python3 scripts/sync.py add "Exact Preset Name" --vendor Vendor --base FILE_BASE
```

`pull` takes `-n` (dry run); `status` and `pull` take optional preset names or repo file paths.

## Adding a new profile

1. Find the exact preset name: `ls ~/Library/Application\ Support/PrusaSlicer/filament/`
   (the file name minus `.ini`). Skip scratch presets (`- Copy`, `Calibration`, `OLD …`)
   unless asked. Confirm the vendor and filename base with the author.
2. Run `sync.py add`. It includes user-preset parents and prints a `note:` for each parent
   it assumes is a PrusaSlicer system preset.
3. Check the preset's `filament_vendor` matches the vendor directory (the validator warns
   otherwise). Changing it is a metadata edit the author must direct.
4. If its `filament_type` isn't a Core One built-in, it needs a worked example in
   `docs/CoreOne_custom_filament.md` and a `README__<profile>.md` beside the `.ini`, with
   printer-side values from the author (the validator flags this).
5. `make validate-net` (confirms system parents exist) and `make check`.

## Updating a profile

- Author edited in PrusaSlicer: `make pull`, then show the author `git diff profiles/`.
- Author edited in the repo: they import it into PrusaSlicer themselves when ready.
- `make status` first if unsure which side changed. PrusaSlicer 2.9.6 writes
  `filament_flush_speed/volume` on save, so those keys can differ harmlessly.

## Legacy route

`make list` / `make publish` (`scripts/extract.py` + local `manifest.json` + a master
bundle exported to `../PrusaSlicer_config_bundle.ini`) still works, but it regenerates
files from PrusaSlicer and overwrites repo edits. Use it only if the author asks.
