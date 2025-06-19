import xml.etree.ElementTree as ET
import gzip
import argparse
import os
import sys
import re  # Add regex module for password sanitization


# Fetch the Legend of a Layer 
# example url call:https://topo-qgis.atkv3-dev.kartverket-intern.cloud/qgis/?MAP=/opt/qgis/Topo_2025.qgs&SERVICE=WMS&REQUEST=GetLegendGraphic&LAYERTITLE=False&LAYER=Topo
def getLegend(layer_name, base_url=None, map_file=None):
    """
    Returns the legend URL for a given layer name.
    
    Args:
        layer_name (str): The name of the layer to get legend for
        base_url (str, optional): Custom base URL for the WMS service
        map_file (str, optional): Custom path to the map file
        
    Returns:
        str: Complete URL for GetLegendGraphic request
    """
    if base_url is None:
        base_url = "https://topo-qgis.atkv3-dev.kartverket-intern.cloud/qgis/"
    if map_file is None:
        map_file = "/opt/qgis/Topo_2025.qgs"
    
    # URL encode the layer name to handle special characters
    import urllib.parse
    encoded_layer_name = urllib.parse.quote(layer_name)
    
    return f"{base_url}?MAP={map_file}&SERVICE=WMS&REQUEST=GetLegendGraphic&LAYERTITLE=False&LAYER={encoded_layer_name}"
    

def parse_qgis_project_xml(project_file_path):
    """
    Parses a QGIS project file (.qgs or .qgz) and returns the XML root element.
    """
    xml_content = None
    try:
        if project_file_path.lower().endswith('.qgz'):
            with gzip.open(project_file_path, 'rb') as f_in:
                xml_content = f_in.read()
        elif project_file_path.lower().endswith('.qgs'):
            with open(project_file_path, 'rb') as f:
                xml_content = f.read()
        else:
            print(f"Error: Unsupported file type: {project_file_path}. Please provide a .qgs or .qgz file.", file=sys.stderr)
            return None

        if xml_content:
            # Remove default namespace if present to simplify XPath queries
            xml_content = xml_content.replace(b'xmlns="http://www.qgis.org/dtd"', b'')
            root = ET.fromstring(xml_content)
            return root
    except FileNotFoundError:
        print(f"Error: Project file not found at {project_file_path}", file=sys.stderr)
    except ET.ParseError as e:
        print(f"Error: Could not parse XML in {project_file_path}. {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred while reading {project_file_path}: {e}", file=sys.stderr)
    return None

def extract_layer_tree_structure(root):
    """
    Extracts the layer tree structure including groups and their layers.
    Returns a dictionary with group structure and a mapping of layer IDs to their groups.
    """
    layer_tree = {}
    layer_to_group = {}

    # Find the layer tree root element
    layer_tree_root = root.find(".//layer-tree-group")
    if layer_tree_root is None:
        return layer_tree, layer_to_group

    # Process layer tree recursively
    def process_group(group_element, parent_path=""):
        group_name = group_element.get("name", "")
        if not group_name:
            group_name = "Unnamed Group"
        
        current_path = f"{parent_path}/{group_name}" if parent_path else group_name
        
        # Create entry for this group
        if current_path not in layer_tree:
            layer_tree[current_path] = {"name": group_name, "layers": [], "groups": []}
        
        # Process child layers in this group
        for layer_element in group_element.findall("./layer-tree-layer"):
            layer_id = layer_element.get("id", "")
            layer_name = layer_element.get("name", "")
            if layer_id:
                layer_tree[current_path]["layers"].append({"id": layer_id, "name": layer_name})
                layer_to_group[layer_id] = current_path
        
        # Process nested groups
        for child_group in group_element.findall("./layer-tree-group"):
            child_group_name = child_group.get("name", "Unnamed Group")
            child_path = f"{current_path}/{child_group_name}"
            layer_tree[current_path]["groups"].append(child_path)
            process_group(child_group, current_path)
    
    # Start processing from the root group
    process_group(layer_tree_root)
    
    return layer_tree, layer_to_group

