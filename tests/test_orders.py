
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.order_service as order_service
from database import Base


@pytest.fixture(autouse=True)
def test_database(monkeypatch):
    """Use an isolated temporary database for every test."""

    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "test.db"
        test_engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )

        TestSessionLocal = sessionmaker(
            bind=test_engine,
            autoflush=False,
            autocommit=False,
        )

        Base.metadata.create_all(bind=test_engine)

        monkeypatch.setattr(
            order_service,
            "SessionLocal",
            TestSessionLocal,
        )

        yield

        test_engine.dispose()


def make_test_order(telegram_user_id=111111111):
    """Create an order with fictional test data."""

    return order_service.create_order(
        telegram_user_id=telegram_user_id,
        service_type="Сантехника",
        problem_description="Тестовая заявка",
        city="Тестовый город",
        district="Центр",
        customer_name="Тестовый клиент",
        customer_contact="+79990000000",
        privacy_consent=True,
    )


def test_create_order():
    order = make_test_order()

    assert order.id is not None
    assert order.status == "new"
    assert order.city == "Тестовый город"


def test_get_order():
    created = make_test_order()

    found = order_service.get_order(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.service_type == "Сантехника"


def test_get_orders():
    make_test_order()

    orders = order_service.get_orders()

    assert len(orders) == 1
    assert orders[0].status == "new"


def test_update_order_status():
    created = make_test_order()

    updated = order_service.update_order_status(
        created.id,
        "in_progress",
    )

    assert updated is not None
    assert updated.status == "in_progress"


def test_delete_customer_order():
    created = make_test_order()

    deleted = order_service.delete_customer_order(
        created.id,
        111111111,
    )

    assert deleted is True
    assert order_service.get_order(created.id) is None


def test_cannot_delete_another_users_order():
    created = make_test_order()

    deleted = order_service.delete_customer_order(
        created.id,
        222222222,
    )

    assert deleted is False
    assert order_service.get_order(created.id) is not None


def test_order_requires_privacy_consent():
    with pytest.raises(ValueError):
        order_service.create_order(
            telegram_user_id=111111111,
            service_type="Сантехника",
            problem_description="Тестовая заявка",
            city="Тестовый город",
            customer_name="Тестовый клиент",
            customer_contact="+79990000000",
            privacy_consent=False,
        )


def test_customer_sees_only_own_orders():
    own_order = make_test_order(111111111)
    make_test_order(222222222)

    orders = order_service.get_customer_orders(111111111)

    assert len(orders) == 1
    assert orders[0].id == own_order.id
    assert orders[0].telegram_user_id == 111111111


def test_customer_can_get_own_order():
    created = make_test_order(111111111)

    found = order_service.get_customer_order(
        created.id,
        111111111,
    )

    assert found is not None
    assert found.id == created.id


def test_customer_cannot_get_another_users_order():
    created = make_test_order(111111111)

    found = order_service.get_customer_order(
        created.id,
        222222222,
    )

    assert found is None


def test_customer_without_orders_gets_empty_list():
    orders = order_service.get_customer_orders(111111111)

    assert orders == []
