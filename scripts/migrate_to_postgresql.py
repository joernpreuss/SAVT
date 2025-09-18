#!/usr/bin/env python3
"""
Data migration script from SQLite to PostgreSQL for SAVT.

This script handles the migration of existing data when transitioning
from SQLite to PostgreSQL for better concurrent user support.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, create_engine, select

from src.config import settings
from src.infrastructure.database.database import get_async_engine
from src.infrastructure.database.models import Feature, Item


def get_sqlite_data():
    """Extract all data from SQLite database."""
    print("📖 Reading data from SQLite database...")

    # Force SQLite connection
    sqlite_url = "sqlite:///./savt.db"
    sqlite_engine = create_engine(sqlite_url)

    items = []
    features = []

    with Session(sqlite_engine) as session:
        # Get all items
        items_result = session.exec(select(Item))
        items = items_result.all()
        print(f"   Found {len(items)} items")

        # Get all features
        features_result = session.exec(select(Feature))
        features = features_result.all()
        print(f"   Found {len(features)} features")

    return items, features


async def migrate_data_to_postgresql(items: list[Item], features: list[Feature]):
    """Migrate data to PostgreSQL database."""
    print("📝 Migrating data to PostgreSQL...")

    async_engine = get_async_engine()

    async with AsyncSession(async_engine) as session:
        try:
            # First, migrate items
            print(f"   Migrating {len(items)} items...")
            for item in items:
                # Reset ID to let PostgreSQL assign new ones
                item.id = None
                session.add(item)

            await session.commit()
            print("   ✅ Items migrated successfully")

            # Refresh items to get new PostgreSQL IDs
            await session.refresh_all()

            # Create mapping from old names to new items
            item_name_to_id = {}
            items_result = await session.execute(select(Item))
            for item in items_result.scalars():
                item_name_to_id[item.name] = item.id

            # Migrate features with correct item_id references
            print(f"   Migrating {len(features)} features...")
            for feature in features:
                # Reset ID and update item_id reference
                feature.id = None
                if feature.item_id is not None:
                    # Find the item by iterating through migrated items
                    old_item_name = None
                    for item in items:
                        if item.id == feature.item_id:  # This is the old SQLite ID
                            old_item_name = item.name
                            break

                    if old_item_name and old_item_name in item_name_to_id:
                        feature.item_id = item_name_to_id[old_item_name]
                    else:
                        # Make it standalone if we can't find the item
                        feature.item_id = None

                session.add(feature)

            await session.commit()
            print("   ✅ Features migrated successfully")

        except Exception as e:
            print(f"   ❌ Migration failed: {e}")
            await session.rollback()
            raise


async def verify_migration():
    """Verify that migration was successful."""
    print("🔍 Verifying migration...")

    async_engine = get_async_engine()

    async with AsyncSession(async_engine) as session:
        # Count items
        items_result = await session.execute(select(Item))
        item_count = len(items_result.scalars().all())
        features_result = await session.execute(select(Feature))
        feature_count = len(features_result.scalars().all())

        print(f"   PostgreSQL now has:")
        print(f"   - {item_count} items")
        print(f"   - {feature_count} features")

        return item_count, feature_count


async def main():
    """Main migration function."""
    print("🚀 Starting SAVT data migration from SQLite to PostgreSQL")
    print(f"📊 Current database URL: {settings.effective_database_url}")

    # Check if we're actually using PostgreSQL
    if "postgresql" not in settings.effective_database_url:
        print("⚠️  Warning: DATABASE_URL is not set to PostgreSQL")
        print("   Set DATABASE_URL to a PostgreSQL connection string, e.g.:")
        print("   export DATABASE_URL='postgresql://user:password@localhost:5432/savt'")
        print("   or update your .env file")
        return

    try:
        # Step 1: Extract data from SQLite
        items, features = get_sqlite_data()

        if not items and not features:
            print("📭 No data found in SQLite database - nothing to migrate")
            return

        # Step 2: Initialize PostgreSQL schema
        print("🏗️  Initializing PostgreSQL schema...")
        from src.infrastructure.database.database import init_async_db

        await init_async_db(get_async_engine())
        print("   ✅ PostgreSQL schema initialized")

        # Step 3: Migrate data
        await migrate_data_to_postgresql(items, features)

        # Step 4: Verify migration
        await verify_migration()

        print("🎉 Migration completed successfully!")
        print("📋 Next steps:")
        print("   1. Test the application with PostgreSQL")
        print("   2. Run load tests to verify concurrency improvements")
        print("   3. Backup the SQLite file as needed")
        print("   4. Update your deployment configuration")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("💡 Troubleshooting tips:")
        print("   - Ensure PostgreSQL is running")
        print("   - Check DATABASE_URL connection string")
        print("   - Verify database credentials")
        print("   - Make sure the database exists")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
