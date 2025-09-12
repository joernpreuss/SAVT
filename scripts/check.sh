#!/bin/bash
set -e

echo "🔍 Running linter..."
uv tool run ruff check src/ tests/
echo

echo "✨ Running formatter..."
uv tool run ruff format src/ tests/ --check
echo

echo "🔎 Running type checker..."
uv tool run mypy src/
echo

echo "🧪 Running tests..."
uv run pytest
echo

echo "✅ All checks passed!"
echo

