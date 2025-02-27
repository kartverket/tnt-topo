#!/usr/bin/env python3
"""
QGIS Project File Handler

This script performs various operations on QGIS project files:
1. Reinserting passwords from environment variables
2. Extracting datasources to text files
3. Replacing datasource connections
4. Removing passwords (Git-safe cleaning)
5. URL encoding for special characters
6. Extracting layers by datasource pattern

For use with TNT Topo QGIS project files.
"""

import os
import sys
import re
import shutil
import argparse
from typing import Dict, List, Optional
import lxml.etree as ET
from dotenv import load_dotenv

# Default list of QGIS project files
DEFAULT_QGIS_PROJECTS = [
    './data/Topo_2025.qgs',
    './data/TopoGraatone_2025.qgs',
    './data/earth.qgs',
    './data/enkel.qgs'
]

def load_env_variables() -> Dict[str, str]:
    """
    Load environment variables from .env file and extract password information.
    
    Returns:
        Dict[str, str]: Dictionary mapping hosts to passwords
    """
    # Try to load from .env file
    load_dotenv()
    
    # Get the secret from environment variable
    gsm_secret = os.environ.get("topo", "")
    
    # If not found, use default for development (this should be removed in production)
    if not gsm_secret:
        print("Warning: No 'topo' environment variable found, using development defaults")
        gsm_secret = "10.40.2.19=rendering_radar_envy_freebase 10.40.2.18=vending_overpower_postcard_chess"
    
    # Parse secrets into a dictionary
    secrets = {}
    try:
        secret_pairs = gsm_secret.split(" ")
        for secret in secret_pairs:
            if '=' in secret:
                host, password = secret.split("=", 1)
                secrets[host] = password
    except Exception as e:
        print(f"Error parsing secrets: {str(e)}")
    
    return secrets


def extract_datasources(qgis_projects: List[str], verbose: bool = False) -> None:
    """
    Extract all datasources from QGIS project files and save to datasources.txt.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        verbose (bool): Whether to print verbose output
    """
    for qgis_project in qgis_projects:
        if verbose:
            print(f"Extracting datasources from: {qgis_project}")
        
        try:
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            # Find all datasources in the QGIS project file
            datasources = root.findall('.//datasource')
            
            # Save all datasources to a file called datasources.txt in the same directory as the QGIS project file
            project_path = os.path.dirname(qgis_project)
            output_file = os.path.join(project_path, 'datasources.txt')
            
            with open(output_file, 'w') as f:
                for datasource in datasources:
                    if datasource.text:
                        f.write(datasource.text + '\n')
            
            if verbose:
                print(f"Extracted {len(datasources)} datasources to {output_file}")
        
        except Exception as e:
            print(f"Error extracting datasources from {qgis_project}: {str(e)}")


def replace_datasources(qgis_projects: List[str], host_pattern: str = 'host=kv-vm-00436', 
                        verbose: bool = False) -> None:
    """
    Replace datasources matching a pattern with new URL-based datasources.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        host_pattern (str): Pattern to match in datasources
        verbose (bool): Whether to print verbose output
    """
    for qgis_project in qgis_projects:
        if verbose:
            print(f"Replacing datasources in: {qgis_project}")
        
        try:
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            datasources = root.findall('.//datasource')
            replaced_count = 0
            
            # Replace datasources matching the pattern
            for datasource in datasources:
                if datasource.text and host_pattern in datasource.text:
                    try:
                        # Extract the dbname and the table name from the datasource
                        dbname = datasource.text.split("dbname='")[1].split("'")[0]
                        # Remove "prod"." from the table name
                        table = datasource.text.split('table="prod"."')[1].split('"')[0]
                        # Extract SQL part if it exists
                        sql_part = ""
                        if 'sql=\"' in datasource.text:
                            sql_part = datasource.text.split('sql=\"')[1]
                        
                        # Create the new datasource
                        new_datasource = f"/vsicurl/https://s3-rin.statkart.no/topo-nkart-fgb/{dbname}/{table}.fgb|layername={table}"
                        
                        # Add SQL subset if it exists
                        if sql_part:
                            new_datasource += f"|subset=\"{sql_part}"
                        
                        datasource.text = new_datasource
                        replaced_count += 1
                        
                        if verbose:
                            print(f"Replaced: {new_datasource}")
                    except Exception as e:
                        print(f"Error replacing datasource: {str(e)}")
            
            # Save the modified QGIS project file
            if replaced_count > 0:
                tree.write(qgis_project, encoding='utf-8', xml_declaration=True)
                print(f"Replaced {replaced_count} datasources in {qgis_project}")
        
        except Exception as e:
            print(f"Error processing {qgis_project}: {str(e)}")


