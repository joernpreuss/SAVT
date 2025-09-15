# PostgreSQL Setup for SAVT

SAVT supports both SQLite (default) and PostgreSQL databases. This guide shows how to set up PostgreSQL using Docker.

## Quick Setup

```bash
# 1. Set up PostgreSQL with Docker
./scripts/postgres.sh setup

# 2. Start SAVT with PostgreSQL
uv run uvicorn src.main:app
```

## Manual Setup

### 1. Start PostgreSQL Container

```bash
# Start PostgreSQL in Docker
docker-compose up -d postgres

# Check if it's running
./scripts/postgres.sh status
```

### 2. Configure Database URL

Copy the PostgreSQL configuration:

```bash
cp .env.postgres .env
```

Or manually set the database URL in your `.env` file:

```env
DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt
```

### 3. Start SAVT

```bash
uv run uvicorn src.main:app
```

## Database Management

### PostgreSQL Script Commands

```bash
./scripts/postgres.sh setup     # First-time setup
./scripts/postgres.sh start     # Start PostgreSQL container
./scripts/postgres.sh stop      # Stop PostgreSQL container
./scripts/postgres.sh status    # Check status and health
./scripts/postgres.sh logs      # View container logs
./scripts/postgres.sh shell     # Connect to PostgreSQL shell
./scripts/postgres.sh reset     # Reset database (DELETE ALL DATA)
```

### Manual Database Access

```bash
# Connect to PostgreSQL directly
docker-compose exec postgres psql -U savt_user -d savt

# View tables
\dt

# Exit
\q
```

## Switching Between Databases

### Use SQLite (Default)

```env
# In .env file
DATABASE_URL=sqlite:///./savt.db
```

### Use PostgreSQL

```env
# In .env file
DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt
```

## Configuration Details

### PostgreSQL Container Settings

- **Image**: `postgres:16-alpine`
- **Database**: `savt`
- **Username**: `savt_user`
- **Password**: `savt_password`
- **Port**: `5432` (mapped to host)
- **Volume**: `postgres_data` (persistent storage)

### Connection Pool Settings

The application automatically configures connection pooling for PostgreSQL:

- **Pool Size**: 10 connections
- **Max Overflow**: 20 connections
- **Pre-ping**: Enabled (validates connections)

## Troubleshooting

### Container Won't Start

```bash
# Check logs
./scripts/postgres.sh logs

# Restart container
./scripts/postgres.sh restart
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
./scripts/postgres.sh status

# Check network connectivity
docker-compose exec postgres pg_isready -U savt_user -d savt
```

### Reset Database

```bash
# WARNING: This deletes all data
./scripts/postgres.sh reset
./scripts/postgres.sh setup
```

### Port Already in Use

If port 5432 is already in use, modify `docker-compose.yml`:

```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Use different host port
```

Then update your DATABASE_URL:

```env
DATABASE_URL=postgresql://savt_user:savt_password@localhost:5433/savt
```

## Performance Considerations

### SQLite vs PostgreSQL

**SQLite (Default)**
- ✅ Zero setup required
- ✅ Perfect for development
- ✅ Single file database
- ❌ Limited concurrency
- ❌ No network access

**PostgreSQL**
- ✅ Better concurrency
- ✅ Network accessible
- ✅ Production ready
- ✅ Advanced features
- ❌ Requires setup
- ❌ More resource usage

### When to Use Each

- **Development**: SQLite (default)
- **Production**: PostgreSQL
- **Multi-user**: PostgreSQL
- **Single user**: SQLite
- **Docker deployment**: PostgreSQL

## Backup and Restore

### Backup PostgreSQL

```bash
# Create backup
docker-compose exec postgres pg_dump -U savt_user savt > backup.sql

# Or with docker directly
docker exec savt_postgres pg_dump -U savt_user savt > backup.sql
```

### Restore PostgreSQL

```bash
# Restore from backup
docker-compose exec -i postgres psql -U savt_user savt < backup.sql
```

### Backup SQLite

```bash
# SQLite backup is just copying the file
cp savt.db backup.db
```

## Environment Variables

All database settings can be configured via environment variables:

```env
# Database Configuration
DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt

# Application Settings
DEBUG=true
HOST=0.0.0.0
PORT=8000
APP_NAME=SAVT

# Terminology Customization
OBJECT_NAME_SINGULAR=pizza
PROPERTY_NAME_SINGULAR=topping

# Security
SECRET_KEY=your-secret-key-here
```

See `.env.postgres` for a complete example configuration.