def sanitize_datasource(datasource):
    """
    Removes password information from datasource strings to prevent credential exposure.
    Handles common database connection string formats.
    """
    if not datasource or datasource == "N/A":
        return datasource
        
    # Handle various password patterns in connection strings
    # Pattern 1: password=value or pwd=value (quoted or unquoted)
    sanitized = re.sub(r'(password\s*=\s*[\'"]?)([^\'"\s]+)([\'"]?)', r'\1[PASSWORD_REMOVED]\3', 
                      datasource, flags=re.IGNORECASE)
    sanitized = re.sub(r'(pwd\s*=\s*[\'"]?)([^\'"\s]+)([\'"]?)', r'\1[PASSWORD_REMOVED]\3', 
                      sanitized, flags=re.IGNORECASE)
    
    # Pattern 2: URI format - username:password@host
    sanitized = re.sub(r'(://[^:@]+:)([^@]+)(@)', r'\1[PASSWORD_REMOVED]\3', sanitized)
    
    # Pattern 3: PG connection string - host=X port=Y dbname=Z user=A password=B
    sanitized = re.sub(r'(\spassword=)[^\s]*', r'\1[PASSWORD_REMOVED]', sanitized, flags=re.IGNORECASE)
    
    return sanitized

def extract_layer_documentation_data(root):
    """
    Extracts datasource and scale visibility for each map layer.
    Also includes group membership information.
    """
    layers_data = []
    if root is None:
        return layers_data, {}
    
    # Extract layer tree structure first
    layer_tree, layer_to_group = extract_layer_tree_structure(root)

    for map_layer_node in root.findall(".//maplayer"):
        layer_name = map_layer_node.findtext("layername", default="N/A")
        layer_id = map_layer_node.findtext("id", default="N/A") # QGIS 3.x stores ID in id element
        if layer_id == "N/A": # Fallback for older QGIS versions or different structures
             layer_id = map_layer_node.get("id", default="N/A")

        datasource = map_layer_node.findtext("datasource", default="N/A")
        # Sanitize the datasource to remove passwords
        sanitized_datasource = sanitize_datasource(datasource)
        
        # Default values
        min_scale_text = "Always Visible"
        max_scale_text = "Always Visible"
        min_scale = "0"
        max_scale = "0"
        
        # Check for scale visibility settings in different locations
        # First try direct attributes on the maplayer tag
        if map_layer_node.get("hasScaleBasedVisibilityFlag") == "1":
            min_scale = map_layer_node.get("minScale", map_layer_node.get("minimumScale", "0"))
            max_scale = map_layer_node.get("maxScale", map_layer_node.get("maximumScale", "0"))
        
        # If not found directly on the maplayer tag, look for a scalebasedvisibility element
        if min_scale == "0" and max_scale == "0":
            scale_visibility_node = map_layer_node.find("scalebasedvisibility")
            if scale_visibility_node is not None and scale_visibility_node.get("enabled") == "1":
                min_scale = scale_visibility_node.get("minimumScale", 
                           scale_visibility_node.get("minimumscale", "0"))
                max_scale = scale_visibility_node.get("maximumScale",
                           scale_visibility_node.get("maximumscale", "0"))
        
        # Process the scale values if they exist
        if min_scale != "0" or max_scale != "0":
            try:
                min_scale_text = f"1:{int(float(min_scale))}" if min_scale != "0" else "No Min (Visible Zoomed Out)"
                max_scale_text = f"1:{int(float(max_scale))}" if max_scale != "0" else "No Max (Visible Zoomed In)"
            except (ValueError, TypeError):
                # In case conversion fails
                min_scale_text = f"Error parsing: {min_scale}"
                max_scale_text = f"Error parsing: {max_scale}"
            
        # Find group membership for this layer
        group_path = layer_to_group.get(layer_id, "")

        layers_data.append({
            "name": layer_name,
            "id": layer_id,
            "datasource": sanitized_datasource,  # Use sanitized version
            "min_scale": min_scale_text,
            "max_scale": max_scale_text,
            "group_path": group_path
        })
    
    return layers_data, layer_tree

