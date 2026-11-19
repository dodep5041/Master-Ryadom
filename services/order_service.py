from sqlalchemy import select

from database import Order, SessionLocal


VALID_STATUSES = {
    "new",
    "in_progress",
    "completed",
    "cancelled",
}


def create_order(
    *,
    telegram_user_id: int,
    service_type: str,
    problem_description: str,
    city: str,
    customer_name: str,
    customer_contact: str,
    privacy_consent: bool,
    district: str | None = None,
    photo_file_id: str | None = None,
) -> Order:
    """Create and save a new customer order."""

    if not privacy_consent:
        raise ValueError("Customer consent is required")

    order = Order(
        telegram_user_id=telegram_user_id,
        service_type=service_type,
        problem_description=problem_description,
        photo_file_id=photo_file_id,
        city=city,
        district=district,
        customer_name=customer_name,
        customer_contact=customer_contact,
        privacy_consent=privacy_consent,
    )

    with SessionLocal() as session:
        try:
            session.add(order)
            session.commit()
            session.refresh(order)
            session.expunge(order)
            return order
        except Exception:
            session.rollback()
            raise


def get_order(order_id: int) -> Order | None:
    """Find an order by its unique ID."""

    with SessionLocal() as session:
        order = session.get(Order, order_id)

        if order is not None:
            session.expunge(order)

        return order


def get_orders(
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[Order]:
    """Return orders, optionally filtered by status."""

    if limit < 1 or limit > 500:
        raise ValueError("Limit must be between 1 and 500")

    if status is not None and status not in VALID_STATUSES:
        raise ValueError("Invalid order status")

    statement = select(Order).order_by(Order.created_at.desc()).limit(limit)

    if status is not None:
        statement = statement.where(Order.status == status)

    with SessionLocal() as session:
        orders = list(session.scalars(statement).all())

        for order in orders:
            session.expunge(order)

        return orders


def get_customer_orders(
    telegram_user_id: int,
    limit: int = 20,
) -> list[Order]:
    """Return only orders belonging to the specified Telegram user."""

    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    statement = (
        select(Order)
        .where(Order.telegram_user_id == telegram_user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )

    with SessionLocal() as session:
        orders = list(session.scalars(statement).all())

        for order in orders:
            session.expunge(order)

        return orders


def get_customer_order(
    order_id: int,
    telegram_user_id: int,
) -> Order | None:
    """Return an order only if it belongs to the specified Telegram user."""

    statement = select(Order).where(
        Order.id == order_id,
        Order.telegram_user_id == telegram_user_id,
    )

    with SessionLocal() as session:
        order = session.scalar(statement)

        if order is not None:
            session.expunge(order)

        return order


def update_order_status(order_id: int, status: str) -> Order | None:
    """Update an order status. Returns None if the order does not exist."""

    if status not in VALID_STATUSES:
        raise ValueError("Invalid order status")

    with SessionLocal() as session:
        try:
            order = session.get(Order, order_id)

            if order is None:
                return None

            order.status = status
            session.commit()
            session.refresh(order)
            session.expunge(order)

            return order
        except Exception:
            session.rollback()
            raise


def delete_customer_order(
    order_id: int,
    telegram_user_id: int,
) -> bool:
    """Delete an order only if it belongs to the requesting customer."""

    with SessionLocal() as session:
        try:
            statement = select(Order).where(
                Order.id == order_id,
                Order.telegram_user_id == telegram_user_id,
            )
            order = session.scalar(statement)

            if order is None:
                return False

            session.delete(order)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise