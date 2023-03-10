from sqlmodel import SQLModel, create_engine

sqlite_url = "sqlite:///./test.db"

engine = create_engine(sqlite_url, echo=True)


def get_engine():
    return engine


def init_db():
    SQLModel.metadata.create_all(engine)
