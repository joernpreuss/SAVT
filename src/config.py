from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    # Server configuration
    debug: bool = Field(default=True, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Database configuration
    database_url: str = Field(
        default="sqlite:///./savt.db", description="Database connection URL"
    )
    db_name: str = Field(default="savt", description="Database name for SQLite")

    # Application configuration
    app_name: str = Field(default="SAVT", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")

    # Security configuration
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32,
        description="Secret key for security features",
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
    def effective_database_url(self) -> str:
        """Get the effective database URL, handling SQLite with db_name."""
        if self.database_url == "sqlite:///./savt.db" and self.db_name != "savt":
            return f"sqlite:///./{self.db_name}.db"
        return self.database_url


# Global settings instance
settings = Settings()
