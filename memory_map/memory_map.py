"""
Data Flow Memory Map for Residual Carbon Project

This script generates a comprehensive flowchart showing the data flow
for all maps generated in the Residual Carbon project.

The flowchart uses:
- Rectangular boxes for files/data
- Rounded boxes for processes/functions
- Arrows to show data flow direction
"""

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    MATPLOTLIB_AVAILABLE = False
    print(f"Warning: matplotlib not available: {e}")
    print("Please install matplotlib: pip install matplotlib")
    print("Or install all requirements: pip install -r requirements.txt")

def create_data_flow_diagram():
    """
    Create a comprehensive data flow diagram for all maps in the Residual Carbon project.
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required to generate the diagram. "
                         "Install it with: pip install matplotlib")
    
    fig, ax = plt.subplots(1, 1, figsize=(28, 18))
    ax.set_xlim(0, 28)
    ax.set_ylim(0, 18)
    ax.axis('off')
    
    # Define colors
    file_color = '#E8F4F8'  # Light blue for files
    process_color = '#FFF4E6'  # Light orange for processes
    map_color = '#E8F5E9'  # Light green for final maps
    edge_color = '#333333'
    
    # Font sizes
    title_font = 20
    label_font = 10
    small_font = 9
    
    # Title
    ax.text(14, 17, 'Residual Carbon - Data Flow Memory Map', 
            ha='center', va='center', fontsize=title_font, fontweight='bold')
    ax.text(14, 16.2, 'All Maps Data Flow Diagram', 
            ha='center', va='center', fontsize=13, style='italic')
    
    # Legend
    legend_y = 16.5
    legend_x = 0.8
    legend_box_width = 1.0
    legend_box_height = 0.4
    
    # File box (rectangle)
    file_box = FancyBboxPatch((legend_x, legend_y - legend_box_height/2), legend_box_width, legend_box_height, 
                              boxstyle="round,pad=0.05", 
                              facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(file_box)
    ax.text(legend_x + legend_box_width/2, legend_y, 'File/Data', 
            ha='center', va='center', fontsize=small_font, fontweight='bold')
    
    # Process box (rounded)
    process_box = FancyBboxPatch((legend_x + 1.3, legend_y - legend_box_height/2), legend_box_width, legend_box_height, 
                                 boxstyle="round,pad=0.05", 
                                 facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(process_box)
    ax.text(legend_x + 1.3 + legend_box_width/2, legend_y, 'Process', 
            ha='center', va='center', fontsize=small_font, fontweight='bold')
    
    # Map box (rounded, different color)
    map_box = FancyBboxPatch((legend_x + 2.6, legend_y - legend_box_height/2), legend_box_width, legend_box_height, 
                             boxstyle="round,pad=0.05", 
                             facecolor=map_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map_box)
    ax.text(legend_x + 2.6 + legend_box_width/2, legend_y, 'Map Output', 
            ha='center', va='center', fontsize=small_font, fontweight='bold')
    
    # ===================================================================
    # COLUMN-BASED LAYOUT: Steps progress left to right
    # ===================================================================
    
    # Box dimensions
    file_box_width = 2.8
    file_box_height = 1.0
    process_box_width = 2.8
    process_box_height = 0.9
    column_spacing = 3.5  # Horizontal spacing between columns
    vertical_spacing = 1.5  # Vertical spacing for parallel paths
    
    # Column positions (x coordinates)
    col1_x = 1.0  # Raw data
    col2_x = col1_x + column_spacing  # Clipping
    col3_x = col2_x + column_spacing  # Convert to DataFrames
    col4_x = col3_x + column_spacing  # H3 indexing
    col5_x = col4_x + column_spacing  # Merge & Aggregate
    col6_x = col5_x + column_spacing  # Calculate Scores
    col7_x = col6_x + column_spacing  # Map Generation
    
    # Center Y position for main pipeline
    center_y = 10
    
    # Column 1: Raw Data
    raw_data_box = FancyBboxPatch((col1_x, center_y - file_box_height/2), file_box_width, file_box_height, 
                                   boxstyle="round,pad=0.1", 
                                   facecolor=file_color, edgecolor=edge_color, linewidth=2)
    ax.add_patch(raw_data_box)
    ax.text(col1_x + file_box_width/2, center_y, 'Raw GeoTIFF Files\n(data/raw/*.tif)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    # Column 2: Optional Clipping
    clip_process = FancyBboxPatch((col2_x, center_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(clip_process)
    ax.text(col2_x + process_box_width/2, center_y, 'clip_all_rasters_to_circle\n(raster_clip.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from col1 to col2
    arrow1 = FancyArrowPatch((col1_x + file_box_width, center_y), 
                            (col2_x, center_y),
                            arrowstyle='->', mutation_scale=20, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow1)
    
    # Clipped rasters output (below process)
    clipped_box = FancyBboxPatch((col2_x, center_y - process_box_height/2 - vertical_spacing - file_box_height/2), 
                                 file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(clipped_box)
    ax.text(col2_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing, 
            'Clipped GeoTIFFs\n(temp directory)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from clip process to clipped
    arrow1b = FancyArrowPatch((col2_x + process_box_width/2, center_y - process_box_height/2), 
                             (col2_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing + file_box_height/2),
                             arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow1b)
    
    # Column 3: Convert to DataFrames
    convert_process = FancyBboxPatch((col3_x, center_y - process_box_height/2), process_box_width, process_box_height, 
                                     boxstyle="round,pad=0.1", 
                                     facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(convert_process)
    ax.text(col3_x + process_box_width/2, center_y, 'convert_all_rasters_to_dataframes\n(raster_to_csv.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from clipped to convert
    arrow2 = FancyArrowPatch((col2_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                            (col3_x, center_y),
                            arrowstyle='->', mutation_scale=20, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow2)
    
    # DataFrames output
    df_box = FancyBboxPatch((col3_x, center_y - process_box_height/2 - vertical_spacing - file_box_height/2), 
                           file_box_width, file_box_height, 
                           boxstyle="round,pad=0.1", 
                           facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(df_box)
    ax.text(col3_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing, 
            'DataFrames\n(lon, lat, value)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from convert to df
    arrow2b = FancyArrowPatch((col3_x + process_box_width/2, center_y - process_box_height/2), 
                             (col3_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing + file_box_height/2),
                             arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow2b)
    
    # Column 4: Add H3 Indexes
    h3_process = FancyBboxPatch((col4_x, center_y - process_box_height/2), process_box_width, process_box_height, 
                               boxstyle="round,pad=0.1", 
                               facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(h3_process)
    ax.text(col4_x + process_box_width/2, center_y, 'process_dataframes_with_h3\n(h3_converter.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from df to h3
    arrow3 = FancyArrowPatch((col3_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                            (col4_x, center_y),
                            arrowstyle='->', mutation_scale=20, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow3)
    
    # H3-indexed DataFrames
    h3_df_box = FancyBboxPatch((col4_x, center_y - process_box_height/2 - vertical_spacing - file_box_height/2), 
                               file_box_width, file_box_height, 
                               boxstyle="round,pad=0.1", 
                               facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(h3_df_box)
    ax.text(col4_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing, 
            'DataFrames with H3\n(lon, lat, value, h3_index)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from h3 process to h3 df
    arrow3b = FancyArrowPatch((col4_x + process_box_width/2, center_y - process_box_height/2), 
                             (col4_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing + file_box_height/2),
                             arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow3b)
    
    # Column 5: Merge and Aggregate
    merge_process = FancyBboxPatch((col5_x, center_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(merge_process)
    ax.text(col5_x + process_box_width/2, center_y, 'merge_and_aggregate_soil_data\n(suitability.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from h3 df to merge
    arrow4 = FancyArrowPatch((col4_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                            (col5_x, center_y),
                            arrowstyle='->', mutation_scale=20, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow4)
    
    # Merged data
    merged_box = FancyBboxPatch((col5_x, center_y - process_box_height/2 - vertical_spacing - file_box_height/2), 
                               file_box_width, file_box_height, 
                               boxstyle="round,pad=0.1", 
                               facecolor=file_color, edgecolor=edge_color, linewidth=2)
    ax.add_patch(merged_box)
    ax.text(col5_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing, 
            'merged_soil_data.csv\n(aggregated by H3)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    # Arrow from merge to merged
    arrow4b = FancyArrowPatch((col5_x + process_box_width/2, center_y - process_box_height/2), 
                             (col5_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing + file_box_height/2),
                             arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow4b)
    
    # Column 6: Calculate Suitability Scores
    score_process = FancyBboxPatch((col6_x, center_y - process_box_height/2), process_box_width, process_box_height, 
                                   boxstyle="round,pad=0.1", 
                                   facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(score_process)
    ax.text(col6_x + process_box_width/2, center_y, 'calculate_biochar_suitability_scores\n(biochar_suitability.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from merged to score
    arrow5 = FancyArrowPatch((col5_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                            (col6_x, center_y),
                            arrowstyle='->', mutation_scale=20, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow5)
    
    # Suitability scores
    scores_box = FancyBboxPatch((col6_x, center_y - process_box_height/2 - vertical_spacing - file_box_height/2), 
                               file_box_width, file_box_height, 
                               boxstyle="round,pad=0.1", 
                               facecolor=file_color, edgecolor=edge_color, linewidth=2)
    ax.add_patch(scores_box)
    ax.text(col6_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing, 
            'suitability_scores.csv\n(biochar scores)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    # Arrow from score to scores
    arrow5b = FancyArrowPatch((col6_x + process_box_width/2, center_y - process_box_height/2), 
                             (col6_x + file_box_width/2, center_y - process_box_height/2 - vertical_spacing + file_box_height/2),
                             arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow5b)
    
    # ===================================================================
    # MAP GENERATION (Column 7 - Rightmost)
    # Maps branch from their data sources
    # ===================================================================
    
    col8_x = col7_x + column_spacing  # Final map outputs
    
    # Map vertical positions (stacked)
    map_y_spacing = 1.8
    map1_y = center_y + 2.5
    map2_y = center_y + 0.5
    map3_y = center_y - 1.5
    map4_y = center_y - 3.5
    map5_y = center_y - 5.5
    
    # 1. Biochar Suitability Map (from suitability_scores.csv)
    map1_process = FancyBboxPatch((col7_x, map1_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map1_process)
    ax.text(col7_x + process_box_width/2, map1_y, 'create_biochar_suitability_map\n(biochar_map.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from scores to map1
    arrow_map1 = FancyArrowPatch((col6_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                                (col7_x, map1_y),
                                arrowstyle='->', mutation_scale=20, linewidth=2, 
                                color='#2E7D32', connectionstyle="arc3,rad=0.1")
    ax.add_patch(arrow_map1)
    
    map1_output = FancyBboxPatch((col8_x, map1_y - file_box_height/2), file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=map_color, edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(map1_output)
    ax.text(col8_x + file_box_width/2, map1_y, 'suitability_map.html\n(Biochar Suitability)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    arrow_map1b = FancyArrowPatch((col7_x + process_box_width, map1_y), 
                                 (col8_x, map1_y),
                                 arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow_map1b)
    
    # 2. SOC Map (from merged_soil_data.csv)
    map2_process = FancyBboxPatch((col7_x, map2_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map2_process)
    ax.text(col7_x + process_box_width/2, map2_y, 'create_soc_map\n(soc_map.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from merged to map2
    arrow_map2 = FancyArrowPatch((col5_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                                (col7_x, map2_y),
                                arrowstyle='->', mutation_scale=20, linewidth=2, 
                                color='#1976D2', connectionstyle="arc3,rad=0.1")
    ax.add_patch(arrow_map2)
    
    map2_output = FancyBboxPatch((col8_x, map2_y - file_box_height/2), file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=map_color, edgecolor='#1976D2', linewidth=2)
    ax.add_patch(map2_output)
    ax.text(col8_x + file_box_width/2, map2_y, 'soc_map.html\n(Soil Organic Carbon)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    arrow_map2b = FancyArrowPatch((col7_x + process_box_width, map2_y), 
                                 (col8_x, map2_y),
                                 arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow_map2b)
    
    # 3. pH Map (from merged_soil_data.csv)
    map3_process = FancyBboxPatch((col7_x, map3_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map3_process)
    ax.text(col7_x + process_box_width/2, map3_y, 'create_ph_map\n(ph_map.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from merged to map3
    arrow_map3 = FancyArrowPatch((col5_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                                (col7_x, map3_y),
                                arrowstyle='->', mutation_scale=20, linewidth=2, 
                                color='#F57C00', connectionstyle="arc3,rad=0.05")
    ax.add_patch(arrow_map3)
    
    map3_output = FancyBboxPatch((col8_x, map3_y - file_box_height/2), file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=map_color, edgecolor='#F57C00', linewidth=2)
    ax.add_patch(map3_output)
    ax.text(col8_x + file_box_width/2, map3_y, 'ph_map.html\n(Soil pH)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    arrow_map3b = FancyArrowPatch((col7_x + process_box_width, map3_y), 
                                 (col8_x, map3_y),
                                 arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow_map3b)
    
    # 4. Moisture Map (from merged_soil_data.csv)
    map4_process = FancyBboxPatch((col7_x, map4_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map4_process)
    ax.text(col7_x + process_box_width/2, map4_y, 'create_moisture_map\n(moisture_map.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrow from merged to map4
    arrow_map4 = FancyArrowPatch((col5_x + file_box_width, center_y - process_box_height/2 - vertical_spacing), 
                                (col7_x, map4_y),
                                arrowstyle='->', mutation_scale=20, linewidth=2, 
                                color='#0288D1', connectionstyle="arc3,rad=-0.05")
    ax.add_patch(arrow_map4)
    
    map4_output = FancyBboxPatch((col8_x, map4_y - file_box_height/2), file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=map_color, edgecolor='#0288D1', linewidth=2)
    ax.add_patch(map4_output)
    ax.text(col8_x + file_box_width/2, map4_y, 'moisture_map.html\n(Soil Moisture)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    arrow_map4b = FancyArrowPatch((col7_x + process_box_width, map4_y), 
                                 (col8_x, map4_y),
                                 arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow_map4b)
    
    # 5. Investor Crop Area Map (separate data sources - starts at col1)
    # Data sources in column 1 (below raw data)
    boundaries_y = center_y - 4.5
    boundaries_box = FancyBboxPatch((col1_x, boundaries_y - file_box_height/2), file_box_width, file_box_height, 
                                    boxstyle="round,pad=0.1", 
                                    facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(boundaries_box)
    ax.text(col1_x + file_box_width/2, boundaries_y, 'Municipality\nBoundaries\n(GPKG/SHP)', 
            ha='center', va='center', fontsize=label_font)
    
    crop_data_y = boundaries_y - vertical_spacing
    crop_data_box = FancyBboxPatch((col1_x, crop_data_y - file_box_height/2), file_box_width, file_box_height, 
                                   boxstyle="round,pad=0.1", 
                                   facecolor=file_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(crop_data_box)
    ax.text(col1_x + file_box_width/2, crop_data_y, 'Crop Area CSV\n(Brazil_Municipality_\nCrop_Area_2024.csv)', 
            ha='center', va='center', fontsize=label_font)
    
    # Process in column 7
    map5_process = FancyBboxPatch((col7_x, map5_y - process_box_height/2), process_box_width, process_box_height, 
                                  boxstyle="round,pad=0.1", 
                                  facecolor=process_color, edgecolor=edge_color, linewidth=1.5)
    ax.add_patch(map5_process)
    ax.text(col7_x + process_box_width/2, map5_y, 'build_investor_waste_deck\n(municipality_waste_map.py)', 
            ha='center', va='center', fontsize=label_font)
    
    # Arrows from data sources to process
    arrow_map5a = FancyArrowPatch((col1_x + file_box_width, boundaries_y), 
                                 (col7_x, map5_y),
                                 arrowstyle='->', mutation_scale=20, linewidth=1.5, 
                                 color=edge_color, connectionstyle="arc3,rad=0.2")
    ax.add_patch(arrow_map5a)
    arrow_map5b = FancyArrowPatch((col1_x + file_box_width, crop_data_y), 
                                 (col7_x, map5_y),
                                 arrowstyle='->', mutation_scale=20, linewidth=1.5, 
                                 color=edge_color, connectionstyle="arc3,rad=0.2")
    ax.add_patch(arrow_map5b)
    
    map5_output = FancyBboxPatch((col8_x, map5_y - file_box_height/2), file_box_width, file_box_height, 
                                 boxstyle="round,pad=0.1", 
                                 facecolor=map_color, edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(map5_output)
    ax.text(col8_x + file_box_width/2, map5_y, 'investor_crop_area_map.html\n(Investor Crop Area)', 
            ha='center', va='center', fontsize=label_font, fontweight='bold')
    
    arrow_map5c = FancyArrowPatch((col7_x + process_box_width, map5_y), 
                                 (col8_x, map5_y),
                                 arrowstyle='->', mutation_scale=15, linewidth=1.5, color=edge_color)
    ax.add_patch(arrow_map5c)
    
    # ===================================================================
    # Additional annotations
    # ===================================================================
    
    # Note about Streamlit copies
    note_y = 1.5
    note_box = FancyBboxPatch((col1_x, note_y - 0.4), col8_x + file_box_width - col1_x, 0.8, 
                              boxstyle="round,pad=0.1", 
                              facecolor='#FFF9C4', edgecolor='#F9A825', linewidth=1.5)
    ax.add_patch(note_box)
    ax.text((col1_x + col8_x + file_box_width) / 2, note_y, 
            'Note: SOC, pH, and Moisture maps are also copied as *_streamlit.html for Streamlit app', 
            ha='center', va='center', fontsize=small_font, style='italic')
    
    # Output directory note
    output_note_y = 0.8
    ax.text((col1_x + col8_x + file_box_width) / 2, output_note_y, 
            'All HTML maps are saved to: output/html/', 
            ha='center', va='center', fontsize=small_font, style='italic', color='#666666')
    
    plt.tight_layout()
    return fig

def save_diagram(output_path='data_flow_memory_map.png', dpi=300):
    """
    Create and save the data flow diagram.
    
    Parameters
    ----------
    output_path : str
        Path to save the diagram
    dpi : int
        Resolution for the saved image
    """
    fig = create_data_flow_diagram()
    fig.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    print(f"Data flow diagram saved to: {output_path}")
    plt.close(fig)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Determine output path - save in the same directory as this script
    script_dir = Path(__file__).parent
    output_path = script_dir / "data_flow_memory_map.png"
    
    print("Generating data flow memory map...")
    save_diagram(str(output_path), dpi=300)
    print(f"\nDiagram saved successfully!")
    print(f"Location: {output_path}")
    print("\nThe diagram shows:")
    print("  - Rectangular boxes: Files and data")
    print("  - Rounded boxes: Processes and functions")
    print("  - Green rounded boxes: Final map outputs")
    print("  - Arrows: Data flow direction")

