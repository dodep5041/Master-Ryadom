
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Оставить заявку")],
            [KeyboardButton(text="📋 Мои заявки")],
            [
                KeyboardButton(text="🔧 Наши услуги"),
                KeyboardButton(text="ℹ️ Как это работает"),
            ],
            [
                KeyboardButton(text="📞 Контакты"),
                KeyboardButton(text="🔒 Конфиденциальность"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите нужный раздел",
    )


def get_services_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🚰 Сантехника"),
                KeyboardButton(text="⚡ Электрика"),
            ],
            [
                KeyboardButton(text="🪑 Ремонт мебели"),
                KeyboardButton(text="🛠 Сборка мебели"),
            ],
            [KeyboardButton(text="🏠 Отделочные работы")],
            [KeyboardButton(text="🔨 Мелкий бытовой ремонт")],
            [KeyboardButton(text="📦 Другое")],
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите нужную услугу",
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите данные или отмените оформление",
    )


def get_customer_orders_keyboard(orders: list) -> ReplyKeyboardMarkup:
    keyboard = []

    for order in orders:
        keyboard.append(
            [KeyboardButton(text=f"📄 Заявка #{order.id}")]
        )

    keyboard.append([KeyboardButton(text="⬅️ Главное меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите заявку",
    )


def get_skip_photo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")],
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Отправьте фото или пропустите",
    )


def get_skip_district_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить район")],
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Укажите район или пропустите",
    )


def get_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Отправить мой номер",
                    request_contact=True,
                ),
            ],
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Отправьте номер телефона",
    )


def get_privacy_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Согласен на обработку данных")],
            [KeyboardButton(text="❌ Не согласен")],
            [KeyboardButton(text="❌ Отменить оформление")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Подтвердите своё решение",
    )
