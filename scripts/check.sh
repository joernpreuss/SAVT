#!/bin/bash
set -e

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "🔍 SAVT Code Quality Checker"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --fix     Auto-fix linting and formatting issues"
    echo "  --help    Show this help message"
    echo
    echo "Examples:"
    echo "  $0               # Run all checks"
    echo "  $0 --fix         # Run all checks and auto-fix issues"
    echo
    exit 0
fi

# Check if --fix option is provided
FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
    echo "🔧 Running in fix mode..."
    echo
fi

echo "✨ Running formatter..."
if [ "$FIX_MODE" = true ]; then
    uv tool run ruff format src/ tests/
else
    uv tool run ruff format src/ tests/ --check
fi
echo

echo "🔍 Running linter..."
if [ "$FIX_MODE" = true ]; then
    uv tool run ruff check src/ tests/ --fix
else
    uv tool run ruff check src/ tests/
fi
echo

echo "🔎 Running type checker..."
uv tool run mypy src/
echo

echo "🧪 Running tests..."
uv run pytest
echo

if [ "$FIX_MODE" = true ]; then
    echo "🔧 All checks completed with fixes applied!"
else
    echo "✅ All checks passed!"
fi
echo

