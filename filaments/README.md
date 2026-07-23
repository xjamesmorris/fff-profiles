# filaments/

Published, ready-to-import filament profiles — one `.ini` per filament.

Each file is a small PrusaSlicer **config bundle** produced from the maintainer's
master bundle by `scripts/extract.py`. A file contains the filament preset plus
any of its ancestor presets that aren't shipped with PrusaSlicer; parents that
*are* PrusaSlicer system presets are referenced by name and resolved on import.

**To use one:** in PrusaSlicer, `File → Import → Import Config Bundle…` and select
the `.ini`. See the repository [README](../README.md) for details, including how
to adapt a profile to a printer other than the Prusa CORE One+.

These files are generated. Do not hand-edit them here — change the source profile
in PrusaSlicer, re-export the master bundle, and re-run the extractor.
