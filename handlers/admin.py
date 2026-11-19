
import logging
from html import escape

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message

from config import get_settings
from keyboards.admin import (
    get_admin_order_keyboard,
    get_admin_orders_keyboard,
)
from services.order_service import (
    get_order,
    get_orders,
    update_order_status,
)


router = Router()
logger = logging.getLogger(__name__)


VALID_STATUSES = {
    "new",
    "in_progress",
    "completed",
    "cancelled",
}


STATUS_NAMES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Выполнена",
    "cancelled": "Отменена",
}


def is_admin(user_id: int | None) -> bool:
    """Check whether the user is the configured administrator."""

    if user_id is None:
        return False

    return user_id == get_settings().admin_id


def format_order_details(order) -> str:
    """Format full order information."""

    status_name = STATUS_NAMES.get(order.status, order.status)

    created_at = (
        order.created_at.strftime("%d.%m.%Y %H:%M")
        if order.created_at
        else "Не указано"
    )

    photo_status = "Есть" if order.photo_file_id else "Нет"

    return (
        f"📄 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Услуга:</b> {escape(order.service_type)}\n"
        f"<b>Описание:</b> {escape(order.problem_description)}\n"
        f"<b>Город:</b> {escape(order.city)}\n"
        f"<b>Район:</b> {escape(order.district or 'Не указан')}\n"
        f"<b>Имя:</b> {escape(order.customer_name)}\n"
        f"<b>Телефон:</b> {escape(order.customer_contact)}\n"
        f"<b>Фотография:</b> {photo_status}\n"
        f"<b>Согласие:</b> {'Да' if order.privacy_consent else 'Нет'}\n"
        f"<b>Статус:</b> {escape(status_name)}\n"
        f"<b>Дата создания:</b> {created_at}"
    )


async def notify_customer(
    bot: Bot,
    order,
    new_status: str,
) -> None:
    """Notify the customer when the order status changes."""

    status_messages = {
        "in_progress": (
            "🔧 Ваша заявка принята в работу!\n\n"
            "Мастер приступил к обработке вашего обращения."
        ),
        "completed": (
            "✅ Ваша заявка успешно выполнена!\n\n"
            "Спасибо, что воспользовались сервисом «Мастер рядом»!"
        ),
        "cancelled": (
            "❌ Ваша заявка отменена.\n\n"
            "Если у вас остались вопросы, вы можете связаться с исполнителем."
        ),
    }

    notification = status_messages.get(new_status)

    if notification is None:
        return

    text = (
        f"<b>Мастер рядом</b>\n\n"
        f"Заявка № {order.id}\n\n"
        f"{notification}"
    )

    try:
        await bot.send_message(
            chat_id=order.telegram_user_id,
            text=text,
        )

        logger.info(
            "Customer notified about order #%s status: %s",
            order.id,
            new_status,
        )

    except TelegramAPIError:
        logger.exception(
            "Could not notify customer about order #%s",
            order.id,
        )


async def show_orders(message: Message) -> None:
    """Display the latest orders with inline buttons."""

    orders = get_orders(limit=10)

    if not orders:
        await message.answer("📭 Пока заявок нет.")
        return

    lines = ["📋 <b>Последние заявки:</b>\n"]

    for order in orders:
        status_name = STATUS_NAMES.get(order.status, order.status)

        lines.append(
            f"🆔 <b>Заявка #{order.id}</b>\n"
            f"Услуга: {escape(order.service_type)}\n"
            f"Город: {escape(order.city)}\n"
            f"Статус: {escape(status_name)}"
        )

    await message.answer(
        "\n\n".join(lines),
        reply_markup=get_admin_orders_keyboard(orders),
    )


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ У вас нет доступа к административным командам.")
        return

    await message.answer(
        "🔐 <b>Панель администратора</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/orders — список последних заявок\n"
        "/order 2 — подробности заявки № 2\n"
        "/status 2 in_progress — изменить статус заявки № 2\n\n"
        "Также теперь можно управлять заявками с помощью кнопок."
    )


