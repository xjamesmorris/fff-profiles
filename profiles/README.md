# profiles/

Published, ready-to-import PrusaSlicer profiles, organised by vendor:

```
profiles/<Vendor>/filament/<Base>__<Printer>_<Slicer>.ini
profiles/<Vendor>/process/<Base>__<Printer>_<Slicer>.ini
```

- **`<Vendor>`** — the filament manufacturer (e.g. `3DXTech`).
- **`filament/` vs `process/`** — filament (material) profiles vs print (process) profiles.
- **filename** — `<Base>__<Printer>_<Slicer>.ini`, no spaces; the target printer and slicer
  are encoded in the name (e.g. `3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`).

Each file is a small PrusaSlicer **config bundle** produced from the maintainer's master
bundle by `scripts/extract.py`. It contains the preset plus any of its ancestors that
aren't shipped with PrusaSlicer; ancestors that *are* system presets are referenced by name
and resolved on import.

**To use one:** in PrusaSlicer, `File → Import → Import Config Bundle…` and select the `.ini`.
See the repository [README](../README.md), including how to adapt a profile to a printer
other than the Prusa CORE One+.

These files are generated — don't hand-edit them here. Change the source profile in
PrusaSlicer, re-export the master bundle, and re-run the extractor.
