"""
Retry Export Tasks

Retries export tasks for SMAP datasets. Reuses GEEDataLoader from the main pipeline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.acquisition.gee_loader import GEEDataLoader


def retry_exports(selected_layers=None):
    """Retry export tasks for specified layers (default: SMAP datasets)."""
    if selected_layers is None:
        selected_layers = ['soil_moisture', 'soil_temperature']
    
    print("=" * 70)
    print("Retrying Export Tasks")
    print("=" * 70)
    
    try:
        loader = GEEDataLoader()
        loader.initialize()
        loader.load_datasets(downscale_smap=True)
        loader.clip_to_mato_grosso()
        loader.create_export_tasks(selected_layers=selected_layers)
        task_ids = loader.start_export_tasks()
        
        print(f"\n[SUCCESS] Started {len(task_ids)} export task(s)")
        print("\nTask IDs:")
        for i, task_id in enumerate(task_ids, 1):
            print(f"  {i}. {task_id}")
        print("\nMonitor at: https://code.earthengine.google.com/")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = retry_exports()
    sys.exit(0 if success else 1)