def get_current_date():
    """
    Returns the current date in a readable format for documentation.
    """
    from datetime import datetime
    return datetime.now().strftime("%B %d, %Y")

def format_as_markdown(project_file_name, layers_data, layer_tree, legend_config=None):
    """
    Formats the extracted layer data as GitHub Wiki compatible Markdown.
    Optimized for GitHub Wiki with proper navigation and formatting.
    
    Args:
        project_file_name (str): Name of the project file
        layers_data (list): List of layer data dictionaries
        layer_tree (dict): Layer tree structure
        legend_config (dict, optional): Configuration for legend generation
    """
    if legend_config is None:
        legend_config = {"enabled": True, "base_url": None, "map_file": None}
    if not layers_data:
        return f"# {project_file_name} - Layer Documentation\n\n❌ **No layer data found** - Project could not be parsed or contains no layers.\n\n---\n*Generated on {get_current_date()}*\n"

    # Extract project name without extension for cleaner titles
    project_name = os.path.splitext(project_file_name)[0]
    
    md_string = f"# {project_name} - Layer Documentation\n\n"
    
    # Add project summary badge-style info
    md_string += f"📊 **Project Summary**: {len(layers_data)} layers • {len(layer_tree)} groups • Generated on {get_current_date()}\n\n"
    
    # Add navigation links for GitHub Wiki
    md_string += "## 🧭 Quick Navigation\n\n"
    md_string += "| Section | Description |\n"
    md_string += "|---------|-------------|\n"
    md_string += "| [📖 Scale Guide](#-scale-interpretation-guide) | Understanding layer visibility settings |\n"
    md_string += "| [🗂️ Layer Groups](#%EF%B8%8F-layer-groups-overview) | Project structure overview |\n"
    
    if legend_config["enabled"]:
        md_string += "| [📋 Layer Details](#-detailed-layer-information) | Complete layer information with legends |\n"
    else:
        md_string += "| [📋 Layer Details](#-detailed-layer-information) | Complete layer information |\n"
    
    md_string += "| [📈 Statistics](#-project-statistics) | Summary and provider breakdown |\n\n"
    
    # Add scale interpretation notes
    md_string += "## 📖 Scale Interpretation Guide\n\n"
    md_string += "> 💡 **Understanding Scale Values**: How QGIS determines when layers are visible based on map zoom level.\n\n"
    md_string += "| Scale Type | Description | Example |\n"
    md_string += "|------------|-------------|----------|\n"
    md_string += "| **Min Scale (Zoomed Out)** | Layer visible when map scale ≥ this value | `1:50000` = visible at 1:50000, 1:100000, etc. |\n"
    md_string += "| **Max Scale (Zoomed In)** | Layer visible when map scale < this value | `1:1000` = visible at 1:500, 1:250, etc. |\n"
    md_string += "| **Always Visible** | No scale-based visibility configured | Layer shows at all zoom levels |\n"
    md_string += "| **No Min/Max** | One limit not set | `No Min` = visible zoomed out, `No Max` = visible zoomed in |\n\n"
    
    # Add layer groups overview
    md_string += "## 🗂️ Layer Groups Overview\n\n"
    md_string += "> **Project Structure**: Hierarchical organization of layers within the QGIS project.\n\n"

    # Helper function to recursively generate the group structure in the markdown
    def format_group_structure(group_path, indent=0):
        nonlocal md_string
        if group_path not in layer_tree:
            return
        
        group_info = layer_tree[group_path]
        group_name = group_info["name"]

        # Add group to markdown with proper indentation
        md_string += f"{'  ' * indent}- **{group_name}** ({len(group_info['layers'])} layers)\n"
        
        # Recursively process child groups
        for child_group_path in group_info["groups"]:
            format_group_structure(child_group_path, indent+1)
    
    # Start with the root groups
    root_groups = [path for path in layer_tree.keys() if "/" not in path]
    for group_path in root_groups:
        format_group_structure(group_path)
    
    # Add ungrouped layers count if any
    ungrouped_layers = [layer for layer in layers_data if not layer.get("group_path")]
    if ungrouped_layers:
        md_string += f"\n- 📄 **Ungrouped Layers** ({len(ungrouped_layers)} layers)\n"
    
    # Add detailed layer information by group
    md_string += "\n## 📋 Detailed Layer Information\n\n"
    if legend_config["enabled"]:
        md_string += "> 🔍 **Layer Details**: Complete information for each layer including data sources, visibility settings, and interactive legends.\n\n"
    else:
        md_string += "> 🔍 **Layer Details**: Complete information for each layer including data sources and visibility settings.\n\n"
    
    # Helper function to create a table for layers in a specific group
    def create_group_table(group_path, group_layers):
        nonlocal md_string
        group_name = layer_tree[group_path]["name"] if group_path in layer_tree else "Ungrouped Layers"
        
        # Use GitHub-style collapsible sections
        md_string += f"<details>\n<summary>📂 <strong>{group_name}</strong> ({len(group_layers)} layers)</summary>\n\n"
        
        # Table headers - include legend column if enabled
        if legend_config["enabled"]:
            md_string += "| Layer Name | Datasource | Min Scale | Max Scale | Legend |\n"
            md_string += "|------------|------------|-----------|----------|--------|\n"
        else:
            md_string += "| Layer Name | Datasource | Min Scale | Max Scale |\n"
            md_string += "|------------|------------|-----------|----------|\n"
        
        for layer in group_layers:
            # Escape pipe characters for Markdown table
            datasource_md = layer['datasource'].replace('|', '\\|') if layer['datasource'] else 'N/A'
            layer_name_md = layer['name'].replace('|', '\\|') if layer['name'] else 'N/A'
            
            # Truncate very long datasources for better GitHub Wiki display
            datasource_limit = 100 if legend_config["enabled"] else 120
            if len(datasource_md) > datasource_limit:
                datasource_md = datasource_md[:datasource_limit-3] + "..."
            
            # Build table row
            row = f"| {layer_name_md} | {datasource_md} | {layer['min_scale']} | {layer['max_scale']}"
            
            # Add legend column if enabled
            if legend_config["enabled"]:
                legend_url = getLegend(layer['name'], legend_config["base_url"], legend_config["map_file"])
                # legend_image = f"![{layer['name']} Legend]({legend_url})"
                # row += f" | {legend_image}"
                # Use a clickable link instead of embedded image
                row += f" | [🎨 Legend]({legend_url})"            
            row += " |\n"
            md_string += row
        
        md_string += "\n</details>\n\n"
    
    # Create a dictionary to group layers by their group path, maintaining order
    layers_by_group = {}
    for layer in layers_data:
        group_path = layer.get('group_path', '')
        if group_path not in layers_by_group:
            layers_by_group[group_path] = []
        layers_by_group[group_path].append(layer)
    
    # Sort layers within each group based on their order in the layer tree
    def sort_layers_by_tree_order(group_path, group_layers):
        if group_path in layer_tree:
            # Create a mapping of layer IDs to their order in the tree
            tree_layers = layer_tree[group_path]["layers"]
            layer_order = {layer_info["id"]: idx for idx, layer_info in enumerate(tree_layers)}
            
            # Sort group_layers based on their position in the tree
            return sorted(group_layers, key=lambda layer: layer_order.get(layer["id"], 999))
        return group_layers
    
    # Apply sorting to all groups
    for group_path in layers_by_group:
        layers_by_group[group_path] = sort_layers_by_tree_order(group_path, layers_by_group[group_path])
    
    # Process groups in the order they appear in the layer tree
    def process_groups_in_order(parent_path=""):
        # Get groups at this level
        if parent_path == "":
            # Root level groups
            current_groups = [path for path in layer_tree.keys() if "/" not in path]
        else:
            # Child groups of the current parent
            if parent_path in layer_tree:
                current_groups = layer_tree[parent_path]["groups"]
            else:
                return
        
        # Process each group at this level
        for group_path in current_groups:
            if group_path in layers_by_group:
                create_group_table(group_path, layers_by_group[group_path])
            
            # Recursively process child groups
            process_groups_in_order(group_path)
    
    # Start processing from root level
    process_groups_in_order()
    
    # Handle ungrouped layers
    if ungrouped_layers:
        create_group_table("", ungrouped_layers)
    
    # Add summary statistics
    md_string += "## 📈 Project Statistics\n\n"
    md_string += "> 📊 **Overview**: Summary of layers, groups, and data providers in this QGIS project.\n\n"
    
    # Create statistics in a nice GitHub-style info box
    md_string += "### 📋 Summary\n\n"
    md_string += "| Metric | Count |\n"
    md_string += "|--------|-------|\n"
    md_string += f"| 🗂️ **Total Layers** | {len(layers_data)} |\n"
    md_string += f"| 📁 **Layer Groups** | {len(layer_tree)} |\n"
    md_string += f"| 📄 **Ungrouped Layers** | {len(ungrouped_layers)} |\n\n"
    
    # Provider statistics
    provider_counts = {}
    for layer in layers_data:
        datasource = layer.get('datasource', '')
        if 'provider=' in datasource:
            provider = datasource.split('provider=')[1].split()[0].strip("'\"")
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        elif 'postgres://' in datasource or 'host=' in datasource:
            provider_counts['postgres'] = provider_counts.get('postgres', 0) + 1
        elif datasource.endswith('.shp') or 'ogr:' in datasource:
            provider_counts['ogr'] = provider_counts.get('ogr', 0) + 1
        else:
            provider_counts['other'] = provider_counts.get('other', 0) + 1
    
    md_string += "### 🔌 Data Providers\n\n"
    md_string += "| Provider | Layer Count | Description |\n"
    md_string += "|----------|-------------|-------------|\n"
    
    provider_descriptions = {
        'postgres': 'PostgreSQL database layers',
        'ogr': 'Vector file formats (Shapefile, GeoJSON, etc.)',
        'gdal': 'Raster file formats',
        'wms': 'Web Map Service layers',
        'wfs': 'Web Feature Service layers',
        'memory': 'Temporary in-memory layers',
        'other': 'Other or unspecified providers'
    }
    
    for provider, count in sorted(provider_counts.items()):
        description = provider_descriptions.get(provider, 'Custom or specialized provider')
        md_string += f"| `{provider}` | {count} | {description} |\n"
    
    # Add footer with generation info
    md_string += f"\n---\n\n🤖 *Generated automatically on {get_current_date()} using the QGIS Project Toolkit*\n\n"
    md_string += "💡 **Need help?** Check the [project documentation](../README.md) for more information about these tools.\n"
    
    return md_string

