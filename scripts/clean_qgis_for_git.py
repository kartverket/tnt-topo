#!/usr/bin/env python3
"""
QGIS Project Git-Safe Cleaner

This script removes sensitive information from QGIS project files (.qgs) before committing to Git.
It specifically removes database passwords and other credentials that might be stored in cleartext.
"""

import os
import sys
import glob
import lxml.etree as ET
import argparse
from typing import List, Optional


def find_qgis_files(directory: str) -> List[str]:
    """
    Find all QGIS project files in a directory and its subdirectories.
    
    Args:
        directory (str): Directory path to search in
        
    Returns:
        List[str]: List of absolute paths to QGIS project files
    """
    pattern = os.path.join(directory, "**", "*.qgs")
    return glob.glob(pattern, recursive=True)


def clean_passwords(qgis_file: str) -> bool:
    """
    Remove passwords from a QGIS project file.
    
    Args:
        qgis_file (str): Path to the QGIS project file
        
    Returns:
        bool: True if passwords were cleaned, False otherwise
    """
    try:
        tree = ET.parse(qgis_file)
        root = tree.getroot()
        
        datasources = root.findall('.//datasource')
        cleaned = False
        
        # Remove all passwords from the datasources
        for datasource in datasources:
            if datasource.text and 'password=' in datasource.text:
                # Extract current password
                password = datasource.text.split('password=')[1].split(' ')[0]
                # Replace with empty password
                datasource.text = datasource.text.replace(password, "''")
                cleaned = True
        
        if cleaned:
            # Save the modified QGIS project file
            tree.write(qgis_file, encoding='utf-8', xml_declaration=True)
            return True
        return False
    
    except Exception as e:
        print(f"Error cleaning {qgis_file}: {str(e)}")
        return False


def main() -> int:
    """
    Main function to parse arguments and clean QGIS project files.
    
    Returns:
        int: Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(description="Clean QGIS project files for Git")
    parser.add_argument("-d", "--directory", default="./data", 
                        help="Directory to search for QGIS project files (default: ./data)")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="Show verbose output")
    parser.add_argument("-f", "--file", 
                        help="Process a specific QGIS file instead of searching a directory")
    
    args = parser.parse_args()
    
    # Find QGIS project files
    qgis_files = []
    if args.file:
        if os.path.exists(args.file) and args.file.endswith('.qgs'):
            qgis_files = [args.file]
        else:
            print(f"Error: File {args.file} does not exist or is not a QGIS project file")
            return 1
    else:
        qgis_files = find_qgis_files(args.directory)
    
    if args.verbose:
        print(f"Found {len(qgis_files)} QGIS project files")
    
    # Clean each file
    cleaned_count = 0
    for qgis_file in qgis_files:
        if clean_passwords(qgis_file):
            cleaned_count += 1
            if args.verbose:
                print(f"Cleaned passwords from {qgis_file}")
    
    print(f"Cleaned {cleaned_count} of {len(qgis_files)} files")
    
    if cleaned_count > 0:
        print("IMPORTANT: Passwords have been removed from QGIS files.")
        print("Use the reInsertPasswords() function from qgis_handling.py to restore them when needed.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())