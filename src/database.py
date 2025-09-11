from sqlalchemy.future import Engine  # for the type hint
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# from sqlmodel.pool import StaticPool


def get_engine(_: str):
    # Use effective_database_url which handles both DATABASE_URL and DB_NAME
    sqlite_url = settings.effective_database_url
    engine = create_engine(
        sqlite_url,
        # echo=True,
        connect_args={
            "check_same_thread": False,  # TODO remove in production
        },
        # poolclass=StaticPool,
    )
    return engine


def init_db(engine: Engine):
    SQLModel.metadata.create_all(engine)


_engine: Engine | None = None


def get_main_engine():
    global _engine
    if _engine is None:
        _engine = get_engine(settings.db_name)
    return _engine


def get_session():
    with Session(get_main_engine()) as session:
        yield session