def remove_passwords(qgis_projects: List[str], verbose: bool = False) -> None:
    """
    Remove passwords from QGIS project files.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        verbose (bool): Whether to print verbose output
    """
    for qgis_project in qgis_projects:
        if verbose:
            print(f"Removing passwords from: {qgis_project}")
        
        try:
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            datasources = root.findall('.//datasource')
            cleaned_count = 0
            
            # Remove all passwords from the datasources
            for datasource in datasources:
                if datasource.text and 'password=' in datasource.text:
                    password = datasource.text.split('password=')[1].split(' ')[0]
                    datasource.text = datasource.text.replace(password, "''")
                    cleaned_count += 1
            
            # Save the modified QGIS project file if changes were made
            if cleaned_count > 0:
                tree.write(qgis_project, encoding='utf-8', xml_declaration=True)
                print(f"Removed {cleaned_count} passwords from {qgis_project}")
        
        except Exception as e:
            print(f"Error cleaning {qgis_project}: {str(e)}")


def reinsert_passwords(qgis_projects: List[str], secrets: Dict[str, str], verbose: bool = False) -> None:
    """
    Reinsert passwords from environment variables into QGIS project files.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        secrets (Dict[str, str]): Dictionary mapping hosts to passwords
        verbose (bool): Whether to print verbose output
    """
    for qgis_project in qgis_projects:
        if verbose:
            print(f"Reinserting passwords in: {qgis_project}")
        
        try:
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            datasources = root.findall('.//datasource')
            updated_count = 0
            
            for datasource in datasources:
                if datasource.text is not None and 'password=' in datasource.text:
                    try:
                        host = datasource.text.split('host=')[1].split(' ')[0]
                        # Replace the password if the host is in our secrets
                        if host in secrets:
                            new_password = secrets[host]
                            datasource.text = re.sub(r"password='[^']*'", f"password='{new_password}'", datasource.text)
                            updated_count += 1
                    except Exception as e:
                        if verbose:
                            print(f"Error processing datasource: {str(e)}")
            
            # Save the modified QGIS project file if changes were made
            if updated_count > 0:
                tree.write(qgis_project, encoding='utf-8', xml_declaration=True)
                print(f"Updated {updated_count} passwords in {qgis_project}")
        
        except Exception as e:
            print(f"Error processing {qgis_project}: {str(e)}")


def encode_urls(qgis_projects: List[str], verbose: bool = False) -> None:
    """
    Encode special characters (å, ø, æ) in datasource URLs.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        verbose (bool): Whether to print verbose output
    """
    for qgis_project in qgis_projects:
        if verbose:
            print(f"Encoding URLs in: {qgis_project}")
        
        try:
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            datasources = root.findall('.//datasource')
            encoded_count = 0
            
            for datasource in datasources:
                if datasource.text is not None:
                    original_text = datasource.text
                    
                    # Find the first | in the datasource string
                    first_pipe = datasource.text.find('|')
                    if first_pipe != -1:
                        # Encode the URL until the first pipe
                        url_part = datasource.text[:first_pipe]
                        url_part = url_part.replace("æ", "%C3%A6").replace("ø", "%C3%B8").replace("å", "%C3%A5")
                        datasource.text = url_part + datasource.text[first_pipe:]
                        
                        # Check if any encoding was actually done
                        if datasource.text != original_text:
                            encoded_count += 1
            
            # Save the modified QGIS project file if changes were made
            if encoded_count > 0:
                tree.write(qgis_project, encoding='utf-8', xml_declaration=True)
                print(f"Encoded URLs in {encoded_count} datasources in {qgis_project}")
        
        except Exception as e:
            print(f"Error processing {qgis_project}: {str(e)}")


