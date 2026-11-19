
import logging
import re
from html import escape

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.user import (
    get_main_keyboard,
    get_customer_orders_keyboard,
)
from services.order_service import (
    get_customer_orders,
    get_customer_order,
)


router = Router()
logger = logging.getLogger(__name__)


STATUS_NAMES = {
    "new": "🆕 Новая",
    "in_progress": "🟡 В работе",
    "completed": "✅ Выполнена",
    "cancelled": "❌ Отменена",
}


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
) -> None:
    # Clear any unfinished application process.
    await state.clear()

    await message.answer(
        "Здравствуйте! 👋\n\n"
        "Добро пожаловать в «Мастер рядом»!\n\n"
        "Здесь вы можете оставить заявку на ремонт "
        "или бытовую услугу, не совершая телефонный звонок.\n\n"
        "Выберите нужный раздел в меню ниже.",
        reply_markup=get_main_keyboard(),
    )


@router.message(
    StateFilter(None),
    F.text == "📋 Мои заявки",
)
async def show_customer_orders(message: Message) -> None:
    if message.from_user is None:
        return

    try:
        orders = get_customer_orders(
            telegram_user_id=message.from_user.id,
            limit=20,
        )
    except Exception:
        logger.exception("Не удалось получить заявки клиента")

        await message.answer(
            "Не удалось загрузить ваши заявки. "
            "Попробуйте немного позже."
        )
        return

    if not orders:
        await message.answer(
            "📋 У вас пока нет оформленных заявок.\n\n"
            "Вы можете создать первую заявку, нажав "
            "«📝 Оставить заявку».",
            reply_markup=get_main_keyboard(),
        )
        return

    await message.answer(
        "📋 <b>Мои заявки</b>\n\n"
        "Выберите заявку, чтобы посмотреть подробную информацию.\n\n"
        "Показаны последние 20 обращений.",
        reply_markup=get_customer_orders_keyboard(orders),
    )


@router.message(
    StateFilter(None),
    F.text.regexp(r"^📄 Заявка #\d+$"),
)
async def show_customer_order_details(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return

    match = re.fullmatch(r"📄 Заявка #(\d+)", message.text)

    if match is None:
        return

    order_id = int(match.group(1))

    try:
        order = get_customer_order(
            order_id=order_id,
            telegram_user_id=message.from_user.id,
        )
    except Exception:
        logger.exception("Не удалось получить заявку #%s", order_id)

        await message.answer(
            "Не удалось загрузить заявку. "
            "Попробуйте немного позже."
        )
        return

    if order is None:
        await message.answer(
            "Заявка не найдена или у вас нет доступа к ней.",
            reply_markup=get_main_keyboard(),
        )
        return

    status_name = STATUS_NAMES.get(
        order.status,
        "Неизвестный статус",
    )

    created_at = (
        order.created_at.strftime("%d.%m.%Y %H:%M")
        if order.created_at
        else "Не указана"
    )

    details = (
        f"📄 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Статус:</b> {status_name}\n"
        f"<b>Услуга:</b> {escape(order.service_type)}\n"
        f"<b>Описание:</b> {escape(order.problem_description)}\n"
        f"<b>Город:</b> {escape(order.city)}\n"
        f"<b>Район:</b> {escape(order.district or 'Не указан')}\n"
        f"<b>Дата создания:</b> {created_at}\n\n"
        "Если статус заявки изменится, "
        "мы сообщим вам об этом."
    )

    await message.answer(
        details,
        reply_markup=get_main_keyboard(),
    )


@router.message(
    StateFilter(None),
    F.text == "⬅️ Главное меню",
)
async def return_to_main_menu(message: Message) -> None:
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=get_main_keyboard(),
    )


@router.message(
    StateFilter(None),
    F.text == "🔧 Наши услуги",
)
async def show_services(message: Message) -> None:
    await message.answer(
        "🔧 <b>Наши услуги</b>\n\n"
        "• Сантехнические работы\n"
        "• Электромонтажные работы\n"
        "• Ремонт мебели\n"
        "• Сборка мебели\n"
        "• Отделочные работы\n"
        "• Мелкий бытовой ремонт\n"
        "• Другие бытовые услуги"
    )


@router.message(
    StateFilter(None),
    F.text == "ℹ️ Как это работает",
)
async def show_how_it_works(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Как это работает</b>\n\n"
        "1. Вы выбираете нужную услугу.\n"
        "2. Описываете проблему.\n"
        "3. Указываете город и контактные данные.\n"
        "4. Подтверждаете заявку.\n\n"
        "После этого мастер получит вашу заявку."
    )


@router.message(
    StateFilter(None),
    F.text == "📞 Контакты",
)
async def show_contacts(message: Message) -> None:
    await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "Чтобы связаться с мастером, оставьте заявку через меню.\n\n"
        "Контактные данные конкретного исполнителя "
        "будут предоставлены здесь после настройки сервиса."
    )


@router.message(
    StateFilter(None),
    F.text == "🔒 Конфиденциальность",
)
async def show_privacy(message: Message) -> None:
    await message.answer(
        "🔒 <b>Конфиденциальность</b>\n\n"
        "Мы запрашиваем только те данные, которые необходимы "
        "для обработки вашей заявки.\n\n"
        "Перед отправкой заявки вы сможете ознакомиться "
        "с условиями обработки персональных данных.\n\n"
        "Полный текст политики конфиденциальности "
        "будет добавлен перед запуском сервиса."
    )
