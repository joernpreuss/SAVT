# SAVT
Pure Python Suggestion And Veto Tool

## Overview
SAVT is a collaborative decision-making tool originally designed as a proof of concept for ordering pizza together. The system allows users to:

- Create **objects** (like pizzas or any item requiring group decisions)
- Suggest **properties** for those objects (like toppings: salami, mushrooms, extra cheese)
- **Veto** properties they don't want, enabling democratic consensus-building

While initially built for pizza ordering, the flexible object-property model makes it suitable for any group decision-making scenario where suggestions and vetoes help reach consensus.

## Start
- Python version is pinned to 3.12 via `.python-version` to ensure consistent behavior across development environments and match the pyproject.toml requirement (~=3.12.0)

### Run test server
- `uv run uvicorn src.main:app --reload --host 0.0.0.0`
  
### Run tests
- `uv run pytest`
