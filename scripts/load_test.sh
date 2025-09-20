#!/bin/bash
set -e

# Default to 33 users if no argument provided
USERS=${1:-33}

# Cleanup function to kill server on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    # Also kill any remaining uvicorn processes on port 8000
    pkill -f "uvicorn src.main:app --host 0.0.0.0 --port 8000" 2>/dev/null || true
    echo "✅ Load test completed!"
}

# Set trap to run cleanup on script exit
trap cleanup EXIT

echo "🧪 SAVT Load Test Script"
echo "========================"
echo "👥 Testing with $USERS users"

# Make sure we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Not in SAVT project directory"
    echo "💡 Run from the SAVT root directory"
    exit 1
fi

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL availability..."
if ! docker exec savt-postgres pg_isready -U savt_user >/dev/null 2>&1; then
    echo "❌ PostgreSQL is not running"
    echo "💡 Starting PostgreSQL..."
    ./scripts/postgres.sh start
    sleep 3
fi

echo "✅ PostgreSQL is running"

# Start the server in background
echo "🚀 Starting SAVT server..."
TEST_DATABASE=postgresql DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt \
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 &

SERVER_PID=$!
echo "📡 Server started with PID $SERVER_PID"

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8000 >/dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    echo "   Waiting... ($i/10)"
    sleep 2
done

# Run the load test
echo ""
echo "🧪 Running $USERS-user load test..."
echo "================================"

# Run the appropriate load test
echo "📝 Running load test with $USERS users"
USERS=$USERS uv run python tests/load_test_quick.py

# Cleanup happens automatically via trap
