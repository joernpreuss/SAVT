from collections.abc import Generator

from sqlalchemy.future import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# from sqlmodel.pool import StaticPool


def _get_engine() -> Engine:
    # Use effective_database_url which handles both DATABASE_URL and DB_NAME
    sqlite_url = settings.effective_database_url
    connect_args = {}

    # Only disable thread checking in development/debug mode
    if settings.debug and "sqlite" in sqlite_url:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        sqlite_url,
        # echo=True,
        connect_args=connect_args,
        # poolclass=StaticPool,
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
