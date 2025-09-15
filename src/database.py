from collections.abc import Generator

from sqlalchemy.future import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# from sqlmodel.pool import StaticPool


def _get_engine() -> Engine:
    # Use effective_database_url which handles both DATABASE_URL and DB_NAME
    database_url = settings.effective_database_url
    connect_args: dict[str, bool] = {}
    engine_kwargs: dict[str, int | bool] = {}

    # Configure connection args based on database type
    if "sqlite" in database_url:
        # SQLite specific configurations
        if settings.debug:
            connect_args["check_same_thread"] = False
    elif "postgresql" in database_url:
        # PostgreSQL specific configurations
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    engine = create_engine(
        database_url,
        # echo=True,  # Enable for SQL debugging
        connect_args=connect_args,
        **engine_kwargs,
        # poolclass=StaticPool,  # Only use for testing
    )
    return engine


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


_engine: Engine | None = None


def get_main_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_main_engine()) as session:
        yield session
