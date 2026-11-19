
import logging
import re
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import get_settings
from keyboards.user import (
    get_main_keyboard,
    get_services_keyboard,
    get_skip_photo_keyboard,
    get_skip_district_keyboard,
    get_contact_keyboard,
    get_privacy_keyboard,
    get_cancel_keyboard,
)
from states.application import ApplicationStates
from services.order_service import create_order


router = Router()
logger = logging.getLogger(__name__)


def is_valid_phone(phone: str) -> bool:
    """Check that a phone number contains 7 to 15 digits."""

    cleaned_phone = re.sub(r"[\s()\-]", "", phone)

    if cleaned_phone.startswith("+"):
        cleaned_phone = cleaned_phone[1:]

    return cleaned_phone.isdigit() and 7 <= len(cleaned_phone) <= 15


async def notify_admin(
    message: Message,
    order,
    photo_file_id: str | None,
) -> None:
    """Send a new order notification to the administrator."""

    settings = get_settings()

    notification = (
        f"🆕 <b>Новая заявка #{order.id}</b>\n\n"
        f"<b>Услуга:</b> {escape(order.service_type)}\n"
        f"<b>Описание:</b> {escape(order.problem_description)}\n"
        f"<b>Город:</b> {escape(order.city)}\n"
        f"<b>Район:</b> {escape(order.district or 'Не указан')}\n"
        f"<b>Имя:</b> {escape(order.customer_name)}\n"
        f"<b>Телефон:</b> {escape(order.customer_contact)}\n"
        f"<b>Статус:</b> {escape(order.status)}"
    )

    await message.bot.send_message(
        chat_id=settings.admin_id,
        text=notification,
    )

    if photo_file_id:
        await message.bot.send_photo(
            chat_id=settings.admin_id,
            photo=photo_file_id,
            caption=f"📷 Фотография к заявке #{order.id}",
        )


@router.message(
    StateFilter(ApplicationStates),
    F.text == "❌ Отменить оформление",
)
async def cancel_application(
    message: Message,
    state: FSMContext,
) -> None:
    """Cancel the application process and clear its FSM state."""

    await state.clear()

    await message.answer(
        "❌ Оформление заявки отменено.\n\n"
        "Все введённые данные незавершённой заявки удалены.\n\n"
        "Вы вернулись в главное меню.",
        reply_markup=get_main_keyboard(),
    )


async def finish_contact_step(
    message: Message,
    state: FSMContext,
    phone: str,
) -> None:
    await state.update_data(customer_contact=phone)
    await state.set_state(ApplicationStates.accepting_privacy)

    await message.answer(
        "Номер телефона сохранён! ✅\n\n"
        "🔒 Перед оформлением заявки ознакомьтесь с условиями "
        "обработки персональных данных.\n\n"
        "Ваши данные будут использованы для регистрации заявки "
        "и связи с вами.\n\n"
        "Подтвердите своё решение:",
        reply_markup=get_privacy_keyboard(),
    )


async def ask_for_city(message: Message) -> None:
    await message.answer(
        "Теперь укажите город, в котором требуется выполнить работу.",
        reply_markup=get_cancel_keyboard(),
    )


async def ask_for_district(message: Message, state: FSMContext) -> None:
    await state.set_state(ApplicationStates.entering_district)

    await message.answer(
        "Укажите район города, если это необходимо.\n\n"
        "Если не хотите указывать район, нажмите «Пропустить район».",
        reply_markup=get_skip_district_keyboard(),
    )


