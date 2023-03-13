from sqlalchemy.future import Engine  # for the type hint
from sqlmodel import SQLModel, create_engine

# from sqlmodel.pool import StaticPool


def get_engine(db_name: str):
    sqlite_url = f"sqlite:///./{db_name}.db"
    engine = create_engine(
        sqlite_url,
        echo=True,
        # connect_args={"check_same_thread": False},
        # poolclass=StaticPool,
    )
    return engine


def init_db(engine: Engine):
    SQLModel.metadata.create_all(engine)
