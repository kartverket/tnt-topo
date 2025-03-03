#!/usr/bin/env python3
"""
Data Downloader for TNT Topo QGIS Projects

This script downloads specific Natural Earth datasets and converts them to FlatGeobuf format:
1. Countries (ne_10m_admin_0_countries)
2. Lakes (ne_10m_lakes)
3. Boundaries (ne_10m_admin_0_boundary_lines_land)

The FlatGeobuf format provides efficient random access to features in the data.
"""

import os
import sys
import argparse
import logging
import requests
import zipfile
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from tqdm import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# Define datasets to download
DATASETS = {
    "countries": {
        "url": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip",
        "description": "Natural Earth 1:10m Countries",
        "shapefile": "ne_10m_admin_0_countries.shp"
    },
    "lakes": {
        "url": "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_lakes.zip",
        "description": "Natural Earth 1:10m Lakes",
        "shapefile": "ne_10m_lakes.shp"
    },
    "boundaries": {
        "url": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_boundary_lines_land.zip",
        "description": "Natural Earth 1:10m Admin 0 Boundary Lines Land",
        "shapefile": "ne_10m_admin_0_boundary_lines_land.shp"
    }
}


def download_file(url: str, target_path: str) -> bool:
    """
    Download a file from a URL to a target path.
    
    Args:
        url (str): URL to download from
        target_path (str): Path to save the downloaded file
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Stream the download with progress bar
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(target_path, 'wb') as f, tqdm(
            desc=f"Downloading {os.path.basename(target_path)}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        logger.info(f"Downloaded {url} to {target_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return False


def extract_zip(zip_path: str, extract_dir: str) -> bool:
    """
    Extract a ZIP file to a directory.
    
    Args:
        zip_path (str): Path to the ZIP file
        extract_dir (str): Directory to extract to
        
    Returns:
        bool: True if extraction was successful, False otherwise
    """
    try:
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get total size for progress bar
            total_size = sum(file.file_size for file in zip_ref.infolist())
            extracted_size = 0
            
            # Create progress bar
            with tqdm(
                desc=f"Extracting {os.path.basename(zip_path)}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as progress_bar:
                for file in zip_ref.infolist():
                    zip_ref.extract(file, extract_dir)
                    extracted_size += file.file_size
                    progress_bar.update(file.file_size)
        
        logger.info(f"Extracted {zip_path} to {extract_dir}")
        return True
    
    except Exception as e:
        logger.error(f"Error extracting {zip_path}: {str(e)}")
        return False


def check_ogr2ogr_available() -> bool:
    """
    Check if ogr2ogr is available in the system.
    
    Returns:
        bool: True if ogr2ogr is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ogr2ogr", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"Found ogr2ogr: {result.stdout.strip()}")
            return True
        else:
            logger.error("ogr2ogr command returned non-zero exit code")
            return False
    except Exception as e:
        logger.error(f"ogr2ogr not found: {str(e)}")
        return False


def convert_to_flatgeobuf(shapefile_path: str, fgb_path: str) -> bool:
    """
    Convert a Shapefile to FlatGeobuf format using ogr2ogr.
    
    Args:
        shapefile_path (str): Path to the Shapefile
        fgb_path (str): Path to save the FlatGeobuf file
        
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        logger.info(f"Converting {os.path.basename(shapefile_path)} to FlatGeobuf")
        
        # Create directory for output file if it doesn't exist
        os.makedirs(os.path.dirname(fgb_path), exist_ok=True)
        
        # Run ogr2ogr to convert from Shapefile to FlatGeobuf
        result = subprocess.run(
            [
                "ogr2ogr", 
                "-f", "FlatGeobuf",
                "-nlt", "PROMOTE_TO_MULTI", 
                fgb_path, 
                shapefile_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Converted {shapefile_path} to {fgb_path}")
            return True
        else:
            logger.error(f"Error converting {shapefile_path} to FlatGeobuf: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Error converting {shapefile_path} to FlatGeobuf: {str(e)}")
        return False


def process_dataset(
    dataset_name: str, 
    dataset_config: Dict, 
    data_dir: str,
    temp_dir: str,
    force: bool = False
) -> bool:
    """
    Process a dataset: download, extract, and convert to FlatGeobuf.
    
    Args:
        dataset_name (str): Name of the dataset
        dataset_config (Dict): Configuration for the dataset
        data_dir (str): Directory to save the final FlatGeobuf files
        temp_dir (str): Temporary directory for downloads and extraction
        force (bool): Force processing even if the output file exists
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Processing dataset: {dataset_name} - {dataset_config['description']}")
    
    # Define paths
    zip_path = os.path.join(temp_dir, f"{dataset_name}.zip")
    extract_path = os.path.join(temp_dir, dataset_name)
    shapefile_path = os.path.join(extract_path, dataset_config["shapefile"])
    fgb_path = os.path.join(data_dir, f"{dataset_name}.fgb")
    
    # Check if output file already exists
    if os.path.exists(fgb_path) and not force:
        logger.info(f"FlatGeobuf file {fgb_path} already exists, skipping (use --force to override)")
        return True
    
    # Download, extract, and convert
    if download_file(dataset_config["url"], zip_path):
        if extract_zip(zip_path, extract_path):
            if convert_to_flatgeobuf(shapefile_path, fgb_path):
                return True
    
    return False


def main() -> int:
    """
    Main function to parse arguments and process datasets.
    
    Returns:
        int: Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        description="Download Natural Earth datasets and convert to FlatGeobuf format"
    )
    parser.add_argument(
        "-d", "--data-dir", 
        default="./data/natural_earth",
        help="Directory to store the converted FlatGeobuf files (default: ./data/natural_earth)"
    )
    parser.add_argument(
        "-s", "--datasets", 
        nargs='+',
        choices=list(DATASETS.keys()) + ["all"],
        default=["all"],
        help="Specific datasets to process (default: all)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force processing even if output files exist"
    )
    parser.add_argument(
        "--keep-temp", 
        action="store_true",
        help="Keep temporary files after processing"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if ogr2ogr is available
    if not check_ogr2ogr_available():
        logger.error("ogr2ogr is required for conversion to FlatGeobuf format.")
        logger.error("Please install GDAL/OGR tools before running this script.")
        return 1
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="tnt-topo-")
    logger.debug(f"Created temporary directory: {temp_dir}")
    
    try:
        # Create output directory
        os.makedirs(args.data_dir, exist_ok=True)
        
        # Determine datasets to process
        if "all" in args.datasets:
            selected_datasets = DATASETS
        else:
            selected_datasets = {name: DATASETS[name] for name in args.datasets}
        
        # Process each dataset
        success_count = 0
        total_datasets = len(selected_datasets)
        
        for dataset_name, dataset_config in selected_datasets.items():
            if process_dataset(dataset_name, dataset_config, args.data_dir, temp_dir, args.force):
                success_count += 1
        
        # Report results
        logger.info(f"Successfully processed {success_count} of {total_datasets} datasets")
        logger.info(f"FlatGeobuf files are available in {os.path.abspath(args.data_dir)}")
        
        # Return success if all datasets were processed
        return 0 if success_count == total_datasets else 1
    
    finally:
        # Clean up temporary directory
        if not args.keep_temp:
            logger.debug(f"Removing temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            logger.info(f"Temporary files kept at: {temp_dir}")


if __name__ == "__main__":
    sys.exit(main())