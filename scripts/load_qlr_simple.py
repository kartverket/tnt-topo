#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple QGIS script to load QLR files into current project

This is a simplified version for quick execution from QGIS Python console.
Loads all .qlr files from ./data/topo_layers into the current project.

Usage in QGIS Python Console:
exec(open('./scripts/load_qlr_simple.py').read())

Generated with VS Code, Chat Mode Agent, Model: Claude Sonnet 4
"""

import os
import re
from pathlib import Path
from qgis.core import QgsProject, QgsLayerDefinition, QgsMessageLog, Qgis

# Simple configuration - modify as needed
QLR_FOLDER = "./data/topo_layers"

def load_qlr_files():
    """Load all .qlr files from folder into current project"""
    
    project = QgsProject.instance()
    folder = Path(QLR_FOLDER)
    
    if not folder.exists():
        print(f"Error: Folder not found: {QLR_FOLDER}")
        return
    
    # Find .qlr files and sort by number
    qlr_files = list(folder.glob("*.qlr"))
    
    if not qlr_files:
        print(f"No .qlr files found in {QLR_FOLDER}")
        return
    
    # Sort by layer number (extract number from filename)
    def get_layer_number(filename):
        # Match pattern: lag{number}_{name}.qlr
        match = re.match(r'^lag(\d+)_', filename)
        if match:
            return int(match.group(1))
        # Fallback to old pattern: {number}_{name}.qlr
        match_old = re.match(r'^(\d+)_', filename)
        return int(match_old.group(1)) if match_old else 999999
    
    qlr_files.sort(key=lambda x: get_layer_number(x.name), reverse=True)
    
    print(f"Loading {len(qlr_files)} .qlr files from topo_layers...")
    print("Layer order (high→low numbers, Arctic territories load first):")
    
    # Load each file
    loaded_count = 0
    for i, qlr_file in enumerate(qlr_files, 1):
        try:
            layer_num = get_layer_number(qlr_file.name)
            layer_name = qlr_file.name.replace('.qlr', '').replace(f'lag{layer_num:02d}_', '')
            print(f"{i:2d}. lag{layer_num:02d}: {layer_name}")
            
            result = QgsLayerDefinition.loadLayerDefinition(
                str(qlr_file), 
                project, 
                project.layerTreeRoot()
            )
            
            if result:
                loaded_count += 1
            else:
                print(f"    ✗ Failed to load {qlr_file.name}")
                
        except Exception as e:
            print(f"    ✗ Error loading {qlr_file.name}: {e}")
    
    print(f"\n✓ Successfully loaded {loaded_count}/{len(qlr_files)} layer groups")
    print(f"Total layers in project: {len(project.mapLayers())}")

# Run the function
load_qlr_files()