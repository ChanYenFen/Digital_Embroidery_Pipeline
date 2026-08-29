# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Rhino/Grasshopper pipeline that turns curve geometry into embroidery machine instructions
(`.DST`). The GH definition is `src/gh/01_Embroidery_Pipeline.gh`; its Python logic lives in
`src/script/`. Curve-path sorting has a C++ backend: `src/script/native/curve_sort.cpp` builds
a nanoflann kd-tree and runs greedy nearest-neighbor + 2-opt, compiled to
`src/script/native/curve_sort.dll` and called from `geometry_utils.py` via `ctypes` as a
drop-in swap for the pure-Python R-Tree sorter.

## Execution model

These `.py` files run inside Rhino's embedded interpreter via GH Python components, not standalone.
Names like `curves_tree`, `native_sort`, `if_flip`, `pts_nested`, `export`, `in_dict` under
`if __name__ == "__main__":` are undefined in-file by design — GH wires them in from upstream nodes.
`Rhino.Geometry`/`ghpythonlib` only exist inside Rhino, so there's no way to run or test this code,
and no lint/build/test command in the repo. `requirements.txt` only covers external-IDE code reading.

`_reload.unload_modules()` force-unloads modules by prefix so GH re-reads edits without restarting
Rhino (see the `unload_modules("emb_constants")` calls atop `emb_prepro.py`/`emb_write_dst.py`).

## Pipeline stages (src/script/)

1. **patternfilter.py** — `PatternFilter` converts a point path into a stitch pattern (zigzag /
   cross / decorative / arrow / feather) by per-path type index.
2. **geometry_utils.py** — orders curves into one continuous path (Python R-Tree or native backend).
3. **emb_prepro.py** — adds start/end caps, jump-threshold tie-ins/outs, and inter-segment travel
   paths; mirrors coords per `MIRROR`; outputs the flat `out_dict` (STITCH_INDEX/PATH_INDEX/X/Y/
   COLOR/TYPE).
4. **emb_write_dst.py** — turns `in_dict` into `pyembroidery` STITCH/JUMP/TRIM/COLOR_CHANGE
   commands (subdividing long stitches past `JUMP_THRESHOLD`, pausing for `CABLE_STOP_TYPES`),
   writes `.dst` + `.csv` under `data/`. `emb_write_dst_old.py` is the prior version, kept for reference.

`emb_constants.py` is the single source of truth for stitch-type sets (`THREAD_STITCH_TYPES`,
`CABLE_STOP_TYPES`) and thresholds — units are 0.1mm machine units (`JUMP_THRESHOLD = 121` = 12.1mm).

## Curve sorting backends

`geometry_utils.py` exposes two interchangeable sorters, both greedy nearest-neighbor + optional
2-opt, both returning `(ordered_curves, ordered_indices)`:

- `sort_curves_by_rtree` — pure Python, `Rhino.Geometry.RTree`.
- `sort_curves_native` — same algorithm via `ctypes` into `curve_sort.dll`/`.dylib`; adds `knn_k`
  and `if_flip`. `native_bridge.py` owns loading the native library (picks `.dll`/`.dylib`/`.so`
  by `platform.system()`) and declaring the `ctypes` signature (cached in a module-level handle);
  `misc.py` marshals curves to a flat `[sx,sy,sz,ex,ey,ez,...]` double buffer and rebuilds
  `Rhino.Geometry.Curve` objects from the returned order/reversal arrays. Pass
  `return_travel_points=True` to also get back the native inter-curve travel path (a list of
  `(start, end)` `Point3d` tuples, one per curve: `start_pt`→first curve, then each curve's
  exit→the next curve's entry) — the default `False` keeps the 2-tuple return so
  `sort_curves_native`/`sort_curves_by_rtree` stay interchangeable via the same `partial(...)` call
  in `geometry_utils.py`'s `__main__` block; this is independent of `emb_prepro.py`'s own
  (post-pattern-filter, jump-arc) travel-path logic, not a replacement for it.

Boundary contract: only flat coordinate/index arrays cross the ctypes boundary, never geometry
objects. `if_flip=False` fixes direction (head→tail only): reversal stays all-zero and 2-opt is
skipped, since reversing a sub-sequence would flip curve directions. 2-opt itself is exhaustive
O(n²) up to `TWO_OPT_WINDOW_THRESHOLD` (10000) curves; above that it switches to a windowed search
over a second kd-tree built on current tour-edge midpoints (`WINDOW_K` = 500 nearest candidates per
edge instead of all pairs) — an accepted accuracy/speed trade-off, not a bug, measured at ~2% worse
total travel than exhaustive in exchange for an order-of-magnitude fewer comparisons.

`curve_sort.dll` (Windows, MSVC) and `curve_sort.dylib` (macOS, clang) in `src/script/native/` are
prebuilt and checked in as binaries — there's no in-repo build script. Rebuild `.dll` with `cl.exe`
against `nanoflann.hpp` on Windows; rebuild `.dylib` on macOS with
`clang++ -std=c++17 -O2 -shared -fPIC -o curve_sort.dylib curve_sort.cpp`. Do this whenever
`curve_sort.cpp` changes — each platform's binary is stale until rebuilt on that platform. The
`.obj`/`.lib`/`.exp` MSVC link intermediates are gitignored (see `.gitignore`), not tracked.

## Repo layout

- `cad/` — Rhino `.3dm` reference/example files.
- `data/` — pipeline outputs (`csv/`, `dst/`).
- `src/gh/` — Grasshopper `.gh` definitions.
- `src/script/` — Python pipeline stages, plus `native/` for the C++ sort backend.
  `_reload.py` (GH module-reload helper) and `native_bridge.py` (DLL loading/ctypes signature)
  are small supporting modules split out of `misc.py`/`geometry_utils.py`.
