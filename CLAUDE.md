# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A collection of Jupyter notebooks and small Python scripts demonstrating how to access and process
MeteoSwiss ICON NWP forecast data (ICON-CH1-EPS, ICON-CH2-EPS, and the REA-L-CH1 reanalysis) via two
different access paths:

- **FDB** (`examples/FDB/`) — direct library access to full horizontal fields. Only works from inside
  CSCS (Balfrin/Alps), requires the `pyfdb`/`fdb-utils` libraries and a `uenv` environment. Not usable
  from outside CSCS.
- **Polytope** (`examples/Polytope/`) — an HTTP feature-extraction service (bounding boxes, polygons,
  time series, trajectories, vertical profiles). Reachable from CSCS, LabVM, and ACPM (not CSCS-restricted).

There is no application code to build or a test suite to run; the repo's "product" is the notebooks
themselves plus the environment plumbing needed to execute them. `pyproject.toml` declares
`testpaths = ["test"]` but no `test/` directory currently exists.

## Environment setup

Two ways to get a working environment, described in the root `README.md`:

**At CSCS (needed for FDB access):**
```bash
bash host/install_kernel.sh
```
This pulls a pre-built `uenv` image (name recorded in `host/.fdb_image`) and registers a Jupyter kernel
("polytope demo") that launches Python through `host/uenv-wrapper.sh`, which runs code inside
`uenv run --view=realtime <image> -- /user-environment/venvs/fdb/bin/python3.11`. In VSCode, select it
via `Ctrl-Shift-P → Notebook: Select Notebook Kernel → Select Another Kernel → Jupyter Kernel → Polytope demo`
(may need `Developer: Reload Window` afterwards for VSCode to see a freshly installed kernel).

**Anywhere (Polytope-only, no FDB):**
```bash
poetry install
poetry run python -m ipykernel install --user --name=polytope-env --display-name "polytope demo"
```

Dependencies (`pyproject.toml`) pin `earthkit-*` to 1.0 release-candidate versions and pull
`eccodes-cosmo-resources-python-internal` from the MeteoSwiss internal PyPI mirror (`pypi-mch` source) —
this package is not on public PyPI.

The `examples/FDB/rea-l-ch1/regrid.py` script has its own separate `pyproject.toml` and a different
setup because it depends on `meteodata-lab` and `pygribjump`:
```bash
cd examples/FDB/rea-l-ch1/
uenv start --view=rea-l-ch1 fdb/5.18:v1
poetry install
poetry run python regrid.py
```

Polytope credentials go in a git-ignored `config.yml` (see `examples/Polytope/config_example.yml` for
the shape: separate `meteoswiss`/`ecmwf` key blocks). Never commit real `config.yml`, `.fdb_image`, or
any notebook containing an `EmailKey`/`Bearer` token — see the notebook workflow below, which enforces
this at snapshot time.

## Notebook development workflow

Documented in `DEVELOPMENT.md`. When you change a notebook:

1. Run all cells in the notebook so outputs are populated.
2. Generate an HTML snapshot for `examples/snapshots/` (referenced from the README so viewers don't
   need to run the notebook themselves):
   ```bash
   ./make_snapshots.sh -s                                        # all notebooks under examples/FDB, examples/Polytope
   ./make_snapshots.sh -s examples/Polytope/feature_time_series.ipynb   # single notebook
   ```
   This step aborts with an error if it detects `EmailKey` or `Bearer` in a notebook's source — treat
   that as a hard stop and remove/obfuscate the secret before retrying.
3. Clear outputs before committing the notebook itself (keeps diffs reviewable):
   ```bash
   ./make_snapshots.sh -c examples/Polytope/feature_time_series.ipynb
   ```
4. Update the notebook list in `README.md` (mirrors `examples/FDB` and `examples/Polytope`, each linked
   alongside its rendered HTML snapshot).
5. Commit both the notebook and its regenerated snapshot together:
   ```bash
   git add examples/snapshots examples/FDB examples/Polytope
   ```

`make_snapshots.sh` prefers `poetry run jupyter` when Poetry is available, otherwise falls back to a
bare `jupyter` on PATH.

## Data-access patterns used across notebooks/scripts

- Requests to both FDB and Polytope are expressed as MARS-style request dicts (`date`, `time`, `stream`,
  `class`, `expver`, `model`, `type`, `levtype`, `param`, `step`, etc.) — see the `.mars` files under
  `examples/FDB/*/` for canonical examples, and the `req = {...}` dict in
  `examples/FDB/rea-l-ch1/wind_10M.py` for the Python equivalent. `model` is `icon-rea-l-ch1` for
  reanalysis or `icon-ch1-eps`/`icon-ch2-eps` for realtime forecasts.
- Parameter shortnames (e.g. `U_10M`, `V_10M`) are resolved to numeric ICON param IDs via
  `shortname_to_paramid(...)` from `uenv_param_map` before being placed in the request.
- Data is loaded through `earthkit.data.from_source("fdb", req, stream=True).to_fieldlist()` (use
  `stream=True` — full-resolution ICON output usually won't fit in memory otherwise), then converted
  per-field to `xarray.Dataset` via `.to_xarray()`.
- `eccodes` is imported before `earthkit.data` purely as a workaround so `fdb` picks up the correct
  shared libraries (see comment referencing APNRZ-998 in `wind_10M.py`) — keep this import order when
  writing new FDB scripts.
- The realtime FDB only holds the **latest day** of forecasts. Requests should use `date` = today and
  `time` on the model's actual cycle boundaries (every 3h for ICON-CH1-EPS, every 6h for ICON-CH2-EPS).
- Regridding between ICON's native triangular mesh and regular/target grids uses either
  `earthkit.geo.grids.regrid` (simple nearest-neighbour/linear cases) or, for the more involved
  conservative-area-weighted case, hand-rolled triangle/cell clipping (see the older notebooks under
  `examples/Polytope/legacy/`).
- `examples/Polytope/legacy/` holds superseded/experimental notebooks kept for reference — don't treat
  them as the current pattern to follow; prefer whatever lives directly under `examples/Polytope/`.