async def ask_for_name(message: Message, state: FSMContext) -> None:
    await state.set_state(ApplicationStates.entering_name)

    await message.answer(
        "Как к вам обращаться?\n\n"
        "Укажите ваше имя.",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(F.text == "📝 Оставить заявку")
async def start_application(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(ApplicationStates.choosing_service)

    await message.answer(
        "📝 Давайте оформим вашу заявку!\n\n"
        "Выберите услугу, которая вам нужна:",
        reply_markup=get_services_keyboard(),
    )


@router.message(ApplicationStates.choosing_service)
async def process_service(
    message: Message,
    state: FSMContext,
) -> None:
    services = {
        "🚰 Сантехника": "Сантехника",
        "⚡ Электрика": "Электрика",
        "🪑 Ремонт мебели": "Ремонт мебели",
        "🛠 Сборка мебели": "Сборка мебели",
        "🏠 Отделочные работы": "Отделочные работы",
        "🔨 Мелкий бытовой ремонт": "Мелкий бытовой ремонт",
        "📦 Другое": "Другое",
    }

    if message.text == "⬅️ Главное меню":
        await state.clear()
        await message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_keyboard(),
        )
        return

    service = services.get(message.text)

    if service is None:
        await message.answer(
            "Пожалуйста, выберите услугу с помощью кнопок ниже."
        )
        return

    await state.update_data(service_type=service)
    await state.set_state(ApplicationStates.entering_description)

    await message.answer(
        f"Вы выбрали: {service}.\n\n"
        "Теперь опишите, пожалуйста, что нужно сделать.\n"
        "Например: «Протекает кран на кухне».",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(ApplicationStates.entering_description, F.text)
async def process_description(
    message: Message,
    state: FSMContext,
) -> None:
    description = message.text.strip()

    if len(description) < 10:
        await message.answer(
            "Пожалуйста, опишите проблему немного подробнее.\n\n"
            "Минимальная длина описания — 10 символов.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    if len(description) > 2000:
        await message.answer(
            "Описание слишком длинное.\n"
            "Пожалуйста, сократите его до 2000 символов.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(problem_description=description)
    await state.set_state(ApplicationStates.uploading_photo)

    await message.answer(
        "Спасибо! Описание проблемы сохранено. ✅\n\n"
        "📷 Теперь можете отправить фотографию проблемы.\n\n"
        "Если фотографии нет, нажмите кнопку «Пропустить».",
        reply_markup=get_skip_photo_keyboard(),
    )


@router.message(ApplicationStates.entering_description)
async def invalid_description(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте описание проблемы обычным текстовым сообщением."
    )


@router.message(ApplicationStates.uploading_photo, F.photo)
async def process_photo(
    message: Message,
    state: FSMContext,
) -> None:
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)

    await message.answer(
        "Фотография получена! ✅"
    )

    await state.set_state(ApplicationStates.entering_city)
    await ask_for_city(message)


@router.message(
    ApplicationStates.uploading_photo,
    F.text == "Пропустить",
)
async def skip_photo(
    message: Message,
    state: FSMContext,
) -> None:
    await state.update_data(photo_file_id=None)

    await message.answer(
        "Хорошо, продолжим без фотографии."
    )

    await state.set_state(ApplicationStates.entering_city)
    await ask_for_city(message)


@router.message(ApplicationStates.uploading_photo)
async def invalid_photo(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте фотографию или нажмите кнопку «Пропустить»."
    )


@router.message(ApplicationStates.entering_city, F.text)
async def process_city(
    message: Message,
    state: FSMContext,
) -> None:
    city = message.text.strip()

    if len(city) < 2 or len(city) > 100:
        await message.answer(
            "Пожалуйста, укажите название города (от 2 до 100 символов).",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(city=city)
    await ask_for_district(message, state)


@router.message(ApplicationStates.entering_city)
async def invalid_city(message: Message) -> None:
    await message.answer(
        "Пожалуйста, укажите город текстовым сообщением.",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(
    ApplicationStates.entering_district,
    F.text == "Пропустить район",
)
async def skip_district(
    message: Message,
    state: FSMContext,
) -> None:
    await state.update_data(district=None)
    await ask_for_name(message, state)


@router.message(ApplicationStates.entering_district, F.text)
async def process_district(
    message: Message,
    state: FSMContext,
) -> None:
    district = message.text.strip()

    if len(district) < 2 or len(district) > 100:
        await message.answer(
            "Пожалуйста, укажите район (от 2 до 100 символов) "
            "или нажмите «Пропустить район».",
            reply_markup=get_skip_district_keyboard(),
        )
        return

    await state.update_data(district=district)
    await ask_for_name(message, state)


@router.message(ApplicationStates.entering_district)
async def invalid_district(message: Message) -> None:
    await message.answer(
        "Пожалуйста, укажите район текстовым сообщением "
        "или нажмите «Пропустить район».",
        reply_markup=get_skip_district_keyboard(),
    )


@router.message(ApplicationStates.entering_name, F.text)
async def process_name(
    message: Message,
    state: FSMContext,
) -> None:
    customer_name = message.text.strip()

    if len(customer_name) < 2 or len(customer_name) > 100:
        await message.answer(
            "Пожалуйста, укажите имя (от 2 до 100 символов).",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(customer_name=customer_name)
    await state.set_state(ApplicationStates.entering_contact)

    await message.answer(
        f"Приятно познакомиться, {escape(customer_name)}! 😊\n\n"
        "Теперь укажите номер телефона для связи с вами.\n\n"
        "Вы можете написать его самостоятельно "
        "или воспользоваться кнопкой ниже.",
        reply_markup=get_contact_keyboard(),
    )


@router.message(ApplicationStates.entering_name)
async def invalid_name(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте своё имя обычным текстовым сообщением.",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(ApplicationStates.entering_contact, F.contact)
async def process_contact(
    message: Message,
    state: FSMContext,
) -> None:
    contact = message.contact

    if (
        message.from_user is not None
        and contact.user_id is not None
        and contact.user_id != message.from_user.id
    ):
        await message.answer(
            "Пожалуйста, отправьте именно свой контакт "
            "или введите номер телефона вручную.",
            reply_markup=get_contact_keyboard(),
        )
        return

    phone = contact.phone_number

    if not is_valid_phone(phone):
        await message.answer(
            "Не удалось распознать номер телефона. "
            "Пожалуйста, введите его вручную.",
            reply_markup=get_contact_keyboard(),
        )
        return

    await finish_contact_step(message, state, phone)


@router.message(ApplicationStates.entering_contact, F.text)
async def process_phone(
    message: Message,
    state: FSMContext,
) -> None:
    phone = message.text.strip()

    if not is_valid_phone(phone):
        await message.answer(
            "Пожалуйста, проверьте номер телефона.\n\n"
            "Укажите от 7 до 15 цифр. Можно использовать "
            "+, пробелы, скобки и дефисы.\n\n"
            "Например: +4915112345678",
            reply_markup=get_contact_keyboard(),
        )
        return

    await finish_contact_step(message, state, phone)


@router.message(ApplicationStates.entering_contact)
async def invalid_contact(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте контакт через кнопку Telegram "
        "или введите номер телефона текстом.",
        reply_markup=get_contact_keyboard(),
    )


@router.message(
    ApplicationStates.accepting_privacy,
    F.text == "✅ Согласен на обработку данных",
)
async def accept_privacy(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    if message.from_user is None:
        await message.answer(
            "Не удалось определить пользователя. Попробуйте ещё раз."
        )
        return

    try:
        order = create_order(
            telegram_user_id=message.from_user.id,
            service_type=data["service_type"],
            problem_description=data["problem_description"],
            city=data["city"],
            district=data.get("district"),
            customer_name=data["customer_name"],
            customer_contact=data["customer_contact"],
            photo_file_id=data.get("photo_file_id"),
            privacy_consent=True,
        )
    except Exception:
        logger.exception("Не удалось сохранить заявку")

        await message.answer(
            "К сожалению, произошла ошибка при сохранении заявки.\n"
            "Попробуйте немного позже или начните оформление заново."
        )
        await state.clear()
        return

    # The order is already saved. Notification failure must not undo it.
    try:
        await notify_admin(
            message=message,
            order=order,
            photo_file_id=data.get("photo_file_id"),
        )
    except Exception:
        logger.exception(
            "Заявка #%s сохранена, но уведомление администратору не отправлено",
            order.id,
        )

    await state.clear()

    await message.answer(
        "✅ Ваша заявка успешно оформлена!\n\n"
        f"Номер заявки: <b>#{order.id}</b>\n\n"
        "Спасибо! Мы получили ваши данные.",
        reply_markup=get_main_keyboard(),
    )


@router.message(
    ApplicationStates.accepting_privacy,
    F.text == "❌ Не согласен",
)
async def reject_privacy(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await message.answer(
        "Вы отказались от обработки персональных данных.\n\n"
        "Заявка не была сохранена.\n\n"
        "Если передумаете, вы сможете оформить её заново.",
        reply_markup=get_main_keyboard(),
    )


@router.message(ApplicationStates.accepting_privacy)
async def invalid_privacy_answer(message: Message) -> None:
    await message.answer(
        "Пожалуйста, выберите один из двух вариантов "
        "с помощью кнопок:\n\n"
        "✅ Согласен на обработку данных\n"
        "❌ Не согласен",
        reply_markup=get_privacy_keyboard(),
    )
