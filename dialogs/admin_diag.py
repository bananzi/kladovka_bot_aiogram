
from os import remove
from datetime import date

from aiogram.fsm.state import State, StatesGroup
from typing import Any
from pathlib import Path


from aiogram import Bot
from aiogram_dialog import Dialog, Window, DialogManager, Data
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, Cancel
from aiogram_dialog.widgets.text import Const
from aiogram.types import CallbackQuery, Message


# from aiogram.fsm.context import FSMContext

from config_reader import config
from utils.mailing import mail_sertain_text, mail_file
from handlers import admin_download


bot = Bot(token=config.bot_token.get_secret_value())


class AdminDialog(StatesGroup):
    offline = State()
    START = State()
    download = State()


async def download(message: Message,
                   message_input: MessageInput,
                   dialog_manager: DialogManager,):
    '''Функция считывает сообщение админа для закачки архива и запускает соответсвующую функцию.'''
    await admin_download.download_zippp(message)
    return

admin_menu = Dialog(
    Window(
        Const(text='Здравствуйте админиcтратор, ваши полномочия: '),
        Start(Const("Загрузить все работы"),
              id="download", state=AdminDialog.download),

        state=AdminDialog.START
    ),
    Window(
        Const(text="Напишите даты в формате «гггг-мм-дд»_«гггг-мм-дд»"),
        MessageInput(download),
        state=AdminDialog.download
    )
)
