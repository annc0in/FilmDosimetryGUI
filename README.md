# FilmDosimetryGUI

A comprehensive tool for film dosimetry analysis that supports both graphical user interface operation and direct script execution in Octave.  
The application performs calibration curve creation, film processing, and detailed dose distribution analysis.

---

## Repository Structure

This repository contains the application code and scripts but does not include experimental data folders containing calibration and experimental film TIF files, or XLSX files with delivered doses.  
These data folders must be provided separately.

### Core Files
- `main.py` – Main application entry point with user instructions
- `calibration_screen.py` – Calibration & Film Processing interface
- `processing_screen.py` – Real-time calibration processing display
- `analysis_screen.py` – Image Analysis & Dose Calculation interface
- `progress_screen.py` – Real-time analysis processing display
- `requirements.txt` – Python dependencies

### Octave Scripts
- `Check_calibration_XD_add_films.m` – Calibration & Film Processing script
- `functions/` – 5 supporting functions for processing
- `scripts/analyze_shots_films_MOD_centering_Charge_Density_bgnd.m` – Analysis script
- `scripts/functions/` – 6 supporting functions for analysis

### Build Resources
- `build.sh` – Linux build script
- `octave_wrapper.sh`- macOS wrapper script for Octave process isolation
- `resources.qrc` – Resources (icons, logos), compiled to `resources_rc.py`
- `_icons/` – Application icons (ico, png, icns)
- `_logos/` – CERN and CLEAR logos (svg, png)

Maintaining this structure is mandatory for correct operation of both the GUI application and direct Octave script execution.  
During application execution, additional folders and temporary files are created and cleaned up.

---

## Development Setup

### Prerequisites
- Python 3.8+ (tested with 3.11)  
- Any Python IDE/editor (development was done in VS Code)

---

### 1. Clone repository
```bash
git clone https://github.com/annc0in/FilmDosimetryGUI.git
cd FilmDosimetryGUI
```
If Git is not installed, you can download ZIP.

---

### 2. Create and activate virtual environment

```bash
python -m venv venv
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

**Windows PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

---

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **PyQt6, pyqt6_sip** — Main GUI libraries
- **PyQt5** — For compiling `resources.qrc` to `resources_rc.py`
- **PyInstaller** — For building executables

---

### 4. Compile resources
```bash
pyrcc5 resources.qrc -o resources_rc.py
```

**Important:** After compilation, manually edit `resources_rc.py` and change the import from **PyQt5** to **PyQt6** to avoid build conflicts.

---

## Architecture

### Screen Management
- `QStackedWidget` for screen navigation
- Modular screen classes with common interface patterns
- Dynamic theme adaptation for dark/light modes

### Data Flow
1. **UI Input** → JSON parameter files  
2. **Octave Processing** → File-based output monitoring  
3. **Result Display** → Dynamic table population and image loading  

### Octave Integration
The application uses `QProcess` to execute Octave scripts as subprocesses with carefully configured environments.

**Windows Environment**
- Automatically locates Octave installation in common directories
- Configures PATH to include Octave binaries and system utilities
- Sets `OCTAVE_GUI_MODE=1` for GUI communication
- Loads required packages

**Linux Environment**
- Uses system Octave (`/usr/bin/octave`)
- Sets `QT_QPA_PLATFORM=offscreen` for headless operation
- Configures UTF-8 locale environment
- Runtime directory management for sandboxed execution

**macOS Environment**
- Automatically sets execute permissions for wrapper script (`chmod 0o755`)
- Unsets `DYLD_LIBRARY_PATH`, `QT_PLUGIN_PATH`, and other Qt variables
- Clears Qt-related environment variables to prevent conflicts with PyQt6
- Configures gnuplot environment (`GNUTERM=qt`) for PDF report generation

### Communication Protocol
- **Input:** JSON parameter files (`user_inputs.json`, `get_user_inputs.json`)  
- **Output:**
  - Real-time stdout/stderr capture  
  - Structured data files for results tables  
  - Progress monitoring through file system events  

- **File Monitoring:** Timer-based polling for result files and image generation

### Key Integration Features
- **Process Control:** Start, pause (terminate), and cleanup operations  
- **Progress Tracking:** Real-time progress bars based on console output parsing  
- **Image Display:** Dynamic loading and scaling of generated calibration curves  
- **Error Handling:** Filtered stderr processing to suppress harmless warnings  
- **Resource Management:** Automatic cleanup of temporary files on completion  

---

## Building Executables

### Windows

**CMD:**
```cmd
cd path	o\project\directory
venv\Scripts\activate.bat
pyinstaller --onefile --windowed --icon=_icons/icon.ico --name "FilmDosimetryGUI" main.py && rmdir /s /q build && del FilmDosimetryGUI.spec && move dist\FilmDosimetryGUI.exe . && rmdir /s /q dist
```

**PowerShell:**
```powershell
cd path	o\project\directory
venv\Scripts\Activate.ps1
pyinstaller --onefile --windowed --icon="_icons/icon.ico" --name "FilmDosimetryGUI" main.py; Remove-Item -Recurse -Force build,FilmDosimetryGUI.spec -ErrorAction SilentlyContinue; Move-Item dist/FilmDosimetryGUI.exe .; Remove-Item -Recurse -Force dist
```

**Output:** `FilmDosimetryGUI.exe` in the project root directory

---

### Linux

1. Make the build script executable (first time only):
```bash
chmod +x build.sh
```

2. Run the build script:
```bash
cd /path/to/project/directory
./build.sh
```

**Output:** `FilmDosimetryGUI.AppImage` in the project root directory

### macOS

```bash
cd path/to/project/directory
source venv/bin/activate
pyinstaller --onedir --windowed --icon="_icons/icon.icns" --name "FilmDosimetryGUI" --add-data "octave_wrapper.sh:." main.py && rm -rf build FilmDosimetryGUI.spec && mv dist/FilmDosimetryGUI.app . && rm -rf dist
```

**Output:** `FilmDosimetryGUI.app` in the project root directory

---

## Distribution

After successful build:

1. Archive the executable file along with required resources  
2. Upload to cloud storage or distribution platform [CERNBox link](https://cernbox.cern.ch/s/0Q4aSmoEJ99K9rl)  
3. Users can download the appropriate archive for their operating system  
4. The application runs standalone without requiring Python installation
