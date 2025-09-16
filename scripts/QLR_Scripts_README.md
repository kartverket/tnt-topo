# QGIS Layer Definition (.qlr) Scripts Documentation

This directory contains Python scripts for working with QGIS Layer Definition files (.qlr) to create and manage QGIS projects.

Disclaimer: Generated with VS Code, Chat Mode Agent, Model: Claude Sonnet 4

## Scripts Overview

### 1. `create_project_from_qlr.py` - Full Project Creator
**Purpose**: Creates a complete new QGIS project from .qlr files in a specified folder.

**Features**:
- Reads all .qlr files from `./data/topo_layers/`
- Sorts layers by number in filename (e.g., `001_layer.qlr`, `002_layer.qlr`)
- Creates new project file at `./data/topo_from_qlr.qgs`
- Sets Norwegian coordinate system (EPSG:5973)
- Comprehensive logging and error handling
- Configurable paths and settings

### 2. `load_qlr_simple.py` - Quick Loader
**Purpose**: Simple script to load .qlr files into the currently open project.

**Features**:
- Loads .qlr files into current project (doesn't create new project)
- Basic sorting by layer number
- Minimal configuration
- Quick execution

## Usage Instructions

### Method 1: Running from QGIS Python Console

1. **Open QGIS**
2. **Open Python Console**: `Plugins > Python Console`
3. **Navigate to project directory** (if needed):
   ```python
   import os
   os.chdir('/path/to/tnt-topo')
   ```
4. **Run the script**:
   ```python
   # For full project creation
   exec(open('./scripts/create_project_from_qlr.py').read())
   
   # Or for simple loading into current project
   exec(open('./scripts/load_qlr_simple.py').read())
   ```

### Method 2: Customizing Settings

You can customize the scripts before running:

```python
# Load the script without running
exec(open('./scripts/create_project_from_qlr.py').read())

# Customize settings
update_qlr_folder('./my_custom_layers')
update_output_project('./my_project.qgs')
update_crs('EPSG:4326')

# Then run
create_project_from_qlr()
```

### Method 3: Using Utility Functions

```python
# Load script
exec(open('./scripts/create_project_from_qlr.py').read())

# Preview layer structure to see what will be loaded
preview_layer_structure()

# List .qlr files to see loading order
list_qlr_files()

# Create project
create_project_from_qlr()
```

## File Naming Convention

The scripts expect .qlr files to be named with a numeric prefix for proper ordering:

```
lag01_hav.qlr
lag02_hoydelag.qlr
lag03_vannflate.qlr
lag04_dybdelag.qlr
...
lag44_Jan_Mayen.qlr
```

**Current TNT Topo Layer Structure** (44 layers total - **Load Order: High→Low Numbers**):
- **Arctic Territories (lag43-lag44)**: Load first → Bottom of layer tree → Svalbard, Jan_Mayen
- **Text/Names (lag28-lag42)**: Load second → Multiple scale place name layers (n5000, n2000, n1000, n500, n250, n100, n50, n5), vegnummer, adresse, gatenavn
- **Infrastructure (lag11-lag27)**: Load third → adm_grense, vannkontur, fkb_f_bygnanlegg, fkb_f_samferdsel, various samferdsel layers, bygning layers, heliport, flyplass, kraftlinje_taubane, hoydepunkt, adm_grensepunkt  
- **Base Layers (lag01-lag10)**: Load last → **Top of layer tree** → hav, hoydelag, vannflate, dybdelag, arealdekke, hoydekurve_og_n50bre, relieff, naturvern, maritim_grense, skytefelt_statsallmenning

**Naming Rules**:
- Format: `lag{number}_{description}.qlr` (e.g., `lag01_hav.qlr`)
- **Loading order**: High numbers first (lag44→lag43→...→lag02→lag01)
- **Layer tree result**: Base layers on top, Arctic territories on bottom
- Leading zeros are used for proper sorting (lag01, lag02, etc.)
- Files without proper numbers are loaded last

## Configuration Options

### Default Settings (create_project_from_qlr.py)

```python
QLR_FOLDER = "./data/topo_layers"          # Source folder for .qlr files
OUTPUT_PROJECT = "./data/topo_from_qlr.qgs" # Output project file
DEFAULT_CRS = "EPSG:25833"                   # Norwegian UTM Zone 33
```

### Coordinate Reference Systems

Common Norwegian CRS options:
- `EPSG:5973` - ETRS89 / UTM zone 33N 
- `EPSG:4258` - ETRS89 geographic
- `EPSG:25833` - ETRS89 / UTM zone 33N (default)
- `EPSG:4326` - WGS84 geographic (international)

## Troubleshooting

### Common Issues

1. **"Folder not found" error**
   - Check that `./data/topo_layers/` exists
   - Use absolute paths if relative paths don't work
   - Update folder path: `update_qlr_folder('/full/path/to/folder')`

2. **"No .qlr files found"**
   - Verify .qlr files exist in the folder
   - Check file extensions (must be `.qlr`)
   - Use `list_qlr_files()` to debug

3. **Layers fail to load**
   - Check that data sources in .qlr files are accessible
   - Verify network connections for web services
   - Check database credentials and connections

4. **Project won't save**
   - Ensure output directory exists and is writable
   - Check disk space
   - Verify file permissions

### Debug Mode

Enable detailed logging in QGIS:
1. Go to `Settings > Options > General > Logging`
2. Enable logging for "QLR to Project"
3. Check `View > Panels > Log Messages`

## Example Workflow

### Creating a New Topographic Project

1. **Prepare .qlr files** (TNT Topo structure):
   ```
   ./data/topo_layers/
   ├── lag01_hav.qlr
   ├── lag02_hoydelag.qlr
   ├── lag03_vannflate.qlr
   ├── ...
   ├── lag43_Svalbard.qlr
   └── lag44_Jan_Mayen.qlr
   ```

2. **Preview the structure** in QGIS Python Console:
   ```python
   exec(open('./scripts/create_project_from_qlr.py').read())
   preview_layer_structure()
   ```

3. **Create the project**:
   ```python
   create_project_from_qlr()
   ```

4. **Open created project**:
   - File created at `/home/miecar/repos/tnt-topo/data/topo_from_qlr.qgs`
   - 44 layer groups loaded in **reverse order** (lag44→lag01)
   - **Layer tree structure**: Base layers (hav, hoydelag) on top, Arctic territories (Svalbard, Jan_Mayen) on bottom
   - Norwegian coordinate system (EPSG:25833) applied

### Quick Layer Addition

To add .qlr layers to an existing project:

```python
# Load into current project
exec(open('./scripts/load_qlr_simple.py').read())
```

## Advanced Usage

### Batch Processing Multiple Folders

```python
# Load script
exec(open('./scripts/create_project_from_qlr.py').read())

folders = ['./layers/base', './layers/thematic', './layers/labels']

for folder in folders:
    update_qlr_folder(folder)
    update_output_project(f'./projects/{Path(folder).name}_project.qgs')
    create_project_from_qlr()
```

### Custom Layer Processing

```python
from pathlib import Path
from qgis.core import QgsLayerDefinition, QgsProject

def load_specific_layers(pattern):
    """Load only .qlr files matching a pattern"""
    project = QgsProject.instance()
    folder = Path('./data/topo_layers')
    
    for qlr_file in folder.glob(f"*{pattern}*.qlr"):
        QgsLayerDefinition.loadLayerDefinition(
            str(qlr_file), project, project.layerTreeRoot()
        )
        print(f"Loaded: {qlr_file.name}")

# Example: Load only water-related layers
load_specific_layers('water')
```

## Integration with TNT Topo Workflow

These scripts integrate with the TNT Topo project workflow:

1. **Export layers as .qlr** from main project files
2. **Organize .qlr files** by theme/scale in folders
3. **Use scripts** to create specialized project variants
4. **Version control** .qlr files for reproducible projects
5. **Automate** project creation for different use cases

## See Also

- [QGIS Layer Definition Documentation](https://docs.qgis.org/3.28/en/docs/user_manual/appendices/qgis_file_formats.html#qlr-qgis-layer-definition-file)
- [PyQGIS Cookbook](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/)
- [TNT Topo Main Documentation](../docs/Topo_2025.md)