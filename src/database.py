from sqlalchemy.future import Engine  # for the type hint
from sqlmodel import Session, SQLModel, create_engine

from config import settings

# from sqlmodel.pool import StaticPool


def get_engine(db_name: str):
    # Use DATABASE_URL from settings if it's not the default SQLite pattern
    if "sqlite:///" in settings.DATABASE_URL and db_name in settings.DATABASE_URL:
        sqlite_url = settings.DATABASE_URL
    else:
        sqlite_url = f"sqlite:///./{db_name}.db"
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
        _engine = get_engine(db_name="prod2")
    return _engine


def get_session():
    with Session(get_main_engine()) as session:
        yield session
