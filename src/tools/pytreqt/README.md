# pytreqt - MOVED TO STANDALONE PACKAGE

⚠️ **This directory is deprecated** ⚠️

pytreqt has been extracted into a standalone package and is now available as a separate PyPI package.

## New Location

- **Repository**: https://github.com/joernpreuss/pytreqt
- **Package**: `pip install pytreqt`
- **CLI**: `pytreqt --help`

## Migration for SAVT

SAVT now uses the standalone pytreqt package:
- ✅ **Dependencies**: Added `pytreqt` to development dependencies
- ✅ **Configuration**: Uses `pytreqt.toml` in project root
- ✅ **pytest integration**: Updated to `-p pytreqt` in pyproject.toml

## Usage in SAVT

```bash
# View requirements coverage
uv run pytest -v
pytreqt show

# Generate reports
pytreqt coverage
pytreqt stats

# Configuration
pytreqt config
```

See the standalone pytreqt documentation for full details.

---

This embedded version will be removed in a future cleanup.
