# Adding a custom filament on the Prusa Core One

Some profiles in this repository tag prints with a filament type the Core One doesn't have
built in (for example `PEKK-A`). Each sliced G-code file records its `filament_type`, and the
printer compares it with the name of the filament you loaded. If the printer has no filament
with that name, it shows a **wrong-filament warning** when you start a print.

The fix is a one-time setup on the printer: create a custom filament whose name matches the
profile's `filament_type`.

## General steps

1. Find the profile's filament type: in PrusaSlicer, **Filament Settings → Advanced →
   Filament type**, or the `filament_type = …` line in the `.ini`.
2. On the printer, go to **Manage Filaments → Edit Filaments** and pick an empty custom slot.
3. Fill in the fields (see below).
4. If the new filament doesn't show up when loading, turn it on under **Manage Filaments**
   (the filament visibility setting).
5. When loading the spool, choose the new filament.

### Field guide

| Setting | What to enter |
|---|---|
| Name | Exactly the profile's `filament_type`, including capital letters and punctuation |
| Base Preset | The closest built-in material (often the one the slicer profile is based on) |
| Nozzle / Bed Temperature | The slicer profile's `temperature` / `bed_temperature` |
| Minimum / Nominal Chamber Temperature | The slicer profile's `chamber_minimal_temperature` / `chamber_temperature` |
| Is Abrasive | On for filled filaments (carbon fiber, glass fiber, etc.) |
| Is Flexible | On only for flexible filaments (TPU and similar) |
| Requires Filtration | On if the material needs it and you have a filter fitted |

## Worked example: 3DXTech PEKK-A+CF

Profile: [`profiles/3DXTech/filament/CARBONX_PEKK-A+CF_HT0.6__PrusaCOREOne_Prusaslicer.ini`](../profiles/3DXTech/filament/CARBONX_PEKK-A+CF_HT0.6__PrusaCOREOne_Prusaslicer.ini)

Experimental, uncalibrated profile. Based on Prusa's Fiberon PPS-CF @COREONE HT0.6 profile.

### Requirements

- PrusaSlicer 2.9.6 or newer
- Prusa system profiles 2.5.11 or newer (**Configuration → Check for Configuration Updates**)
- Core One with the HT400 hotend, standard-flow 0.6 mm nozzle, and the high-temperature idler door

### 1. Import the slicer profile

In PrusaSlicer, use **File → Import → Import Config Bundle** and select
`CARBONX_PEKK-A+CF_HT0.6__PrusaCOREOne_Prusaslicer.ini`. It appears as
**3DXTech PEKK-A+CF @COREONE HT0.6 experimental** under filaments.

### 2. Add a PEKK-A custom filament on the printer

The slicer profile tags prints as `PEKK-A`. On the printer, go to
**Manage Filaments → Edit Filaments**, pick an empty custom slot, and set:

| Setting | Value | Notes |
|---|---|---|
| Name | `PEKK-A` | Must match exactly, including capital letters and the hyphen |
| Base Preset | PPS | Closest built-in material; the slicer profile is also based on PPS-CF |
| Nozzle Temperature | 375 °C | Same as the slicer profile |
| Nozzle Preheat Temperature | leave default | |
| Bed Temperature | 120 °C | Same as the slicer profile |
| Heatbreak Temperature (if shown) | 50 °C | The profile's start G-code sets this anyway |
| Minimum Chamber Temperature | 40 °C | Same as the slicer profile |
| Nominal Chamber Temperature | 55 °C | Same as the slicer profile |
| Maximum Chamber Temperature | 65 °C | Matches the printer's built-in PPS settings |
| Is Abrasive | On | Carbon-fiber filled |
| Is Flexible | Off | |
| Requires Filtration | Off | Optional; turn on if you run a filter |

When loading, choose **PEKK-A**. If it isn't in the list, turn it on under **Manage Filaments**
(the filament visibility setting).

> ⚠️ **Fit the high-temperature idler door yourself before loading.** The printer reminds you
> about it for its built-in PPS and PPA filaments, but not for custom ones.

---

Menu names and fields are taken from the Core One firmware source (v6.10.1) and may differ
slightly on other firmware versions.
