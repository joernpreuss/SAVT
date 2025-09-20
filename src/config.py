import secrets
from typing import Final

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import DEFAULT_PORT, MIN_SECRET_KEY_LENGTH


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    # Server configuration
    debug: bool = Field(default=True, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535, description="Server port")

    # Database configuration
    database_url: str = Field(
        default="sqlite:///./savt.db", description="Database connection URL"
    )
    db_name: str = Field(default="savt", description="Database name for SQLite")

    # Application configuration
    app_name: str = Field(default="SAVT", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")

    # Terminology configuration
    object_name_singular: str = Field(
        default="object",
        description="Singular term for objects (e.g., 'pizza', 'item')",
    )
    object_name_plural: str | None = Field(
        default=None, description="Plural term for objects (defaults to singular + 's')"
    )
    property_name_singular: str = Field(
        default="property",
        description="Singular term for properties (e.g., 'topping', 'feature')",
    )
    property_name_plural: str | None = Field(
        default=None,
        description="Plural term for properties (defaults to singular + 's')",
    )

    # Security configuration
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=MIN_SECRET_KEY_LENGTH,
        description="Secret key for security features",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate and potentially generate a secure secret key."""
        # If using the insecure default, generate a random one
        if v == "dev-secret-key-change-in-production":
            # Generate a cryptographically secure random key
            secure_key = secrets.token_urlsafe(64)
            print(
                "⚠️  WARNING: Using default secret key. "
                "Generated secure key for this session."
            )
            print(
                "💡 For production, set SECRET_KEY environment variable "
                "or add to .env file:"
            )
            print(f"   SECRET_KEY={secure_key}")
            return secure_key

        # Validate minimum length
        if len(v) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"Secret key must be at least {MIN_SECRET_KEY_LENGTH} characters long"
            )

        return v

    # Logging configuration
    log_to_file: bool = Field(
        default=False, description="Force logging to file even in debug mode"
    )

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug

    @computed_field  # type: ignore[prop-decorator]
    @property
    def object_name_plural_computed(self) -> str:
        """Get the plural form of object name, defaulting to singular + 's'."""
        return self.object_name_plural or f"{self.object_name_singular}s"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def property_name_plural_computed(self) -> str:
        """Get the plural form of property name, defaulting to singular + 's'."""
        return self.property_name_plural or f"{self.property_name_singular}s"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL, handling SQLite with db_name."""
        if self.database_url == "sqlite:///./savt.db" and self.db_name != "savt":
            return f"sqlite:///./{self.db_name}.db"
        return self.database_url


# Global settings instance
settings: Final = Settings()
