#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QGIS Python script to create a project from Layer Definition (.qlr) files

This script reads all .qlr files from a specified folder and creates a new QGIS project
with all layers loaded in the correct order based on filename sorting.

Usage:
- Run this script from within QGIS Python console
- Modify the QLR_FOLDER and OUTPUT_PROJECT paths as needed
- The script expects .qlr files named in format: lag{number}_{name}.qlr (e.g., lag01_hav.qlr)

Author: TNT Topo Team
Generated with VS Code, Chat Mode Agent, Model: Claude Sonnet 4
Date: September 2025
"""

import os
import re
from pathlib import Path
from qgis.core import (
    QgsProject, 
    QgsLayerDefinition, 
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    Qgis
)

# Configuration
QLR_FOLDER = "./data/topo_layers"
OUTPUT_PROJECT = "./data/topo_from_qlr.qgs"
DEFAULT_CRS = "EPSG:25833"  # Norwegian coordinate system (UTM zone 33)

def log_message(message, level=Qgis.Info):
    """Log message to QGIS message log"""
    QgsMessageLog.logMessage(message, "QLR to Project", level)
    print(f"[QLR to Project] {message}")

def get_layer_number(filename):
    """
    Extract layer number from filename for sorting
    Expected format: lag{number}_{name}.qlr (e.g., lag01_hav.qlr, lag02_hoydelag.qlr)
    
    Args:
        filename (str): The .qlr filename
        
    Returns:
        int: Layer number for sorting, or 999999 if no number found
    """
    # Match pattern: lag{number}_{name}.qlr
    match = re.match(r'^lag(\d+)_', filename)
    if match:
        return int(match.group(1))
    else:
        # Also try old pattern for backward compatibility: {number}_{name}.qlr
        match_old = re.match(r'^(\d+)_', filename)
        if match_old:
            return int(match_old.group(1))
        else:
            # If no number found, put at end
            log_message(f"Warning: No layer number found in filename: {filename}", Qgis.Warning)
            return 999999

def find_qlr_files(folder_path):
    """
    Find all .qlr files in the specified folder and sort them by layer number
    
    Args:
        folder_path (str): Path to folder containing .qlr files
        
    Returns:
        list: Sorted list of .qlr file paths
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        log_message(f"Error: Folder does not exist: {folder_path}", Qgis.Critical)
        return []
    
    if not folder.is_dir():
        log_message(f"Error: Path is not a directory: {folder_path}", Qgis.Critical)
        return []
    
    # Find all .qlr files
    qlr_files = list(folder.glob("*.qlr"))
    
    if not qlr_files:
        log_message(f"Warning: No .qlr files found in folder: {folder_path}", Qgis.Warning)
        return []
    
    # Sort by layer number extracted from filename (reverse order - higher numbers first)
    qlr_files.sort(key=lambda x: get_layer_number(x.name), reverse=True)
    
    log_message(f"Found {len(qlr_files)} .qlr files in {folder_path}")
    
    return qlr_files

def create_project_from_qlr():
    """
    Main function to create QGIS project from .qlr files
    """
    log_message("=== Starting QLR to Project Creation ===")
    
    # Get current project instance
    project = QgsProject.instance()
    
    # Clear existing project
    project.clear()
    log_message("Cleared existing project")
    
    # Set project CRS
    crs = QgsCoordinateReferenceSystem(DEFAULT_CRS)
    if crs.isValid():
        project.setCrs(crs)
        log_message(f"Set project CRS to: {DEFAULT_CRS}")
    else:
        log_message(f"Warning: Invalid CRS: {DEFAULT_CRS}, using default", Qgis.Warning)
    
    # Find and sort .qlr files
    qlr_files = find_qlr_files(QLR_FOLDER)
    
    if not qlr_files:
        log_message("No .qlr files found. Aborting.", Qgis.Critical)
        return False
    
    # Load each .qlr file
    loaded_count = 0
    failed_count = 0
    
    for qlr_file in qlr_files:
        try:
            log_message(f"Loading: {qlr_file.name}")
            
            # Load layer definition
            result = QgsLayerDefinition.loadLayerDefinition(
                str(qlr_file), 
                project, 
                project.layerTreeRoot()
            )
            
            if result:
                loaded_count += 1
                log_message(f"✓ Successfully loaded: {qlr_file.name}")
            else:
                failed_count += 1
                log_message(f"✗ Failed to load: {qlr_file.name}", Qgis.Warning)
                
        except Exception as e:
            failed_count += 1
            log_message(f"✗ Exception loading {qlr_file.name}: {str(e)}", Qgis.Critical)
    
    # Summary
    log_message(f"=== Loading Summary ===")
    log_message(f"Successfully loaded: {loaded_count} layers")
    log_message(f"Failed to load: {failed_count} layers")
    log_message(f"Total layers in project: {len(project.mapLayers())}")
    
    # Save project if layers were loaded
    if loaded_count > 0:
        try:
            # Ensure output directory exists
            output_path = Path(OUTPUT_PROJECT)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save project
            result = project.write(OUTPUT_PROJECT)
            
            if result:
                log_message(f"✓ Project saved successfully: {OUTPUT_PROJECT}")
                log_message(f"=== Project Creation Complete ===")
                return True
            else:
                log_message(f"✗ Failed to save project: {OUTPUT_PROJECT}", Qgis.Critical)
                return False
                
        except Exception as e:
            log_message(f"✗ Exception saving project: {str(e)}", Qgis.Critical)
            return False
    else:
        log_message("No layers loaded, project not saved.", Qgis.Warning)
        return False