def generate_wiki_sidebar(layers_data, layer_tree, project_name):
    """
    Generates a GitHub Wiki sidebar (_Sidebar.md) content for easy navigation.
    """
    sidebar = f"## 📖 {project_name} Wiki\n\n"
    sidebar += "### 🏠 Main Pages\n"
    sidebar += "- [🏠 Home](Home)\n"
    sidebar += f"- [📋 Layer Documentation]({project_name.replace(' ', '-')}-Layer-Documentation)\n\n"
    
    sidebar += "### 🗂️ Layer Groups\n"
    root_groups = [path for path in layer_tree.keys() if "/" not in path]
    for group_path in root_groups[:10]:  # Limit to first 10 groups to avoid sidebar clutter
        group_name = layer_tree[group_path]["name"]
        safe_name = group_name.replace(' ', '-').replace('/', '-')
        sidebar += f"- 📁 [{group_name}]({project_name.replace(' ', '-')}-Layer-Documentation#{safe_name.lower()})\n"
    
    if len(root_groups) > 10:
        sidebar += f"- ... and {len(root_groups) - 10} more groups\n"
    
    sidebar += f"\n### 📊 Quick Stats\n"
    sidebar += f"- 🗂️ {len(layers_data)} layers\n"
    sidebar += f"- 📁 {len(layer_tree)} groups\n"
    
    return sidebar

