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

Because these were tuned for a specific setup (Prusa CORE One+), treat them as starting points: review the print, filament, and printer settings and adjust them to match your own hardware, nozzle, and materials before printing.

### Using these on a different printer

Each filament preset carries a compatibility condition targeting the Prusa CORE One
(for example `printer_model=~/(COREONE…)/ and nozzle_diameter[0]==0.4`), so on another
printer the filament may show as **incompatible** and stay hidden. To adapt one:

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

## A note on LLM usage

Large language models were used in this project only for administrative work:
documentation (this README), repository organization, and the **tooling** that
packages and validates the profiles — the extraction script under `scripts/` and its
test suite. That tooling only *selects and copies* presets; it does not author, tune,
or alter any of the profiles' technical values.

The printing profiles themselves — every temperature, speed, flow, and cooling value —
were developed, tuned, and validated by the human author.

## Repository layout

| Path | What it is |
| --- | --- |
| `profiles/<Vendor>/{filament,process}/` | Published, ready-to-import profiles (generated). |
| `scripts/extract.py` | Splits the maintainer's master config bundle into the per-profile files. |
| `tests/` | Test suite for the tooling, plus a fixture bundle. |
| `manifest.example.json` | Template listing which presets to publish. |
| `LICENSE`, `LICENSE-CODE` | CC BY-SA 4.0 (profiles/docs) and GPLv3 (code). |

The full master bundle is maintained locally by the author and is not committed; only
the curated per-filament outputs are published.

## Development

The tooling is plain Python 3 (standard library only — no dependencies).

```sh
make test          # run the offline test suite
make test-net      # also validate against a pristine bundle pulled from Prusa's GitHub
make list          # list presets in your local master bundle
make publish       # regenerate profiles/ from manifest.json
```

See `scripts/extract.py --help` for direct usage.

## Contributing & reporting issues

Contributions and feedback are welcome:

- **Reporting issues:** Open an issue on the [GitHub issue tracker](../../issues) describing the problem, the profile involved, and your hardware/setup.
- **Contributions:** Fork the repository, make your changes on a branch, and open a pull request. Please describe what you changed and the setup you tested it on.

## License

This project uses two licenses depending on the type of file:

- **Printing profiles and documentation** are licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](LICENSE). You are free to share and adapt them, including for commercial use, as long as you give appropriate credit and distribute any derivatives under the same license.
- **Any code** (scripts, tooling) is licensed under the [GNU General Public License v3.0 (GPLv3)](LICENSE-CODE) — the share-alike equivalent for software.
