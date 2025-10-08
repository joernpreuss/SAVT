#!/bin/bash
# Remove SQLite database files

echo "Removing SQLite database..."
rm -f savt.db savt.db-shm savt.db-wal
echo "✓ Database removed"
