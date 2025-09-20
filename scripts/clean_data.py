#!/usr/bin/env python3
"""
Clean database data by removing items and features with problematic characters.

Removes:
- Newlines (\n)
- Carriage returns (\r)
- Tabs (\t)
- Other control characters

Keeps:
- Normal ASCII
- Unicode letters (umlauts, accents, etc.)
- Spaces, punctuation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.database import get_async_session
from src.infrastructure.database.models import Feature, Item


def has_problematic_chars(text: str) -> bool:
    """Check if text contains problematic control characters."""
    if not text:
        return False

    # Check for control characters except space (32)
    for char in text:
        if (ord(char) < 32 and char not in [" "]) or ord(char) == 127:  # Allow space, reject DEL
            return True
        # Also check for specific problematic characters
        if char in ["\n", "\r", "\t", "\v", "\f"]:
            return True

    return False


async def clean_database():
    """Clean the database of items and features with problematic characters."""
    print("🧹 CLEANING DATABASE")
    print("=" * 40)

    async for session in get_async_session():
        # Clean Features
        print("🔍 Checking features...")

        # Get all features
        from sqlalchemy import select

        result = await session.execute(select(Feature))
        features = result.scalars().all()

        problematic_features = []
        for feature in features:
            if has_problematic_chars(feature.name):
                problematic_features.append(feature)
                print(f"  ❌ Feature: {repr(feature.name)} (ID: {feature.id})")

        # Delete problematic features
        if problematic_features:
            for feature in problematic_features:
                await session.delete(feature)
            await session.commit()
            print(f"✅ Deleted {len(problematic_features)} problematic features")
        else:
            print("✅ No problematic features found")

        # Clean Items
        print("\n🔍 Checking items...")

        result = await session.execute(select(Item))
        items = result.scalars().all()

        problematic_items = []
        for item in items:
            if has_problematic_chars(item.name):
                problematic_items.append(item)
                print(f"  ❌ Item: {repr(item.name)} (ID: {item.id})")

        # Delete problematic items
        if problematic_items:
            for item in problematic_items:
                await session.delete(item)
            await session.commit()
            print(f"✅ Deleted {len(problematic_items)} problematic items")
        else:
            print("✅ No problematic items found")

        # Show remaining data
        print("\n📊 Remaining clean data:")

        result = await session.execute(select(Feature))
        clean_features = result.scalars().all()
        print(f"  Features: {len(clean_features)}")
        for feature in clean_features[:5]:  # Show first 5
            print(f"    - {feature.name}")
        if len(clean_features) > 5:
            print(f"    ... and {len(clean_features) - 5} more")

        result = await session.execute(select(Item))
        clean_items = result.scalars().all()
        print(f"  Items: {len(clean_items)}")
        for item in clean_items[:5]:  # Show first 5
            print(f"    - {item.name}")
        if len(clean_items) > 5:
            print(f"    ... and {len(clean_items) - 5} more")


async def test_valid_unicode():
    """Test that valid Unicode characters are preserved."""
    print("\n🌍 TESTING UNICODE SUPPORT")
    print("=" * 40)

    test_names = [
        "café",  # French
        "naïve",  # French
        "résumé",  # French
        "Müller",  # German umlaut
        "Björk",  # Swedish
        "José",  # Spanish
        "Москва",  # Russian (Cyrillic)
        "東京",  # Japanese
        "العربية",  # Arabic
    ]

    for name in test_names:
        has_problem = has_problematic_chars(name)
        status = "❌ PROBLEM" if has_problem else "✅ CLEAN"
        print(f"  {status}: {name}")


if __name__ == "__main__":
    # Set database URL
    os.environ["DATABASE_URL"] = (
        "postgresql://savt_user:savt_password@localhost:5432/savt"
    )

    asyncio.run(clean_database())
    asyncio.run(test_valid_unicode())