def extract_layers_by_datasource(qgis_projects: List[str], datasource_pattern: str, 
                                 output_project: str, verbose: bool = False) -> None:
    """
    Extract layers matching a datasource pattern to a new QGIS project.
    
    Args:
        qgis_projects (List[str]): List of QGIS project file paths
        datasource_pattern (str): Pattern to match in datasources
        output_project (str): Path to save the new project file
        verbose (bool): Whether to print verbose output
    """
    try:
        if verbose:
            print(f"Extracting layers matching '{datasource_pattern}' to {output_project}")
        
        processed = False
        
        for qgis_project in qgis_projects:
            if verbose:
                print(f"Processing project file: {qgis_project}")
            
            tree = ET.parse(qgis_project)
            root = tree.getroot()
            
            # Create new project structure
            new_tree = ET.ElementTree(ET.Element('qgis'))
            new_root = new_tree.getroot()
            
            # Copy project information (properties, relations, mapcanvas)
            for element_name in ['properties', 'relations', 'mapcanvas']:
                element = root.find(element_name)
                if element is not None:
                    new_root.append(ET.fromstring(ET.tostring(element)))
            
            # Get original layer structure preserving document order
            matching_layers = {}
            layer_order = []
            
            projectlayers = root.find('projectlayers')
            if projectlayers is not None:
                for layer in projectlayers.findall('maplayer'):
                    layer_id_element = layer.find('id')
                    datasource = layer.find('datasource')
                    
                    if (layer_id_element is not None and datasource is not None 
                            and datasource.text and datasource_pattern in datasource.text):
                        layer_id = layer_id_element.text
                        layer_order.append(layer_id)
                        matching_layers[layer_id] = {'layer': layer, 'element': layer, 'id': layer_id}
            
            if not matching_layers:
                if verbose:
                    print(f"No layers found matching pattern '{datasource_pattern}' in {qgis_project}")
                continue
            
            processed = True
            
            # Clear existing elements in the new project
            for element in new_root.findall('projectlayers') + new_root.findall('layerorder') + \
                          new_root.findall('layer-tree-group') + new_root.findall('legend'):
                new_root.remove(element)
            
            # Create basic structure
            new_projectlayers = ET.SubElement(new_root, 'projectlayers')
            new_layerorder = ET.SubElement(new_root, 'layerorder')
            new_layer_tree = ET.SubElement(new_root, 'layer-tree-group')
            new_legend = ET.SubElement(new_root, 'legend')
            new_legend.set('updateDrawingOrder', "true")
            
            # Copy matching layers in original order
            final_layer_order = []
            
            # Use order from layer_order
            for layer_id in layer_order:
                if layer_id in matching_layers:
                    final_layer_order.append(layer_id)
            
            # Add any matching layers not in original order
            for layer_id in matching_layers:
                if layer_id not in final_layer_order:
                    final_layer_order.append(layer_id)
            
            # Add layers to project preserving order
            for layer_id in final_layer_order:
                layer = matching_layers[layer_id]['element']
                
                # Add to projectlayers
                new_projectlayers.append(ET.fromstring(ET.tostring(layer)))
                
                # Add to layerorder
                layer_elem = ET.SubElement(new_layerorder, 'layer')
                layer_elem.set('id', layer_id)
                
                # Add to layer tree
                tree_layer = root.find(f'.//layer-tree-layer[@id="{layer_id}"]')
                if tree_layer is not None:
                    parent = tree_layer.getparent()
                    if parent.tag == 'layer-tree-group':
                        # Create/reuse group
                        group_name = parent.get('name')
                        existing_group = None
                        for group in new_layer_tree.findall('layer-tree-group'):
                            if group.get('name') == group_name:
                                existing_group = group
                                break
                        if existing_group is None:
                            existing_group = ET.SubElement(new_layer_tree, 'layer-tree-group')
                            existing_group.attrib.update(parent.attrib)
                        existing_group.append(ET.fromstring(ET.tostring(tree_layer)))
                    else:
                        new_layer_tree.append(ET.fromstring(ET.tostring(tree_layer)))
                
                # Add to legend
                legend_layer = root.find(f'.//legendlayer/filegroup/legendlayerfile[@layerid="{layer_id}"]/../..')
                if legend_layer is not None:
                    parent = legend_layer.getparent()
                    if parent.tag == 'legendgroup':
                        # Create/reuse group
                        group_name = parent.get('name')
                        existing_group = None
                        for group in new_legend.findall('legendgroup'):
                            if group.get('name') == group_name:
                                existing_group = group
                                break
                        if existing_group is None:
                            existing_group = ET.SubElement(new_legend, 'legendgroup')
                            existing_group.attrib.update(parent.attrib)
                        existing_group.append(ET.fromstring(ET.tostring(legend_layer)))
                    else:
                        new_legend.append(ET.fromstring(ET.tostring(legend_layer)))
            
            # Skip to the next project if this one had matching layers
            break
        
        if processed:
            # Create directory for output file if it doesn't exist
            output_dir = os.path.dirname(output_project)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Save the new project
            new_tree.write(output_project, encoding='utf-8', xml_declaration=True)
            print(f"Extracted {len(final_layer_order)} layers to {output_project}")
            if verbose:
                print("Layer order:", final_layer_order)
        else:
            print(f"No layers matching '{datasource_pattern}' found in any project file")
    
    except Exception as e:
        print(f"Error extracting layers: {str(e)}")
        raise


