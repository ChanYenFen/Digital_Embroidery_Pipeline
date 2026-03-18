# Digital_Embroidery_Pipeline

Author: Yen-Fen Chan

## Installation

If you are developing or reviewing the code in an external IDE (like VSCode), install the dependencies via pip:

```
pip install -r requirements.txt
```

## Run (Rhino Grasshopper Environment)

For Rhino 8 Grasshopper Users (Native CPython 3)
You do not need to use the command line to install dependencies. The Grasshopper Python components in this project use Rhino 8's native package manager. 

Simply open the Grasshopper definition and run the script in the top left canvas "Check & Install Modules"; Rhino will automatically read the `# r: package_name` headers and install the required modules internally.


## Project Structure

This project follows a standardized folder layout for Rhino + Grasshopper Python workflows:

- `cad/`  
  Rhino `.3dm` files or exported geometry used as base design assets or simulation references.

- `data/`  
  Input data and machine constraints, as well as digital-to-machine outputs like `.csv`, `.dst`, and `.json`.

- `doc/`  
  Documentation, sketches, technical drawings, and visual references (`.png`, `.pdf`, etc.).

- `result/`  
  Outputs generated from scripts or Grasshopper definitions, such as renderings and log files.

- `src/`  
  Source code including GH Python scripts (.py), reusable logic, and external language components.

- `.github/`  
  GitHub-specific automation (e.g., Actions, issue templates).  
  **Note:** If the project involves proprietary data or IP, do **not** make this repository public.

- `requirements.txt`  
  Lists Python dependencies for external IDE environment setup.
