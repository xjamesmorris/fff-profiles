# 3DXTech 3DXLABS EMI-ABS — Core One

Profile: [`3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini`](3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini)
(appears in PrusaSlicer as **3DXTech 3DXLABS EMI-ABS**).
The standard structural profile; not tuned for EMI characterization.

## Printer setup required

This profile tags prints with filament type `EMI-ABS`, which the Core One doesn't have built
in. **Before printing, create a custom filament named `EMI-ABS` on the printer**, or it will
show a wrong-filament warning when you start a print.

The settings to enter (name, base preset, temperatures, abrasive flag, etc.) are listed in
[Add an EMI-ABS custom filament on the printer](../../../docs/CoreOne_custom_filament.md#2-add-an-emi-abs-custom-filament-on-the-printer).

## Requirements

- Core One (or Core One L) with a standard-flow nozzle; not for 0.6 mm or 0.8 mm nozzles
- Hardened (abrasion-resistant) nozzle

The filament is brittle: preheat the nozzle before loading, don't over-tighten the idler
screws, and turn off auto-retract. See the
[full EMI-ABS walkthrough](../../../docs/CoreOne_custom_filament.md#worked-example-3dxtech-3dxlabs-emi-abs).
