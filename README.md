# fff-profiles

FFF (Fused Filament Fabrication) printing profiles.

## Overview

A collection of 3D printer profiles I've created or modified.

Currently, these profiles only cover the Prusa CORE One+ device, with Prusaslicer. They might be useful as starting points for other setups.


## Usage

These profiles are distributed as PrusaSlicer **config bundles** — single `.ini` files that can contain several named presets (for example, multiple filament profiles) at once. To use one:

1. Download the bundle you want (or clone this repository).
2. Open PrusaSlicer.
3. Go to **File → Import → Import Config Bundle…** and select the `.ini` file, or drag and drop the file onto the PrusaSlicer window.
4. The bundled print, filament, and printer presets will be added to the corresponding dropdowns. Select the ones you want before slicing.

Because these were tuned for a specific setup (Prusa CORE One+), treat them as starting points: review the print, filament, and printer settings and adjust them to match your own hardware, nozzle, and materials before printing.

### Exporting your own profiles

If you want to share your own profiles or contribute changes back, export them as a config bundle:

1. In PrusaSlicer, make sure the presets you want to share are saved (use the save/floppy-disk icon next to each preset dropdown to name and store any modified settings).
2. Go to **File → Export → Export Config Bundle…**.
3. Choose which preset types to include and save the resulting `.ini` file.
4. Share that file, or include it in a pull request (see below).

To export a single active configuration instead of a bundle, use **File → Export → Export Config…**.

## A note on LLM usage

Large language models were used in this project only for administrative and documentation tasks — for example, drafting and tidying this README and organizing the repository. The printing profiles themselves were developed, tuned, and validated by the human author.

## Contributing & reporting issues

Contributions and feedback are welcome:

- **Reporting issues:** Open an issue on the [GitHub issue tracker](../../issues) describing the problem, the profile involved, and your hardware/setup.
- **Contributions:** Fork the repository, make your changes on a branch, and open a pull request. Please describe what you changed and the setup you tested it on.

## License

This project uses two licenses depending on the type of file:

- **Printing profiles and documentation** are licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](LICENSE). You are free to share and adapt them, including for commercial use, as long as you give appropriate credit and distribute any derivatives under the same license.
- **Any code** (scripts, tooling) is licensed under the [GNU General Public License v3.0 (GPLv3)](LICENSE-CODE) — the share-alike equivalent for software.
