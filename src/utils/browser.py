"""
Browser Utilities Module

Handles opening HTML files in the default browser.
"""

from pathlib import Path
import webbrowser
import os


def open_html_in_browser(file_path: Path) -> bool:
    """
    Open HTML file in default browser.
    
    Parameters
    ----------
    file_path : Path
        Path to HTML file
    
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    if not file_path.exists():
        print(f"Warning: HTML file not found: {file_path}")
        return False
    
    try:
        # Convert to absolute path
        abs_path = file_path.resolve()
        
        # Convert to file:// URL
        file_url = f"file:///{abs_path.as_posix()}"
        
        # Open in default browser
        webbrowser.open(file_url)
        
        return True
    
    except Exception as e:
        print(f"Warning: Could not open HTML file in browser: {e}")
        print(f"  File path: {file_path}")
        print(f"  Please open manually: {file_path}")
        return False


def get_browser_command() -> str:
    """
    Get the command to open the default browser.
    
    Returns
    -------
    str
        Browser command or URL
    """
    try:
        # Try to get default browser
        browser = webbrowser.get()
        return str(browser)
    except Exception:
        return "default browser"


if __name__ == "__main__":
    """Debug and test browser opening."""
    import sys
    
    print("""============================================================
Browser Utilities - Debug Mode
============================================================""")
    
    # Test with a sample file
    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "data" / "processed" / "suitability_map.html"
    
    if test_file.exists():
        print(f"\nTest file found: {test_file}")
        print("Attempting to open in browser...")
        
        success = open_html_in_browser(test_file)
        if success:
            print("PASS: Successfully opened HTML file in browser")
        else:
            print("FAIL: Could not open HTML file in browser")
    else:
        print(f"\nTest file not found: {test_file}")
        print("Please create a test HTML file first")
    
    print(f"""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.utils.browser import open_html_in_browser
  from pathlib import Path
  
  html_file = Path('data/processed/suitability_map.html')
  open_html_in_browser(html_file)
------------------------------------------------------------""")

