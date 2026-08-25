# digital-stitch-pipeline

Author: Yen-Fen Chan

A computational-design pipeline built for Rhino + Grasshopper that turns embroidery/cable-stitch
curve designs into machine-ready `.DST` files — covering stitch pattern generation, path
optimization, and export in one workflow.

**Requires Rhino 8** — the pipeline runs inside Rhino's Grasshopper environment and won't run
standalone with just Python.

## Highlights

- **Pattern generation** — turns guide curves into stitch patterns (zigzag, cross, decorative,
  arrow, feather) automatically.
- **Fast path optimization** — a custom C++ engine (k-d tree + greedy/2-opt search) sorts the
  stitch path to minimize travel, handling 3000+ curves in real time — far beyond what the
  pure-Python fallback can do.
- **Machine-ready export** — one step to `.DST` (the industry-standard embroidery format), with
  tie-stitches, jump-thread handling, and cable color-change logic built in, plus a CSV log for QA.

## Installation

If you are developing or reviewing the code in an external IDE (like VSCode), install the dependencies via pip:

```
pip install -r requirements.txt
```

## Run (Rhino Grasshopper Environment)

For Rhino 8 Grasshopper Users (Native CPython 3)
You do not need to use the command line to install dependencies. The Grasshopper Python components in this project use Rhino 8's native package manager. 

Simply open the Grasshopper definition and run the script in the top left canvas "Check & Install Modules"; Rhino will automatically read the `# r: package_name` headers and install the required modules internally.


## SVG Pre-processing Workflow

Before the Grasshopper pipeline runs, stitch layers are prepared in a standalone browser tool
(`tools/svg-stitch-editor.html`) that writes the stitch parameters into each layer's name.

1. Double-click `open-svg-editor.bat` to open the SVG pre-processor in your browser.
2. Upload the source SVG (keep the originals in `data/svg/raw/`).
3. Edit the layer parameters — drag to reorder, then set embroidery type / color ID / stitch
   length and the rest per layer.
4. Download the `_processed.svg` and save it into `data/svg/processed/`.
5. Import the processed SVG into Rhino; the GH pipeline (`gh/RhStream_v2.py`) reads the
   parameters back from each object's Name.

### Layer naming convention

Layer names carry the stitch parameters as underscore-separated fields, in this order:

```
sequence_ETS_colorID_patternType_stitchLen_patternWid_description
```

| Field | Meaning |
| --- | --- |
| `sequence` | Stitch order of the layer |
| `ETS` | Embroidery type (`ETS` / `SAT` / `OTHER`) |
| `colorID` | Thread color index |
| `patternType` | Stitch pattern index (zigzag / cross / decorative / arrow / feather) |
| `stitchLen` | Stitch length |
| `patternWid` | Pattern width |
| `description` | Free-text label |

**Caution:** these parameters are stored in the `id` attribute of each `<path>`, which is the only
thing carrying them downstream. Take the `_processed.svg` straight from the editor into Rhino — if
it is re-saved through Illustrator, Inkscape, or any other SVG tool on the way, those tools may
rewrite or drop the element IDs, and the stitch parameters are silently lost. Re-export from the
editor rather than repairing a round-tripped file.

## Project Structure

This project follows a standardized folder layout for Rhino + Grasshopper Python workflows:

- `cad/`  
  Rhino `.3dm` files or exported geometry used as base design assets or simulation references.

- `data/`  
  Input data and machine constraints, as well as digital-to-machine outputs like `.csv`, `.dst`, and `.json`.
  `data/svg/raw/` holds source SVGs, `data/svg/processed/` the `_processed.svg` files exported
  from the SVG pre-processor.

- `tools/`  
  Standalone helper tools, currently the browser-based SVG stitch editor
  (`svg-stitch-editor.html`), launched by `open-svg-editor.bat` in the repo root.

- `gh/`  
  GHPython scripts loaded by the Grasshopper definition (e.g. `RhStream_v2.py`).

- `doc/`  
  Documentation, sketches, technical drawings, and visual references (`.png`, `.pdf`, etc.).

- `result/`  
  Outputs generated from scripts or Grasshopper definitions, such as renderings and log files.

- `src/`  
  Source code: Grasshopper Python components (`src/script/`), the Grasshopper definition
  (`src/gh/`), and a native C++ path-sorting engine (`src/script/native/`) for large designs.

- `.github/`  
  GitHub-specific automation (e.g., Actions, issue templates).  
  **Note:** If the project involves proprietary data or IP, do **not** make this repository public.

- `requirements.txt`  
  Lists Python dependencies for external IDE environment setup.

## License

See [LICENSE](LICENSE) for this project's license. This project also vendors
[nanoflann](https://github.com/jlblancoc/nanoflann) (BSD 2-Clause) in
`src/script/native/`; see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for its full license text.
