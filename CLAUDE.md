# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A personal collection of Jupyter notebooks (`scripts/`) for processing and comparing MeteoSwiss ICON
NWP forecast data and NWCSAF satellite products at CSCS — cloud cover comparisons, ICON-to-NWCSAF
regridding, inversion/sounding analysis, KENDA/IAU consistency checks, etc.

This was forked from MeteoSwiss's `nwp-fdb-polytope-demo` repo, but none of these notebooks actually
use FDB or the Polytope HTTP service — they read GRIB/NetCDF files directly off `/store`/`/scratch` at
CSCS via `earthkit.data.from_source("file", ...)` and process them with `earthkit`, `xarray`, `cartopy`,
`scipy`, `pandas`, `matplotlib`. What's kept from the original demo repo is only the dependency stack
(`pyproject.toml`/`poetry.lock`) and the CSCS kernel setup (`host/`), since those two provide the
`eccodes`/`eckit`/`mir` native libraries these notebooks need. There is no build step, lint config, or
test suite — the repo's only "product" is the notebooks themselves.

## Why: the research question behind the notebooks

These notebooks exist to investigate a "spin-up/spin-down" bias in ICON-CH1/KENDA-CH1 total cloud cover
(CLCT) forecasts: error metrics shift for ~4-6h after each forecast initialization, with a seasonally-varying
diurnal pattern, before settling. The investigation compares ICON/KENDA verification scores against NWCSAF
satellite products and Payerne sounding-derived inversion strength, and includes dedicated assimilation
e-suite experiments (e.g. excluding T_2M/RH_2M) to isolate the cause. The plots and comparison GIFs these
notebooks produce feed a running findings write-up shared with the team — that write-up (not the notebooks
themselves) is the actual deliverable. Detailed findings-to-date and the current working hypotheses
extracted from it live in Claude's memory (project/reference entries), not here — ask to recall them
rather than expecting this file to carry the full history.

## Environment setup (CSCS)

```bash
bash host/install_kernel.sh
```
Pulls a pre-built `uenv` image (name recorded in `host/.fdb_image`) and registers a Jupyter kernel
("polytope demo") that launches Python through `host/uenv-wrapper.sh`, which runs code inside
`uenv run --view=realtime <image> -- /user-environment/venvs/fdb/bin/python3.11`. In VSCode, select it
via `Ctrl-Shift-P → Notebook: Select Notebook Kernel → Select Another Kernel → Jupyter Kernel → Polytope
demo` (may need `Developer: Reload Window` afterwards for VSCode to see a freshly installed kernel).

Dependencies (`pyproject.toml`) pin `earthkit-*` to 1.0 release-candidate versions and pull
`eccodes-cosmo-resources-python-internal` from the MeteoSwiss internal PyPI mirror (`pypi-mch` source) —
this package is not on public PyPI, so `poetry install` only works from a network with access to it
(e.g. at CSCS or over the MeteoSwiss VPN).

## Patterns used across notebooks

- `eccodes` is imported before `earthkit.data` purely as a workaround so downstream native libraries
  pick up the correct shared libraries — keep this import order when writing new scripts.
- ICON files are read directly by path (e.g.
  `/store_new/mch/msopr/osm/ICON-CH1-EPS/FCST25/<cycle>/grib/...`) and NWCSAF files from
  `/scratch/mch/<user>/nwcsaf/`; there's no request/query abstraction — just `xr.open_dataset(...)` or
  `earthkit.data.from_source("file", ...)` followed by `.to_xarray()`.
- Regridding between ICON's native triangular mesh and the NWCSAF/regular grid uses either
  `earthkit.geo.grids.regrid` (nearest-neighbour/linear cases) or, for the conservative area-weighted
  case, hand-rolled triangle/cell clipping — see `scripts/legacy/depr_NWCSAF.ipynb` for the derivation.
- `scripts/legacy/` holds superseded/experimental notebooks kept for reference — don't treat them as
  the current pattern to follow; prefer whatever lives directly under `scripts/`.
