# Data conventions

## NWCSAF CMA ↔ NWP time matching

**Status: VERIFIED 2026-09-03** against `/scratch/mch/jdelbeke/nwcsaf/MSG_nwcsaf_cosmo1eqc3km_*.nc`
and the 801/802 e-suite output. Supersedes the proposed handover of the same name.

### Confirmed convention

The NWCSAF slot label (the `YYYYMMDDHHMM` in the filename) is the **nominal START of the SEVIRI
repeat cycle**. Verified on six slots spread across the period: `cma.attrs["start_time"]` equals the
filename label exactly in every case, and `end_time` is `start + 743 s` (12.38 min).

743 s is a **full-disk** scan duration, not a subregion window — a Swiss-only strip would be ~30 s.
So the times describe the whole disk and the Swiss acquisition time has to be modelled, not read.

```
slot label 11:00  ->  start_time 11:00:00, end_time 11:12:23
```

### Swiss acquisition offset

SEVIRI scans south → north, linearly in the geostationary N-S scan angle. With the Earth disc
half-angle `arcsin(R_E / R_S) = 0.15168 rad` and the scan duration read from the files:

| latitude | scan fraction | offset from slot label |
|---|---|---|
| equator | 0.500 | +6.19 min |
| 45.8 N | 0.895 | **+11.09 min** |
| 46.8 N | 0.901 | **+11.16 min** |
| 47.8 N | 0.907 | **+11.23 min** |

**Swiss offset = +11.2 min, with only 8 s of north–south spread across 45.8–47.8 N.**

Sensitivity: if the scan is assumed to span up to 5% beyond the Earth disc rather than exactly it,
the offset falls to 10.9 min. So **+11.2 min ± ~0.3 min** is the honest figure.

### Matching rule

Model output for these experiments is **hourly only** (`lff`/`iff`/`iaf`/`inc`/`laf`, 145 files over
144 h — no sub-hourly output exists), so a slot must be chosen rather than interpolated.

```
NWCSAF slot T-15min  <->  model field valid at T
```

| pairing | acquisition vs model valid time |
|---|---|
| slot T (nominal) | **+11.2 min** (obs after model) |
| slot T−15 (adopted) | **−3.8 min** (obs before model) |

CMA is categorical, so temporal interpolation between model fields is not appropriate — nearest-in-time
is the correct rule, and nearest is T−15. The residual is small, signed and near-constant for a fixed
domain, so it documents cleanly instead of appearing as a forecast phase error.

**Apply uniformly. Never mix conventions within a verification period.**

### How much it actually buys

Measured over 144 hours, changing *only* the paired slot (same mask, same domain, same model field):

- pooled `max J`: 0.5002 (nominal) → 0.5047 (matched), **+0.0045**
- per-hour paired difference at the global `tau*`: mean **+0.0035**, matched better in **59%** of hours
- by time of day: night +0.0084, afternoon +0.0044, evening +0.0053, **morning 06–11 UTC −0.0041**
  (the one window where the nominal slot scores better)

A naive Wilcoxon test gives `p = 3e-4`, **but that assumes independent hours and they are not** — the
domain-mean bias decorrelates over ~5 h, so the effective sample is ~29, not 143. On that basis the
improvement is roughly 1.4 standard errors: **not statistically distinguishable from zero.**

So adopt this convention because it is *physically correct and documented*, not because it improves
scores. It does not meaningfully improve them at hourly model output and 3 km cloud fields — the
11-minute mismatch is simply not the limiting error. Do not cite it as a skill improvement.

### Implementation

`scripts/CLCT_threshold_corrected.ipynb` (section 5) does **not** hardcode the offset. It reads
`start_time`/`end_time` from each file, computes the scan fraction from the domain's geostationary
angle, and selects the candidate slot minimising `|imaged_at − T|`. That is deliberately preferred over
a `NWCSAF_SLOT_OFFSET_CH = timedelta(minutes=11)` constant: it self-corrects if the scan duration,
domain or satellite ever changes, and it degrades gracefully when a slot is missing.

Useful side effect: the two genuinely missing slots (2025-10-06 12:00 and 12:15) stop being fatal,
because hour 12:00 is matched to 11:45 anyway.

### Platform

`platform_name = Meteosat-10`, `sensor = seviri`, `resolution = 3000` m, 15-minute repeat cycle
(573 consecutive 15-min gaps in the file listing; the single 45-min gap is the two missing slots).
**Not** MSG RSS (5-min cycle, ~1392 rows) and **not** MTG/FCI (10-min, chunked) — the offsets above
would be wrong for either.

### Known limitation

These files are satpy resamples onto the COSMO-1 3 km grid, and the resampling **dropped the original
NWCSAF global metadata**: there is no `nominal_product_time` and no `time_coverage_start`/`_end` in the
global attributes (only `history` and `Conventions`). What survives is satpy's normalised
`start_time`/`end_time` as *per-variable* attributes.

So strictly this verifies satpy's interpretation of the NWCSAF header rather than the raw header
itself. The conclusion is nonetheless safe: `start_time` matches the filename label exactly on every
slot checked, and a 12.38-minute span is unambiguously a full-disk acquisition. If the raw NWCSAF
header is ever needed, it must be re-extracted with the original global attributes retained — the same
extraction that would be needed to recover the missing `cma_quality` / `cma_conditions` variables
(see the NWCSAF file-internals notes).
