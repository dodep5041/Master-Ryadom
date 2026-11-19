from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_orders_keyboard(
    orders: list,
) -> InlineKeyboardMarkup:
    """Create an inline keyboard with order buttons."""

    keyboard = []

    for order in orders:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📄 Заявка #{order.id}",
                    callback_data=f"admin:order:{order.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_order_keyboard(
    order_id: int,
    status: str,
) -> InlineKeyboardMarkup:
    """Create action buttons for a single order."""

    keyboard = []

    if status == "new":
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🟡 Взять в работу",
                    callback_data=f"admin:status:{order_id}:in_progress",
                )
            ]
        )

    elif status == "in_progress":
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="✅ Завершить",
                    callback_data=f"admin:status:{order_id}:completed",
                )
            ]
        )

    if status not in {"completed", "cancelled"}:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="❌ Отменить заявку",
                    callback_data=f"admin:status:{order_id}:cancelled",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К списку заявок",
                callback_data="admin:orders",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)