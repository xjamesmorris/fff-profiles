# fff-profiles

FFF (Fused Filament Fabrication) printing profiles.

## Overview

A collection of 3D printer profiles I've created or modified.

Currently, these profiles only cover the Prusa CORE One+ device, with Prusaslicer. They might be useful as starting points for other setups.


## Usage

Profiles are published individually under [`profiles/`](profiles/), organised by vendor as
`profiles/<Vendor>/filament/<Base>__<Printer>_<Slicer>.ini` (the target printer and slicer
are encoded in the filename). Each file is a small PrusaSlicer **config bundle**: it holds
the filament preset (plus any of its non-system parent presets, and optionally a paired
print/process and printer preset). To use one:

1. Download the `.ini` you want (or clone this repository).
2. Open PrusaSlicer.
3. Go to **File → Import → Import Config Bundle…** and select the `.ini` file, or drag and drop the file onto the PrusaSlicer window.
4. The imported presets are added to the corresponding dropdowns. Select the filament (and, if included, the print/printer preset) before slicing.

### Printer-side setup

Some profiles tag prints with a filament type the Core One doesn't have built in (for
example `PEKK-A` or `EMI-ABS`). For those, create a matching custom filament on the printer
first, or it will show a wrong-filament warning when you start a print. See
[Adding a custom filament on the Prusa Core One](docs/CoreOne_custom_filament.md), which
has the exact printer settings and hardware requirements for each such profile.

Because these were tuned for a specific setup (Prusa CORE One+), treat them as starting points: review the print, filament, and printer settings and adjust them to match your own hardware, nozzle, and materials before printing.

### Using these on a different printer

Each filament preset carries a compatibility condition targeting the Prusa CORE One
(for example `printer_model=~/(COREONE…)/ and nozzle_diameter[0]==0.4`), so on another
printer the filament may show as **incompatible** and stay hidden. Some profiles are
narrower still: the 3DXTech PEKK-A+CF profile only matches a CORE One with the HT400 hotend
and a standard-flow 0.6 mm nozzle. To adapt one:

- Select a printer profile for **your** machine first, then either edit the filament's
  *Compatible printers condition* (Filament Settings → Advanced) to match, or tick
  *All* to show it regardless.
- Re-check temperatures, cooling, flow, and max volumetric speed against your hotend and
  extruder — these were tuned for the CORE One's high-flow hardware and are the settings
  most likely to need adjusting.

### Exporting your own profiles

If you want to share your own profiles or contribute changes back, export them as a config bundle:

1. In PrusaSlicer, make sure the presets you want to share are saved (use the save/floppy-disk icon next to each preset dropdown to name and store any modified settings).
2. Go to **File → Export → Export Config Bundle…**.
3. Choose which preset types to include and save the resulting `.ini` file.
4. Share that file, or include it in a pull request (see below).

To export a single active configuration instead of a bundle, use **File → Export → Export Config…**.

## Calibration workflow (OrcaSlicer → PrusaSlicer)

These profiles were **initially calibrated in [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer)**,
using its built-in calibration tooling (flow, temperature, pressure advance, etc.), and then
**transferred to PrusaSlicer for finishing** and day-to-day use.

If you want to follow a similar workflow, be aware of some CORE One gotchas on the OrcaSlicer
side:

- **Pressure advance** is configured differently between the two slicers — don't copy the value
  across blindly; re-check it in the target slicer.
- OrcaSlicer needs **custom G-code** for things the Prusa firmware/PrusaSlicer handle more
  directly, notably the **heatbreak (cooling) temperature** and the **filtration fan** (if you
  have one installed).

A dedicated write-up of these differences (and possibly a conversion helper) is planned — see
the TODOs in `CLAUDE.md`.

## A note on LLM usage

Large language models were used in this project only for administrative work:
documentation (this README), repository organization, and the **tooling** that
packages and validates the profiles — the extraction and validation scripts under
`scripts/`, their test suites, and the pre-commit hook. That tooling only *selects, copies and checks* presets; it does not author, tune,
or alter any of the profiles' technical values.

The printing profiles themselves — every temperature, speed, flow, and cooling value —
were developed, tuned, and validated by the human author.

## Repository layout

| Path | What it is |
| --- | --- |
| `profiles/<Vendor>/{filament,process}/` | Published, ready-to-import profiles (generated). |
| `docs/` | Setup guides (e.g. adding a custom filament on the Core One). |
| `scripts/extract.py` | Splits the maintainer's master config bundle into the per-profile files. |
| `scripts/validate.py`, `.githooks/` | Pre-commit validation of profiles, docs and repo hygiene. |
| `tests/` | Test suite for the tooling, plus a fixture bundle. |
| `manifest.example.json` | Template listing which presets to publish. |
| `LICENSE`, `LICENSE-CODE` | CC BY-SA 4.0 (profiles/docs) and GPLv3 (code). |

The full master bundle is maintained locally by the author and is not committed; only
the curated per-filament outputs are published.

## Development

The tooling is plain Python 3 (standard library only — no dependencies).

```sh
make hooks         # once per clone: enable the pre-commit hook
make check         # validate + offline tests (what the pre-commit hook runs)
make validate      # check profiles, docs and repo hygiene
make validate-net  # also verify parent presets against Prusa's published system bundle
make test          # run the offline test suite
make test-net      # also validate against a pristine bundle pulled from Prusa's GitHub
make list          # list presets in your local master bundle
make publish       # regenerate profiles/ from manifest.json
```

See `scripts/extract.py --help` and `scripts/validate.py --help` for direct usage.

### Validation

`scripts/validate.py` checks the repository before each commit (via the pre-commit hook in
`.githooks/`, enabled with `make hooks`). It validates exactly what's staged:

- **Profiles:** file layout and naming; INI syntax (no malformed lines, duplicate keys or
  presets, or `[presets]` block); required keys; inheritance cycles; well-formed
  compatibility conditions; and that a filament type the Core One doesn't have built in is
  covered by the printer-side setup docs. `make validate-net` also confirms every parent
  preset exists in Prusa's current system bundle (catching dangling parents).
- **Docs:** relative links and `#anchors` resolve, backticked repo paths exist, code fences
  are closed, and each profile readme (`README__<profile>.md`) has a matching `.ini`.
- **Repo hygiene:** the master config bundle and the local `manifest.json` are never
  committed; `manifest.example.json` is well-formed.

Errors block the commit; warnings are printed but don't (`--strict` makes them fail too).
The validator only *reports*. It never edits profiles or judges tuned values. Bypass the
hook in an emergency with `git commit --no-verify`.

## Contributing & reporting issues

Contributions and feedback are welcome:

- **Reporting issues:** Open an issue on the [GitHub issue tracker](../../issues) describing the problem, the profile involved, and your hardware/setup.
- **Contributions:** Fork the repository, make your changes on a branch, and open a pull request. Please describe what you changed and the setup you tested it on.

## License

This project uses two licenses depending on the type of file:

- **Printing profiles and documentation** are licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](LICENSE). You are free to share and adapt them, including for commercial use, as long as you give appropriate credit and distribute any derivatives under the same license.
- **Any code** (scripts, tooling) is licensed under the [GNU General Public License v3.0 (GPLv3)](LICENSE-CODE) — the share-alike equivalent for software.
