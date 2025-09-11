import os


class Settings:
    """Application settings loaded from environment variables."""

    # Server configuration
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///./{os.getenv('DB_NAME', 'savt')}.db"
    )

    # Application configuration
    APP_NAME: str = os.getenv("APP_NAME", "SAVT")
    VERSION: str = "0.1.0"

    # Security (for future use)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    @property
    def is_development(self) -> bool:
        return self.DEBUG

    @property
    def is_production(self) -> bool:
        return not self.DEBUG


# Global settings instance
settings = Settings()
