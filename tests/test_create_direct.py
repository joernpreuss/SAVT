from sqlmodel import Session

import database
from models import SVProperty

engine = database.get_engine()
database.init_db()


def test_create_property():

    test_prop = SVProperty(
        name="test_prop",
    )

    # test_obj = SVObject(
    #     name="test_obj",
    #     properties=[test_prop],
    # )

    with Session(engine) as session:
        session.add(test_prop)
        # session.add(test_obj)

        session.commit()