def list_qlr_files():
    """
    Utility function to list .qlr files in the folder with their order
    """
    log_message("=== Listing .qlr files ===")
    
    qlr_files = find_qlr_files(QLR_FOLDER)
    
    if not qlr_files:
        log_message("No .qlr files found.")
        return
    
    log_message(f"Found {len(qlr_files)} .qlr files in order:")
    for i, qlr_file in enumerate(qlr_files, 1):
        layer_num = get_layer_number(qlr_file.name)
        log_message(f"{i:3d}. lag{layer_num:02d} - {qlr_file.name}")

def preview_layer_structure():
    """
    Preview the layer structure without loading anything
    Shows the layer stacking order (top to bottom in QGIS layer tree)
    """
    log_message("=== Layer Structure Preview (Load Order: High→Low Numbers) ===")
    
    qlr_files = find_qlr_files(QLR_FOLDER)
    
    if not qlr_files:
        log_message("No .qlr files found.")
        return
    
    # Group layers by categories for better overview (shown in load order)
    categories = {
        'Arctic Territories (43-44) - Load First (Bottom of Tree)': [],
        'Text/Names (28-42) - Load Second': [],
        'Infrastructure (11-27) - Load Third': [],
        'Base Layers (1-10) - Load Last (Top of Tree)': []
    }
    
    for qlr_file in qlr_files:
        layer_num = get_layer_number(qlr_file.name)
        layer_name = qlr_file.name.replace('.qlr', '').replace(f'lag{layer_num:02d}_', '')
        
        if 43 <= layer_num <= 44:
            categories['Arctic Territories (43-44) - Load First (Bottom of Tree)'].append(f"lag{layer_num:02d}: {layer_name}")
        elif 28 <= layer_num <= 42:
            categories['Text/Names (28-42) - Load Second'].append(f"lag{layer_num:02d}: {layer_name}")
        elif 11 <= layer_num <= 27:
            categories['Infrastructure (11-27) - Load Third'].append(f"lag{layer_num:02d}: {layer_name}")
        elif 1 <= layer_num <= 10:
            categories['Base Layers (1-10) - Load Last (Top of Tree)'].append(f"lag{layer_num:02d}: {layer_name}")
    
    for category, layers in categories.items():
        if layers:
            log_message(f"\n{category}:")
            for layer in layers:
                log_message(f"  {layer}")
    
    log_message(f"\nTotal layers: {len(qlr_files)}")
    log_message("Load order: lag44→lag43→lag42→...→lag02→lag01")
    log_message("Layer tree: Arctic/Text (bottom) ← Infrastructure ← Base layers (top)")
    log_message("Use create_project_from_qlr() to load all layers into a new project.")

# Main execution
if __name__ == "__main__":
    # This section runs when script is executed
    
    print("\n" + "="*60)
    print("QGIS Project Creator from Layer Definition Files (.qlr)")
    print("="*60)
    print(f"QLR Folder: {QLR_FOLDER}")
    print(f"Output Project: {OUTPUT_PROJECT}")
    print(f"Default CRS: {DEFAULT_CRS}")
    print("="*60)
    
    # Uncomment the next line to just list files without creating project
    # list_qlr_files()
    
    # Uncomment the next line to preview layer structure
    # preview_layer_structure()
    
    # Create the project
    success = create_project_from_qlr()
    
    if success:
        print("\n✓ Project creation completed successfully!")
        print(f"Open the project file: {OUTPUT_PROJECT}")
    else:
        print("\n✗ Project creation failed. Check the message log for details.")

    print("="*60)

# Additional utility functions that can be called manually

def update_qlr_folder(new_folder):
    """Update the QLR folder path"""
    global QLR_FOLDER
    QLR_FOLDER = new_folder
    log_message(f"Updated QLR folder to: {new_folder}")

def update_output_project(new_path):
    """Update the output project path"""
    global OUTPUT_PROJECT
    OUTPUT_PROJECT = new_path
    log_message(f"Updated output project to: {new_path}")

def update_crs(new_crs):
    """Update the default CRS"""
    global DEFAULT_CRS
    DEFAULT_CRS = new_crs
    log_message(f"Updated default CRS to: {new_crs}")

# Example usage in QGIS Python Console:
"""
# Load and run the script
# Use a relative path or set the path variable as needed for your environment:
# Example with relative path:
exec(open('./scripts/create_project_from_qlr.py').read())
# Or set the path dynamically:
# script_path = os.path.join(os.getcwd(), 'scripts', 'create_project_from_qlr.py')
# exec(open(script_path).read())

# Or customize settings before running:
update_qlr_folder('/path/to/my_custom_layers')
update_output_project('/path/to/my_custom_project.qgs')
create_project_from_qlr()

# Preview the layer structure:
preview_layer_structure()

# Or just list files:
list_qlr_files()

# Example file naming pattern in /data/topo_layers/:
# lag01_hav.qlr
# lag02_hoydelag.qlr
# lag03_vannflate.qlr
# ...
# lag44_Jan_Mayen.qlr
"""
