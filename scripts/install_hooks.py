#!/usr/bin/env python3
"""
Git Hooks Installer

This script installs custom Git hooks for the TNT Topo repository.
It copies hooks from the scripts/hooks directory to the .git/hooks directory
and makes them executable.
"""

import os
import shutil
import stat
import sys


def install_pre_commit_hook():
    """Install pre-commit hook to check for passwords in QGIS files."""
    # Create pre-commit hook content
    pre_commit = """#!/bin/bash
#
# Pre-commit hook to ensure all QGIS files have passwords removed before committing
#

echo "Running pre-commit hook to check for passwords in QGIS files..."

# Find all staged QGIS project files
STAGED_QGIS_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.qgs$')

if [ -z "$STAGED_QGIS_FILES" ]; then
    echo -e "No QGIS files found in commit. Proceeding with commit.${NC}"
    exit 0
fi

echo -e "Found QGIS files in commit. Checking for passwords...${NC}"

# Flag to track if we found any passwords
FOUND_PASSWORDS=0

# Check each staged QGIS file
for FILE in $STAGED_QGIS_FILES; do
    if [ -f "$FILE" ]; then
        # Check if file contains passwords
        if grep -E -q "password='[^']+'" "$FILE"; then
            echo -e "ERROR: File $FILE contains passwords!${NC}"
            FOUND_PASSWORDS=1
        fi
    fi
done

# If we found passwords, clean the files and abort the commit
if [ $FOUND_PASSWORDS -eq 1 ]; then
    echo -e "Found passwords in QGIS files. Please clean them before committing.${NC}"
    echo -e "Running the password cleaning script...${NC}"
    
    # Run the cleaning script
    python3 scripts/clean_qgis_for_git.py -d . -v
    
    echo -e "Commit aborted. Please stage the cleaned files and commit again.${NC}"
    exit 1
fi

echo -e "No passwords found in QGIS files. Proceeding with commit.${NC}"
exit 0
"""

    # Get git root directory
    try:
        git_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    except Exception as e:
        print(f"Error finding git root: {str(e)}")
        return False

    # Create hooks directory if it doesn't exist
    hooks_dir = os.path.join(git_root, '.git', 'hooks')
    if not os.path.exists(hooks_dir):
        try:
            os.makedirs(hooks_dir)
        except Exception as e:
            print(f"Error creating hooks directory: {str(e)}")
            return False

    # Write the pre-commit hook
    pre_commit_path = os.path.join(hooks_dir, 'pre-commit')
    try:
        with open(pre_commit_path, 'w') as f:
            f.write(pre_commit)
        
        # Make it executable
        os.chmod(pre_commit_path, os.stat(pre_commit_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Installed pre-commit hook to {pre_commit_path}")
        return True
    except Exception as e:
        print(f"Error installing pre-commit hook: {str(e)}")
        return False


def main():
    """Main function to install all hooks."""
    print("Installing Git hooks...")
    
    if install_pre_commit_hook():
        print("Successfully installed pre-commit hook.")
    else:
        print("Failed to install one or more hooks.")
        return 1
    
    print("\nHooks installed successfully. They will run automatically on git operations.")
    print("To bypass hooks temporarily, use git commit with --no-verify")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())