@router.message(Command("orders"))
async def admin_orders(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ У вас нет доступа к административным командам.")
        return

    await show_orders(message)


@router.message(Command("order"))
async def admin_order_details(
    message: Message,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ У вас нет доступа к административным командам.")
        return

    argument = (command.args or "").strip()

    if not argument.isdigit():
        await message.answer(
            "Укажи номер заявки.\n"
            "Пример: <code>/order 2</code>"
        )
        return

    order = get_order(int(argument))

    if order is None:
        await message.answer("❌ Заявка с таким номером не найдена.")
        return

    await message.answer(
        format_order_details(order),
        reply_markup=get_admin_order_keyboard(order.id, order.status),
    )


@router.message(Command("status"))
async def admin_change_status(
    message: Message,
    command: CommandObject,
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ У вас нет доступа к административным командам.")
        return

    arguments = (command.args or "").split()

    if len(arguments) != 2:
        await message.answer(
            "Укажи номер заявки и новый статус.\n\n"
            "Пример: <code>/status 2 in_progress</code>"
        )
        return

    order_id_text, new_status = arguments

    if not order_id_text.isdigit():
        await message.answer("❌ Номер заявки должен быть числом.")
        return

    if new_status not in VALID_STATUSES:
        await message.answer(
            "❌ Неизвестный статус.\n\n"
            "Допустимые значения:\n"
            "<code>new</code>\n"
            "<code>in_progress</code>\n"
            "<code>completed</code>\n"
            "<code>cancelled</code>"
        )
        return

    previous_order = get_order(int(order_id_text))

    if previous_order is None:
        await message.answer("❌ Заявка с таким номером не найдена.")
        return

    order = update_order_status(int(order_id_text), new_status)

    if order is None:
        await message.answer("❌ Не удалось изменить статус заявки.")
        return

    if previous_order.status != new_status:
        await notify_customer(message.bot, order, new_status)

    status_name = STATUS_NAMES[new_status]

    await message.answer(
        f"✅ Статус заявки #{order.id} изменён.\n\n"
        f"Новый статус: <b>{status_name}</b>"
    )

    logger.info(
        "Administrator changed order #%s status to %s",
        order.id,
        new_status,
    )


@router.callback_query(lambda callback: callback.data and callback.data.startswith("admin:"))
async def admin_callback_handler(callback: CallbackQuery) -> None:
    """Handle administrator inline keyboard actions."""

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ У вас нет доступа.",
            show_alert=True,
        )
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Не удалось открыть сообщение.")
        return

    parts = (callback.data or "").split(":")

    if parts[1] == "orders":
        orders = get_orders(limit=10)

        if not orders:
            await callback.message.edit_text("📭 Пока заявок нет.")
            await callback.answer()
            return

        lines = ["📋 <b>Последние заявки:</b>\n"]

        for order in orders:
            status_name = STATUS_NAMES.get(order.status, order.status)

            lines.append(
                f"🆔 <b>Заявка #{order.id}</b>\n"
                f"Услуга: {escape(order.service_type)}\n"
                f"Город: {escape(order.city)}\n"
                f"Статус: {escape(status_name)}"
            )

        await callback.message.edit_text(
            "\n\n".join(lines),
            reply_markup=get_admin_orders_keyboard(orders),
        )
        await callback.answer()
        return

    if len(parts) == 3 and parts[1] == "order":
        if not parts[2].isdigit():
            await callback.answer("Некорректный номер заявки.", show_alert=True)
            return

        order = get_order(int(parts[2]))

        if order is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        await callback.message.edit_text(
            format_order_details(order),
            reply_markup=get_admin_order_keyboard(order.id, order.status),
        )
        await callback.answer()
        return

    if len(parts) == 4 and parts[1] == "status":
        order_id_text = parts[2]
        new_status = parts[3]

        if not order_id_text.isdigit() or new_status not in VALID_STATUSES:
            await callback.answer("Некорректные данные.", show_alert=True)
            return

        previous_order = get_order(int(order_id_text))

        if previous_order is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        order = update_order_status(int(order_id_text), new_status)

        if order is None:
            await callback.answer("Не удалось изменить статус.", show_alert=True)
            return

        if previous_order.status != new_status:
            await notify_customer(callback.bot, order, new_status)

        await callback.message.edit_text(
            format_order_details(order),
            reply_markup=get_admin_order_keyboard(order.id, order.status),
        )

        logger.info(
            "Administrator changed order #%s status to %s using a button",
            order.id,
            new_status,
        )

        await callback.answer("Статус заявки обновлён.")
        return

    await callback.answer("Неизвестное действие.", show_alert=True)
