from aiogram.fsm.state import State, StatesGroup

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Row, Cancel

class TPBot(StatesGroup):
    START = State()

tp_bot_menu = Dialog(
    Window(
        Const("Если у вас возникли технические проблемы, то советуем обратиться в чат поддержки"),
        Row(
            Cancel(Const("Вернуться в главное меню"))
        ),
        state=TPBot.START
    )
)