def main() -> int:
    """
    Main function to parse arguments and perform operations on QGIS project files.
    
    Returns:
        int: Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(description="QGIS Project File Handler")
    parser.add_argument("-d", "--directory", default="./data",
                      help="Directory containing QGIS project files (default: ./data)")
    parser.add_argument("-f", "--files", nargs='+',
                      help="Specific QGIS project files to process (overrides directory)")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Show verbose output")
    
    # Operation arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--extract-datasources", action="store_true",
                     help="Extract datasources to text files")
    group.add_argument("--replace-datasources", action="store_true",
                     help="Replace datasources with URL-based datasources")
    group.add_argument("--remove-passwords", action="store_true",
                     help="Remove passwords from QGIS files")
    group.add_argument("--reinsert-passwords", action="store_true",
                     help="Reinsert passwords from environment variables")
    group.add_argument("--encode-urls", action="store_true",
                     help="Encode special characters in URLs")
    group.add_argument("--extract-layers", action="store_true",
                     help="Extract layers matching a pattern to a new project")
    
    # Additional options for specific operations
    parser.add_argument("--host-pattern", default="host=kv-vm-00436",
                      help="Host pattern for replace-datasources (default: host=kv-vm-00436)")
    parser.add_argument("--datasource-pattern",
                      help="Pattern to match for extract-layers")
    parser.add_argument("--output-project",
                      help="Output project file for extract-layers")
    
    args = parser.parse_args()
    
    # Find QGIS project files
    qgis_projects = []
    if args.files:
        for file in args.files:
            if os.path.exists(file) and file.endswith('.qgs'):
                qgis_projects.append(file)
            else:
                print(f"Warning: File {file} does not exist or is not a QGIS project file")
    else:
        # Use default projects or find all in directory
        if os.path.exists(args.directory):
            pattern = os.path.join(args.directory, "*.qgs")
            qgis_projects = glob.glob(pattern)
        else:
            print(f"Error: Directory {args.directory} does not exist")
            return 1
    
    if not qgis_projects:
        print("Error: No QGIS project files found")
        return 1
    
    if args.verbose:
        print(f"Found {len(qgis_projects)} QGIS project files")
        for project in qgis_projects:
            print(f"  {project}")
    
    # Perform the specified operation
    if args.extract_datasources:
        extract_datasources(qgis_projects, args.verbose)
    
    elif args.replace_datasources:
        replace_datasources(qgis_projects, args.host_pattern, args.verbose)
    
    elif args.remove_passwords:
        remove_passwords(qgis_projects, args.verbose)
    
    elif args.reinsert_passwords:
        secrets = load_env_variables()
        reinsert_passwords(qgis_projects, secrets, args.verbose)
    
    elif args.encode_urls:
        encode_urls(qgis_projects, args.verbose)
    
    elif args.extract_layers:
        if not args.datasource_pattern:
            print("Error: --datasource-pattern is required for --extract-layers")
            return 1
        if not args.output_project:
            print("Error: --output-project is required for --extract-layers")
            return 1
        
        extract_layers_by_datasource(qgis_projects, args.datasource_pattern, 
                                    args.output_project, args.verbose)
    
    print("QGIS project file handling finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())