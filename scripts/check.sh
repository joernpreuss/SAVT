#!/bin/bash
set -e

echo "🔍 Running linter..."
uv tool run ruff check src/ tests/

echo "✨ Running formatter..."
uv tool run ruff format src/ tests/ --check

echo "🔎 Running type checker..."
uv tool run mypy src/

echo "🧪 Running tests..."
uv run pytest

echo "✅ All checks passed!"