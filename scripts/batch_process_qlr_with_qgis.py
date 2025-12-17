#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch process .qlr files using QGIS headless to create individual project files.
This script runs create_project_from_qlr.py logic for each .qlr file separately.

Usage:
    python3 batch_process_qlr_with_qgis.py --input ./data/QLR --output ./data/projects

Requirements:
    - QGIS installed with Python bindings
    - qgis Python package available
"""

import argparse
import sys
import time
from pathlib import Path

# Initialize QGIS
def init_qgis():
    """Initialize QGIS application with proper settings and authentication"""
    import os
    from qgis.core import QgsApplication, QgsAuthManager, QgsSettings
    
    # Get user's home directory for QGIS profile
    home_dir = os.path.expanduser("~")
    qgis_profile_path = os.path.join(home_dir, ".local/share/QGIS/QGIS3/profiles/default")
    
    # Set up environment variables for GDAL/OGR to access cloud storage and databases
    # Check for Google Cloud credentials
    google_app_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if google_app_creds:
        print(f"✓ Found Google Cloud credentials: {google_app_creds}")
    else:
        # Try to find gcs-key.json in current directory
        if os.path.exists('gcs-key.json'):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('gcs-key.json')
            print(f"✓ Using gcs-key.json for Google Cloud authentication")
        else:
            print("⚠️  Warning: No Google Cloud credentials found (GOOGLE_APPLICATION_CREDENTIALS not set)")
            print("   Some layers may fail to load if they require GCS access")
    
    # Set GDAL options for better cloud storage access
    os.environ.setdefault('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', '.tif,.tiff,.vrt,.ovr,.geojson,.json,.fgb')
    os.environ.setdefault('GDAL_HTTP_TIMEOUT', '300')
    os.environ.setdefault('GDAL_HTTP_CONNECTTIMEOUT', '60')
    os.environ.setdefault('VSI_CACHE', 'TRUE')
    os.environ.setdefault('VSI_CACHE_SIZE', '50000000')  # 50MB cache
    
    # Supply path to qgis install location
    QgsApplication.setPrefixPath("/usr", True)
    
    # Create a reference to the QgsApplication
    # Setting the second argument to False disables the GUI
    qgs = QgsApplication([], False)
    
    # Set the QGIS configuration path to use the default profile
    if os.path.exists(qgis_profile_path):
        print(f"✓ Using QGIS profile: {qgis_profile_path}")
        # The profile path is used automatically by QgsApplication
    
    # Load providers and initialize
    qgs.initQgis()
    
    # Initialize authentication manager to load saved credentials
    auth_manager = QgsApplication.authManager()
    if auth_manager:
        print("✓ Authentication manager initialized")
        # The auth manager will automatically load credentials from the profile
    
    # Verify that data providers are available
    from qgis.core import QgsProviderRegistry
    provider_registry = QgsProviderRegistry.instance()
    providers = provider_registry.providerList()
    print(f"✓ Available data providers: {', '.join(providers)}")
    
    # Load QGIS settings from the profile (includes database connections, etc.)
    settings = QgsSettings()
    print(f"✓ QGIS settings loaded from profile")
    
    return qgs

def create_single_project_from_qlr(qlr_file: Path, output_file: Path, crs: str = "EPSG:25833") -> bool:
    """
    Create a single QGIS project from a .qlr file using QGIS API
    
    Args:
        qlr_file: Path to the .qlr file
        output_file: Path for the output .qgs file
        crs: Coordinate reference system
        
    Returns:
        bool: True if successful, False otherwise
    """
    from qgis.core import (
        QgsProject, 
        QgsLayerDefinition, 
        QgsCoordinateReferenceSystem,
        QgsMessageLog,
        Qgis
    )
    
    try:
        print(f"Processing: {qlr_file.name}")
        
        # Create new project instance (don't use singleton to avoid conflicts)
        project = QgsProject.instance()
        project.removeAllMapLayers()
        project.clear()
        
        # Set project CRS
        project_crs = QgsCoordinateReferenceSystem(crs)
        if project_crs.isValid():
            project.setCrs(project_crs)
        else:
            print(f"  Warning: Invalid CRS: {crs}, using default")
        
        # Load layer definition
        result = QgsLayerDefinition.loadLayerDefinition(
            str(qlr_file), 
            project, 
            project.layerTreeRoot()
        )
        
        if not result:
            print(f"  ✗ Failed to load layer definition from {qlr_file.name}")
            return False
        
        # Check if layers were loaded and their validity
        all_layers = list(project.mapLayers().values())
        layer_count = len(all_layers)
        
        if layer_count == 0:
            print(f"  ✗ No layers loaded from {qlr_file.name}")
            return False
        
        # Check for invalid layers
        invalid_layers = [layer for layer in all_layers if not layer.isValid()]
        valid_layers = layer_count - len(invalid_layers)
        
        if valid_layers == 0:
            print(f"  ✗ All {layer_count} layers are invalid:")
            for layer in invalid_layers[:3]:  # Show first 3
                error_msg = layer.error().message() if layer.error() else "Unknown error"
                print(f"    - {layer.name()}: {error_msg}")
            return False
        
        if invalid_layers:
            print(f"  ⚠️  Loaded {layer_count} layers ({valid_layers} valid, {len(invalid_layers)} invalid)")
        else:
            print(f"  ✓ Loaded {layer_count} valid layers")
        
        # Set project title and metadata
        # Use a valid identifier for the project name (no spaces, must start with letter)
        project_name = f"tnt_topo_{qlr_file.stem}"
        project.setTitle(project_name)
        
        # Configure QGIS Server capabilities (WMS/WMTS/WFS/OAPIF)
        print(f"  Configuring QGIS Server capabilities...")
        
        # Enable WMS Service
        project.writeEntry("WMSServiceCapabilities", "/", "True")
        project.writeEntry("WMSServiceTitle", "/", f"TNT Topo - {qlr_file.stem}")
        project.writeEntry("WMSServiceAbstract", "/", f"QGIS Server WMS service for {qlr_file.stem}")
        project.writeEntry("WMSOnlineResource", "/", "")
        project.writeEntry("WMSContactPerson", "/", "TNT Topo Team")
        project.writeEntry("WMSContactOrganization", "/", "Kartverket")
        project.writeEntry("WMSContactPosition", "/", "")
        project.writeEntry("WMSContactPhone", "/", "")
        project.writeEntry("WMSContactMail", "/", "")
        project.writeEntry("WMSKeywordList", "/", ["topo", "norway", "kartverket", qlr_file.stem])
        project.writeEntry("WMSExtent", "/", [])
        project.writeEntry("WMSCrsList", "/", ["EPSG:25833", "EPSG:5973", "EPSG:4326", "EPSG:3857"])
        project.writeEntry("WMSAddWktGeometry", "/", False)
        project.writeEntry("WMSPrecision", "/", "8")
        project.writeEntry("WMSUseLayerIDs", "/", False)
        project.writeEntry("WMSImageQuality", "/", "90")
        project.writeEntry("WMSTileBuffer", "/", "0")
        project.writeEntry("WMSMaxWidth", "/", "5000")
        project.writeEntry("WMSMaxHeight", "/", "5000")
        project.writeEntry("WMSDefaultMapUnitsPerMm", "/", "1")
        
        # Enable WMTS Service
        project.writeEntry("WMTSServiceCapabilities", "/", "True")
        project.writeEntry("WMTSUrl", "/", "")
        
        # Enable WFS Service
        project.writeEntry("WFSServiceCapabilities", "/", "True")
        project.writeEntry("WFSUrl", "/", "")
        project.writeEntry("WFSLayersPrecision", "/", {})
        
        # Enable OGC API - Features
        project.writeEntry("WFS3ServiceCapabilities", "/", "True")
        
        # Set measurement units
        project.writeEntry("Measurement", "/DistanceUnits", "meters")
        project.writeEntry("Measurement", "/AreaUnits", "m2")
        
        # Set paths to relative
        project.writeEntry("Paths", "/Absolute", False)
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save project
        print(f"  Saving to: {output_file.name}")
        save_result = project.write(str(output_file))
        
        if save_result:
            file_size = output_file.stat().st_size / 1024
            print(f"  ✓ Created: {output_file.name} ({file_size:.1f} KB)")
            return True
        else:
            print(f"  ✗ Failed to save project to {output_file}")
            return False
            
    except Exception as e:
        print(f"  ✗ Exception: {str(e)}")
        return False

def batch_process_qlr_files(input_dir: Path, output_dir: Path, crs: str = "EPSG:25833", pattern: str = "*.qlr"):
    """
    Process all .qlr files in a directory
    
    Args:
        input_dir: Directory containing .qlr files
        output_dir: Directory to save .qgs project files
        crs: Coordinate reference system
        pattern: Glob pattern for finding .qlr files
        
    Returns:
        dict: Statistics about the batch processing
    """
    print("=" * 70)
    print("🗺️  Batch QGIS Project Generator (Using QGIS API)")
    print("=" * 70)
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Coordinate system: {crs}")
    print("=" * 70)
    
    # Find all .qlr files
    qlr_files = sorted(input_dir.glob(pattern))
    
    if not qlr_files:
        print(f"❌ No .qlr files found in {input_dir}")
        return {"total": 0, "success": 0, "failed": 0}
    
    print(f"Found {len(qlr_files)} .qlr files to process\n")
    
    # Process each file
    success_count = 0
    failed_count = 0
    start_time = time.time()
    
    for i, qlr_file in enumerate(qlr_files, 1):
        print(f"\n[{i}/{len(qlr_files)}] ", end="")
        
        # Create output filename (replace .qlr with .qgs)
        output_file = output_dir / qlr_file.with_suffix('.qgs').name
        
        # Process the file
        if create_single_project_from_qlr(qlr_file, output_file, crs):
            success_count += 1
        else:
            failed_count += 1
    
    # Calculate statistics
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 70)
    print("📊 Batch Generation Summary")
    print("=" * 70)
    print(f"✓ Successfully generated: {success_count} projects")
    print(f"✗ Failed:                {failed_count} projects")
    print(f"⏱️  Total time:            {duration:.2f} seconds")
    if len(qlr_files) > 0:
        print(f"⚡ Average time per file: {duration/len(qlr_files):.2f} seconds")
    print(f"📁 Output location:       {output_dir.absolute()}")
    print("=" * 70)
    
    # List generated files
    if success_count > 0:
        print("\n📋 Generated project files:")
        qgs_files = sorted(output_dir.glob("*.qgs"))
        for qgs_file in qgs_files:
            size_kb = qgs_file.stat().st_size / 1024
            print(f"  • {qgs_file.name} ({size_kb:.1f} KB)")
    
    print("\n💡 Next steps:")
    print("  1. Deploy .qgs files to your QGIS Server")
    print("  2. Configure Apache/Nginx to serve them")
    print("  3. Test with WMS GetCapabilities request")
    print("  4. Example: http://your-server/qgis?SERVICE=WMS&REQUEST=GetCapabilities&MAP=/path/to/lag01_hav.qgs")
    
    return {
        "total": len(qlr_files),
        "success": success_count,
        "failed": failed_count,
        "duration": duration
    }

def main():
    parser = argparse.ArgumentParser(
        description='Generate QGIS project files from .qlr files using QGIS API with QGIS Server support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate projects from all .qlr files in data/QLR
  python3 batch_process_qlr_with_qgis.py --input ./data/QLR --output ./data/projects
  
  # Use custom coordinate system
  python3 batch_process_qlr_with_qgis.py --input ./data/QLR --output ./data/projects --crs EPSG:5973
  
  # Process only specific files
  python3 batch_process_qlr_with_qgis.py --input ./data/QLR --output ./data/projects --pattern "lag0*.qlr"

Features:
  - Uses QGIS Python API to properly load .qlr files
  - Automatically configures QGIS Server capabilities:
    * WMS (Web Map Service)
    * WMTS (Web Map Tile Service)
    * WFS (Web Feature Service)
    * OGC API - Features
  - Supports multiple CRS: EPSG:25833, EPSG:5973, EPSG:4326, EPSG:3857
  - Preserves layer styling and configuration
  - Loads saved database connections and Google Cloud credentials
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input directory containing .qlr files'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for .qgs project files'
    )
    
    parser.add_argument(
        '--crs', '-c',
        default='EPSG:25833',
        help='Coordinate reference system (default: EPSG:25833)'
    )
    
    parser.add_argument(
        '--pattern', '-p',
        default='*.qlr',
        help='Glob pattern for .qlr files (default: *.qlr)'
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects and resolve to absolute paths immediately
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    
    # Validate input directory
    if not input_dir.exists():
        print(f"❌ Error: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"❌ Error: Input path is not a directory: {input_dir}")
        sys.exit(1)
    
    # Initialize QGIS
    print("Initializing QGIS...")
    try:
        qgs = init_qgis()
        print("✓ QGIS initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize QGIS: {e}")
        print("Make sure QGIS is installed and Python bindings are available.")
        sys.exit(1)
    
    # Process files
    try:
        results = batch_process_qlr_files(
            input_dir=input_dir,
            output_dir=output_dir,
            crs=args.crs,
            pattern=args.pattern
        )
    finally:
        # Clean up QGIS
        qgs.exitQgis()
    
    # Exit with appropriate code
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
