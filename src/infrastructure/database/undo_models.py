"""Database models for undo functionality.

Provides persistent storage for deleted items and features to enable undo operations
that survive server restarts and don't consume increasing memory.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class DeletedItemRecord(SQLModel, table=True):  # type: ignore[call-arg]
    """Persistent storage for deleted items that can be restored."""

    __tablename__: str = "deleted_items"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)

    # Original item data
    original_name: str = Field(index=True)
    original_kind: str | None = None

    # Deletion metadata
    deleted_at: datetime = Field(default_factory=datetime.now, index=True)
    features_data: str  # JSON serialized features list

    # For cleanup
    expires_at: datetime = Field(index=True)


class DeletedFeatureRecord(SQLModel, table=True):  # type: ignore[call-arg]
    """Persistent storage for deleted features that can be restored."""

    __tablename__: str = "deleted_features"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)

    # Original feature data
    original_feature_id: int = Field(index=True)
    original_name: str
    original_kind: str | None = None
    original_item_id: int | None
    original_vetoed_by: str  # JSON serialized list

    # Deletion metadata
    deleted_at: datetime = Field(default_factory=datetime.now, index=True)

    # For cleanup
    expires_at: datetime = Field(index=True)
