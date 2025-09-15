#!/bin/bash
# PostgreSQL management script for SAVT

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

case "${1:-help}" in
    start)
        echo "Starting PostgreSQL container..."
        docker compose up -d postgres
        echo "PostgreSQL is starting up. Use 'postgres.sh status' to check health."
        echo "Use 'postgres.sh logs' to view startup logs."
        ;;

    stop)
        echo "Stopping PostgreSQL container..."
        docker compose stop postgres
        ;;

    restart)
        echo "Restarting PostgreSQL container..."
        docker compose restart postgres
        ;;

    status)
        echo "PostgreSQL container status:"
        docker compose ps postgres
        echo
        echo "Health check:"
        docker compose exec postgres pg_isready -U savt_user -d savt 2>/dev/null && \
            echo "✅ PostgreSQL is ready" || \
            echo "❌ PostgreSQL is not ready"
        ;;

    logs)
        echo "PostgreSQL container logs:"
        docker compose logs -f postgres
        ;;

    shell)
        echo "Connecting to PostgreSQL shell..."
        docker compose exec postgres psql -U savt_user -d savt
        ;;

    setup)
        echo "Setting up PostgreSQL for SAVT..."
        # Check if .env exists and warn about DATABASE_URL
        if [[ -f .env ]]; then
            if grep -q "DATABASE_URL.*sqlite" .env 2>/dev/null; then
                echo "⚠️  Warning: .env file contains SQLite DATABASE_URL"
                echo "   Copy .env.postgres to .env to use PostgreSQL"
            fi
        else
            echo "📋 Copying PostgreSQL configuration..."
            cp .env.postgres .env
            echo "✅ Created .env with PostgreSQL settings"
        fi

        echo "🐘 Starting PostgreSQL container..."
        "$0" start

        echo "⏳ Waiting for PostgreSQL to be ready..."
        for i in {1..30}; do
            if docker compose exec postgres pg_isready -U savt_user -d savt >/dev/null 2>&1; then
                echo "✅ PostgreSQL is ready!"
                break
            fi
            echo "   Waiting... ($i/30)"
            sleep 2
        done

        echo
        echo "🎉 PostgreSQL setup complete!"
        echo "   Database URL: postgresql://savt_user:savt_password@localhost:5432/savt"
        echo "   Run 'uv run uvicorn src.main:app' to start SAVT with PostgreSQL"
        ;;

    reset)
        echo "⚠️  This will DELETE ALL DATA in the PostgreSQL database!"
        read -p "Are you sure? Type 'yes' to continue: " -r
        if [[ $REPLY == "yes" ]]; then
            echo "Stopping and removing PostgreSQL container and volume..."
            docker compose down postgres
            docker volume rm savt_postgres_data 2>/dev/null || echo "Volume already removed"
            echo "✅ PostgreSQL data reset complete"
        else
            echo "Cancelled"
        fi
        ;;

    help|*)
        echo "PostgreSQL management script for SAVT"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  setup     - Set up PostgreSQL (copy config, start container)"
        echo "  start     - Start PostgreSQL container"
        echo "  stop      - Stop PostgreSQL container"
        echo "  restart   - Restart PostgreSQL container"
        echo "  status    - Show container and database status"
        echo "  logs      - Show container logs"
        echo "  shell     - Connect to PostgreSQL shell"
        echo "  reset     - Reset database (DELETE ALL DATA)"
        echo "  help      - Show this help"
        echo
        echo "Examples:"
        echo "  $0 setup                 # First-time setup"
        echo "  $0 start                 # Start database"
        echo "  $0 shell                 # Connect to database"
        echo
        ;;
esac
