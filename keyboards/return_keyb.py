from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ReturnCallbackFactory(CallbackData, prefix="ret"):
    action: str


def get_return_keyboard_fab():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Вернуться на start", callback_data=ReturnCallbackFactory(action="returnStart")
    )
    builder.adjust(1)
    return builder.as_markup()
