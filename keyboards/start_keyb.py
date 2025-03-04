from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class StartCallbackFactory(CallbackData, prefix="fabstart"):
    action: str


def get_start_keyboard_fab():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Оплата", callback_data=StartCallbackFactory(action="payment")
    )
    builder.button(
        text="Тех.поддержка", callback_data=StartCallbackFactory(action="helpbot")
    )
    builder.button(
        text="Пробное задание", callback_data=StartCallbackFactory(action="freeQuest")
    )
    builder.adjust(2)
    return builder.as_markup()
