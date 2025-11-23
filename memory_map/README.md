# Data Flow Memory Map

This folder contains standalone documentation showing the data flow for all maps generated in the Residual Carbon project.

## Files

- **memory_map.py**: Python script that generates the data flow diagram
- **data_flow_memory_map.png**: Generated flowchart showing the complete data pipeline

## Usage

To regenerate the diagram:

```bash
cd memory_map
python memory_map.py
```

## Diagram Description

The flowchart shows:
- **Rectangular boxes (light blue)**: Files and data
- **Rounded boxes (light orange)**: Processes and functions
- **Green rounded boxes**: Final map outputs (HTML maps)
- **Arrows**: Data flow direction

The diagram is organized in columns, with steps progressing from left to right:
1. Raw GeoTIFF files
2. Clipping process
3. Convert to DataFrames
4. H3 indexing
5. Merge & Aggregate
6. Calculate Scores
7. Map generation processes
8. Final HTML map outputs

## Note

This is standalone documentation and does not interfere with the main project code. It can be safely moved or modified without affecting the Residual Carbon application.

