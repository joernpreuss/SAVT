#!/bin/bash
# Development server launcher for SAVT using uv with SQLite
# Clear shell environment variables - .env file is source of truth
unset DATABASE_URL
unset OBJECT_NAME_SINGULAR
unset PROPERTY_NAME_SINGULAR
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