def format_as_csv(layers_data):
    """
    Formats the extracted layer data as a CSV string.
    """
    if not layers_data:
        return ""

    # Import csv module here to keep it local to this function if not used elsewhere
    import csv
    from io import StringIO

    output = StringIO()
    # Use a more robust CSV writer that handles quoting
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # CSV Header
    header = ["Layer Name", "Layer ID", "Group Path", "Datasource", "Min Scale", "Max Scale"]
    writer.writerow(header)

    for layer in layers_data:
        group_path = layer.get('group_path', 'Ungrouped')
        if not group_path: # Ensure empty group_path is represented as "Ungrouped"
            group_path = 'Ungrouped'
            
        row = [
            layer.get('name', 'N/A'),
            layer.get('id', 'N/A'),
            group_path,
            layer.get('datasource', 'N/A'),
            layer.get('min_scale', 'N/A'),
            layer.get('max_scale', 'N/A')
        ]
        writer.writerow(row)
    
    return output.getvalue()

def main():
    parser = argparse.ArgumentParser(description="Generate GitHub Wiki documentation for layers in a QGIS project file, including group structure, datasource and zoom levels (scale visibility).")
    parser.add_argument("input_project", help="Path to the input QGIS project file (.qgs or .qgz)")
    parser.add_argument("-o", "--output", help="Path to the output Markdown file. If not specified, prints to console.")
    parser.add_argument("--csv", help="Path to the output CSV file.")
    parser.add_argument("--sidebar", help="Generate GitHub Wiki sidebar file (_Sidebar.md) at this path.")
    parser.add_argument("--wiki-title", help="Custom title for the wiki page (defaults to project filename).")
    parser.add_argument("--legend-base-url", help="Base URL for WMS legend service (defaults to topo-qgis.atkv3-dev.kartverket-intern.cloud)")
    parser.add_argument("--legend-map-file", help="Path to map file on server for legend generation (defaults to /opt/qgis/Topo_2025.qgs)")
    parser.add_argument("--no-legends", action="store_true", help="Disable legend generation in documentation")
    
    args = parser.parse_args()

    project_file_path = args.input_project
    output_file_path = args.output
    csv_output_path = args.csv
    sidebar_path = args.sidebar
    wiki_title = args.wiki_title
    
    # Configure legend settings
    legend_config = {
        "enabled": not args.no_legends,
        "base_url": args.legend_base_url,
        "map_file": args.legend_map_file
    }

    if not os.path.exists(project_file_path):
        print(f"Error: Input project file '{project_file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    xml_root = parse_qgis_project_xml(project_file_path)
    
    if xml_root is None:
        sys.exit(1)
        
    layers_data, layer_tree = extract_layer_documentation_data(xml_root)
    project_file_name = os.path.basename(project_file_path)
    project_name = wiki_title or os.path.splitext(project_file_name)[0]
    
    # Generate Markdown output
    markdown_output = format_as_markdown(project_file_name, layers_data, layer_tree, legend_config)
    
    if output_file_path:
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            print(f"📋 Wiki documentation successfully written to {output_file_path}")
        except IOError as e:
            print(f"Error: Could not write to output file {output_file_path}. {e}", file=sys.stderr)
    else:
        print(markdown_output)

    # Generate sidebar if requested
    if sidebar_path:
        sidebar_content = generate_wiki_sidebar(layers_data, layer_tree, project_name)
        try:
            with open(sidebar_path, 'w', encoding='utf-8') as f:
                f.write(sidebar_content)
            print(f"📁 Wiki sidebar successfully written to {sidebar_path}")
        except IOError as e:
            print(f"Error: Could not write to sidebar file {sidebar_path}. {e}", file=sys.stderr)

    if csv_output_path:
        csv_output = format_as_csv(layers_data)
        if csv_output:
            try:
                with open(csv_output_path, 'w', encoding='utf-8', newline='') as f:
                    f.write(csv_output)
                print(f"📊 CSV data successfully written to {csv_output_path}")
            except IOError as e:
                print(f"Error: Could not write to CSV output file {csv_output_path}. {e}", file=sys.stderr)
        else:
            print("No data to write to CSV.")

if __name__ == "__main__":
    main()