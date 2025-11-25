"""
Optional: Check Google Earth Engine Export Task Status (Template)

NOTE: This script is OPTIONAL and is a TEMPLATE. Data acquisition is done manually outside the codebase.
GeoTIFF files should be manually placed in data/ directory (flat structure).

This script is a TEMPLATE that can be used to check GEE export task status if needed,
but it is NOT FUNCTIONAL until you provide credentials in configs/config.yaml.

See src/data/acquisition/README_TEMPLATE.md for setup instructions.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ee
from src.data_acquisition.gee_loader import GEEDataLoader


def check_task_status(task_ids=None):
    """Check status of export tasks. If task_ids provided, only check those."""
    print("=" * 70)
    print("Checking GEE Export Task Status")
    print("=" * 70)
    
    try:
        loader = GEEDataLoader()
        loader.initialize()
        
        all_tasks = ee.batch.Task.list()
        
        if task_ids:
            # Check specific tasks
            print(f"\nChecking {len(task_ids)} specific task(s)...")
            print("-" * 70)
            tasks_to_check = []
            for task_id in task_ids:
                for task in all_tasks:
                    if task.id == task_id:
                        tasks_to_check.append(task)
                        break
        else:
            # Check all tasks (first 20)
            tasks_to_check = all_tasks[:20]
            print(f"\nFound {len(all_tasks)} task(s) (showing first 20)")
        
        if not tasks_to_check:
            print("\nNo tasks found.")
            return
        
        print("\nTask Status:")
        print("-" * 70)
        
        completed = running = failed = ready = 0
        
        for task in tasks_to_check:
            state = task.state
            task_id = task.id
            description = task.config.get('description', 'N/A')
            
            if state == 1:
                status = "READY"
                ready += 1
            elif state == 2:
                status = "RUNNING"
                running += 1
            elif state == 3:
                status = "COMPLETED"
                completed += 1
            elif state == 4:
                status = "FAILED"
                failed += 1
                error = task.config.get('error_message', 'No error message')
                print(f"  {status:10} | {task_id} | {description[:50]}")
                print(f"    Error: {error[:100]}")
                continue
            elif state == 5:
                status = "CANCELLED"
            else:
                status = f"UNKNOWN ({state})"
            
            print(f"  {status:10} | {task_id} | {description[:50]}")
        
        print("-" * 70)
        if not task_ids:
            print(f"\nSummary:")
            print(f"  Completed: {completed}")
            print(f"  Running:   {running}")
            print(f"  Ready:     {ready}")
            print(f"  Failed:    {failed}")
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_task_status()

