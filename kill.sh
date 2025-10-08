#!/bin/bash
# Kill processes on port 8000

echo "Killing processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
echo "✓ Port 8000 cleared"
