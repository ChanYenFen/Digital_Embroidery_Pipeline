# EmbroideryFundamentalTest

Author: Fen

## Installation

```bash
pip install -r requirements.txt
```

## ▶️ Run

To generate a new project using this template:

1. **Open Command Prompt**

2. **Activate your Python environment** (if applicable):
   ```bash
   path\to\your\env\Scripts\activate
   ```

3. **Navigate to the folder where you want to create the new project:**
   ```bash
   cd path\to\your\desired\project\location
   ```

4. **Run Cookiecutter with the local template:**
   ```bash
   cookiecutter path\to\cookiecutter-rhino-gh-python
   ```

5. **Follow the prompts** to customize your project (e.g., project name, author).


## 📁 Project Structure

This project follows a standardized folder layout for Rhino + Grasshopper Python workflows:

- `cad/`  
  Rhino `.3dm` files or exported geometry used as base design assets or simulation references.

- `data/`  
  Input data such as `.csv`, `.json`, `.txt`, or visual references (`.png`, `.pdf`, etc.). These are treated as part of the digital design pipeline's inputs.

- `doc/`  
  Documentation, sketches, technical drawings, or diagrams relevant to the design or logic.

- `result/`  
  Outputs generated from scripts or Grasshopper definitions, such as renderings and log files.

- `src/`  
  Source code including GH Python modules, reusable logic, and external language components (e.g., C#, C++, Python).

- `.github/`  
  GitHub-specific automation (e.g., Actions, issue templates).  
  ⚠️ **Note:** If the project involves proprietary data or IP, do **not** make this repository public.

- `requirements.txt`  
  Lists Python dependencies. Install them using:
  ```bash
  pip install -r requirements.txt
