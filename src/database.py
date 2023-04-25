from sqlalchemy.future import Engine  # for the type hint
from sqlmodel import Session, SQLModel, create_engine

# from sqlmodel.pool import StaticPool


def get_engine(db_name: str):
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


def get_main_engine():
    engine = get_engine(db_name="prod2")
    init_db(engine)
    return engine


def get_session():
    with Session(get_main_engine()) as session:
        yield session
