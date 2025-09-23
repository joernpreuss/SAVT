# VSCode Phantom .git Files Issue

## Problem
VSCode/Pylance shows type errors for phantom files with `.git` extension (e.g., `qa.py.git`) that don't actually exist in the filesystem. These are likely temporary git-related files created by VSCode's git integration that Pylance incorrectly tries to analyze.

## Solution

### 1. Update VSCode Settings (Aggressive Exclusions)
Add the following to `.vscode/settings.json`:

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

### 2. Clear VSCode Caches
Run these commands to clear all VSCode and Pylance caches:

```bash
# Clear main VSCode caches
rm -rf ~/Library/Caches/com.microsoft.VSCode* ~/Library/Caches/Code

# Clear Python language server caches (if they exist)
rm -rf ~/.cache/pylsp* ~/.cache/python* ~/.cache/microsoft 2>/dev/null || true
```

### 3. Nuclear Option: Force Pylance Index Rebuild
If the issue persists after steps 1-2, try this:

1. **Close VSCode completely**
2. **Disable and re-enable Python extension**:
   - Open VSCode
   - `Cmd+Shift+P` → "Extensions: Disable" → search "Python" → disable
   - **Restart VSCode**
   - `Cmd+Shift+P` → "Extensions: Enable" → search "Python" → enable
3. **Alternatively**: `Cmd+Shift+P` → "Python: Select Interpreter" and reselect your interpreter

This forces Pylance to rebuild its entire index from scratch, clearing any phantom file references.

### 4. Quick Fixes (for minor cases)
Try these in order if you don't want the nuclear option:
1. `Cmd+Shift+P` → "Python: Restart Language Server"
2. `Cmd+Shift+P` → "Python: Clear Cache and Reload Window"
3. `Cmd+Shift+P` → "Developer: Reload Window"

## Root Cause
This issue occurs when Pylance's workspace indexing gets corrupted and references temporary git-related files that VSCode's git integration creates during diff operations. The aggressive exclusions and index rebuild prevent this from happening.

## Last Resort: Switch Language Server
If the phantom `.git` files keep coming back despite all the above steps, this is likely a persistent Pylance bug. **Switch to a different Python language server**:

### Option 1: Jedi Language Server (Lightweight)
Add to `.vscode/settings.json`:
```json
{
  "python.languageServer": "Jedi"
}
```

### Option 2: Install Standalone Pyright Extension
1. Install the "Pyright" extension from the marketplace
2. Disable the Python extension's built-in language server:
   ```json
   {
     "python.languageServer": "None"
   }
   ```

### Option 3: BasedPyright (Community Fork)
1. Install "BasedPyright" extension
2. Disable Python extension's language server as above

### Option 4: Python LSP Server
```json
{
  "python.languageServer": "Pylsp"
}
```

**After switching**: Restart VSCode completely. The phantom file issues should disappear since you're no longer using Pylance's indexing system.

## Trade-offs
- **Jedi**: Lighter, fewer features but very stable
- **Pyright**: Same features as Pylance but potentially more stable
- **BasedPyright**: Community-maintained, often has bug fixes faster
- **Pylsp**: Good middle ground with plugin ecosystem

## Prevention
The comprehensive exclusion settings in step 1 should prevent this issue from recurring if you stick with Pylance. However, switching language servers is often the most reliable long-term solution for this particular bug.
