from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture(scope="function")
def timestamp_str():
    return datetime.now().strftime(r"%Y-%m-%d %H:%M:%S:%f")


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///./pytest.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
