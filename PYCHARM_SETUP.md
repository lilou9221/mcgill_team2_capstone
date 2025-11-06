# PyCharm Configuration Guide - Residual_Carbon

## Resolving "Unresolved Reference" Errors

If you're seeing "unresolved reference" errors for `src` imports in PyCharm, follow these steps:

## Solution 1: Mark Project Root as Source Root (Recommended)

1. **Open PyCharm Settings:**
   - File → Settings (Windows/Linux) or PyCharm → Preferences (Mac)
   - Or press `Ctrl+Alt+S` (Windows/Linux) or `Cmd+,` (Mac)

2. **Navigate to Project Structure:**
   - Go to: Project → Project Structure

3. **Mark Residual_Carbon as Source Root:**
   - Select the `Residual_Carbon` folder in the directory tree
   - Click the "Sources" button (or right-click → Mark Directory as → Sources Root)
   - The folder should turn blue, indicating it's a source root

4. **Apply and Close:**
   - Click "Apply" and then "OK"

PyCharm should now recognize imports like `from src.data.gee_loader import GEEDataLoader`.

## Solution 2: Install Package in Editable Mode (Alternative)

If marking as source root doesn't work, you can install the package in editable mode:

1. **Open Terminal in PyCharm:**
   - View → Tool Windows → Terminal
   - Or press `Alt+F12`

2. **Navigate to project root:**
   ```bash
   cd C:\Users\lilou\PycharmProjects\PythonProject\Residual_Carbon
   ```

3. **Install in editable mode:**
   ```bash
   pip install -e .
   ```

   This installs the package in "editable" mode, so changes to source files are immediately reflected.

4. **Restart PyCharm:**
   - File → Invalidate Caches / Restart → Invalidate and Restart

## Solution 3: Configure Python Path (If still not working)

1. **Open Run/Debug Configurations:**
   - Run → Edit Configurations...
   - Or click the dropdown next to the run button

2. **Edit Python Interpreter:**
   - Select your Python interpreter
   - In "Environment variables" section, add:
     ```
     PYTHONPATH=C:\Users\lilou\PycharmProjects\PythonProject\Residual_Carbon
     ```

3. **Apply and Close**

## Solution 4: Verify Project Interpreter

1. **Check Python Interpreter:**
   - File → Settings → Project → Python Interpreter
   - Make sure the correct interpreter is selected (the one with your virtual environment)

2. **Verify Interpreter Path:**
   - Ensure it's pointing to your virtual environment if you're using one
   - Example: `C:\Users\lilou\PycharmProjects\PythonProject\Residual_Carbon\venv\Scripts\python.exe`

## Verification

After applying any solution, verify it works:

1. **Open `src/main.py`**
2. **Check if the imports are resolved:**
   - `from src.data.gee_loader import GEEDataLoader` should not show red squiggly lines
3. **Try running the code:**
   ```bash
   python src/main.py --help
   ```

## Common Issues

### Issue: "Config file not found" when running in PyCharm

**Solution:**
- **This has been fixed!** The code now resolves relative paths relative to the project root, not the working directory
- **If you still see this error:**
  1. Check that `configs/config.yaml` exists in the project root
  2. Set the working directory in Run Configuration:
     - Run → Edit Configurations...
     - Select your run configuration
     - Set "Working directory" to: `C:\Users\lilou\PycharmProjects\PythonProject\Residual_Carbon`
     - Or use: `$PROJECT_DIR$` (PyCharm variable)
  3. The code should now work regardless of working directory

### Issue: Still seeing unresolved references after marking as source root

**Solution:**
- Invalidate caches: File → Invalidate Caches → Invalidate and Restart
- Make sure you marked the `Residual_Carbon` folder, not the `src` folder
- Check that `.idea` folder exists (PyCharm project folder)

### Issue: Python path is correct but imports still fail

**Solution:**
- Close and reopen PyCharm
- Check that `__init__.py` files exist in all package directories:
  - `src/__init__.py` [OK]
  - `src/data/__init__.py` [OK]
  - `src/utils/__init__.py` [OK]
  - `src/analysis/__init__.py` [OK]
  - `src/visualization/__init__.py` [OK]

### Issue: Works in terminal but not in PyCharm

**Solution:**
- PyCharm might be using a different Python interpreter
- Check: File → Settings → Project → Python Interpreter
- Make sure it matches your terminal's Python interpreter

## Quick Fix Checklist

- [ ] Mark `Residual_Carbon` folder as Sources Root
- [ ] Verify Python interpreter is correct
- [ ] Check that all `__init__.py` files exist
- [ ] Invalidate caches and restart PyCharm
- [ ] If still not working, try `pip install -e .` in terminal

## Still Having Issues?

If none of these solutions work:

1. **Check PyCharm version:** Make sure you're using a recent version (2021.1+)
2. **Check project structure:** Ensure your project structure matches the expected layout
3. **Try creating a new PyCharm project:** File → New → Project from Existing Sources
4. **Check for conflicting Python installations:** Make sure there's only one Python interpreter active
