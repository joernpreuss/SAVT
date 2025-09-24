# VS Code Python Development Issues

## Issue 1: Import Resolution Errors

### Problem
Pylance shows "Import could not be resolved" errors for relative imports in src-layout projects.

### Solution

#### Option A: Disable Pylance (Recommended)
1. Open VS Code Extensions panel (Cmd+Shift+X)
2. Search for "Pylance" and click "Disable"
3. Update `.vscode/settings.json`:
```json
{
  "python.languageServer": "None",
  "python.linting.mypyEnabled": true,
  "python.linting.enabled": true,
  "pylance.enable": false,
  "python.analysis.disabled": true
}
```
4. Use mypy for type checking and Ruff for formatting/linting

#### Option B: Alternative Language Servers
If you prefer to keep a language server:

**Python LSP Server:**
```json
{
  "python.languageServer": "Pylsp"
}
```

**Jedi:**
```json
{
  "python.languageServer": "Jedi"
}
```

### Why This Happens
Pylance has difficulty resolving relative imports in src-layout projects with complex package structures.

---

## Issue 2: Phantom .git Files

### Problem
VS Code/Pylance shows type errors for phantom files with `.git` extension (e.g., `qa.py.git`) that don't actually exist in the filesystem.

### Solution

#### 1. Update VS Code Settings (Aggressive Exclusions)
Add to `.vscode/settings.json`:
```json
{
  "files.exclude": {
    "**/*.git": true,
    "**/.git/**": true,
    "**/qa.py.git": true
  },
  "python.analysis.exclude": [
    "**/*.git",
    "**/.git/**",
    "**/qa.py.git"
  ],
  "python.analysis.ignore": [
    "**/*.git",
    "**/qa.py.git"
  ],
  "search.exclude": {
    "**/*.git": true,
    "**/.git/**": true,
    "**/qa.py.git": true
  },
  "files.watcherExclude": {
    "**/*.git": true,
    "**/.git/**": true
  }
}
```

#### 2. Clear VS Code Caches
```bash
# Clear main VS Code caches
rm -rf ~/Library/Caches/com.microsoft.VSCode* ~/Library/Caches/Code

# Clear Python language server caches
rm -rf ~/.cache/pylsp* ~/.cache/python* ~/.cache/microsoft 2>/dev/null || true
```

#### 3. Force Pylance Index Rebuild
If issues persist:
1. Close VS Code completely
2. Disable and re-enable Python extension:
   - `Cmd+Shift+P` → "Extensions: Disable" → search "Python"
   - Restart VS Code
   - `Cmd+Shift+P` → "Extensions: Enable" → search "Python"
3. Or: `Cmd+Shift+P` → "Python: Select Interpreter" and reselect

#### 4. Quick Fixes
Try in order:
1. `Cmd+Shift+P` → "Python: Restart Language Server"
2. `Cmd+Shift+P` → "Python: Clear Cache and Reload Window"
3. `Cmd+Shift+P` → "Developer: Reload Window"

### Root Cause
Pylance's workspace indexing gets corrupted and references temporary git-related files created during diff operations.

---

## Issue 3: F2/F12 (Go to Definition, Rename) Not Working

### Problem
F2 (rename symbol) and F12 (go to definition) stop working in VS Code.

### Solution
This is usually caused by the Python language server being disabled.

1. **Check Python language server setting:**
   - Press `Ctrl+,` (or `Cmd+,`) to open Settings
   - Search for "python language server"
   - Ensure it's set to "Pylance" (not "None")

2. **Or edit settings JSON directly:**
   - Press `Ctrl+Shift+P`, type "Preferences: Open Settings (JSON)"
   - Change `"python.languageServer": "None"` to `"python.languageServer": "Pylance"`

3. **Verify Pylance is installed and enabled:**
   - Press `Ctrl+Shift+X` to open Extensions
   - Search for "Pylance" and ensure it's installed and enabled

4. **Restart language server:**
   - Press `Ctrl+Shift+P`, type "Pylance: Restart Server"

### Root Cause
The setting `"python.languageServer": "None"` completely disables language server features including F2/F12 functionality.

---

## Language Server Alternatives

If Pylance issues persist, consider switching:

### Option 1: Jedi (Lightweight)
```json
{
  "python.languageServer": "Jedi"
}
```

### Option 2: Python LSP Server
```json
{
  "python.languageServer": "Pylsp"
}
```

### Option 3: Standalone Pyright
1. Install "Pyright" extension
2. Set `"python.languageServer": "None"`

### Option 4: BasedPyright (Community Fork)
1. Install "BasedPyright" extension
2. Set `"python.languageServer": "None"`

### Trade-offs
- **Jedi**: Lighter, fewer features but very stable
- **Pylsp**: Good middle ground with plugin ecosystem
- **Pyright**: Same features as Pylance but potentially more stable
- **BasedPyright**: Community-maintained, often has faster bug fixes

### Recommended Setup for This Project
Based on current configuration:
```json
{
  "python.languageServer": "None",
  "python.linting.mypyEnabled": true,
  "python.linting.ruffEnabled": true,
  "pylance.enable": false,
  "python.analysis.disabled": true
}
```
This uses mypy for type checking and Ruff for formatting/linting without language server complications.
