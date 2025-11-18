#!/usr/bin/env python
"""
Wrapper script to ensure dependencies are installed before running the analysis pipeline.
This is used by Streamlit Cloud where dependencies might not be available in subprocess.

This script installs PyYAML if missing, then imports and runs main() directly
(not via subprocess) to ensure all imports happen in the same environment.
"""
import sys
import subprocess
from pathlib import Path

# Ensure PyYAML is installed BEFORE any other imports
try:
    import yaml
except ImportError:
    print("Installing PyYAML...", file=sys.stderr, flush=True)
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "pyyaml>=6.0", 
            "--quiet", "--disable-pip-version-check", "--user"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # Try importing again
        import yaml
        print("PyYAML installed successfully.", file=sys.stderr, flush=True)
    except (subprocess.CalledProcessError, ImportError) as e:
        print(f"Failed to install/import PyYAML: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

# Add project root (two levels up from this script) to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Now import and run main() directly (not via subprocess)
# This ensures all imports happen in the same Python process where we installed PyYAML
if __name__ == "__main__":
    # Import main function
    from src.main import main
    
    # Call main() - it will parse sys.argv and handle everything
    exit_code = main()
    sys.exit(exit_code)

