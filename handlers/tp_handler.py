### Импорты необходимых библиотек
from aiogram import types, Router, F, Bot
from pathlib import Path
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.types.callback_query import CallbackQuery 
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities.modes import ShowMode, StartMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
### импорты локальных файлов
from text import hello
import database.tp_requests as rq
from dialogs.main_menu_diag import MainMenu



id_admin = 605954613

router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    #print(message.chat.id)
    await message.answer("Привет! Здесь ты можешь описать свою проблему, а наши специалисты ответят тебе.")

@router.message((F.text) & F.chat.id != id_admin)
async def test(message: types.Message):
    id_user = message.chat.id
    await rq.create_question(tg_id=id_user, text=message.text)
 
    from tp_main2 import bot
    await bot.send_message(chat_id=id_admin, text=f'Вопрос от пользователя {id_user}')
    await bot.send_message(chat_id=id_admin, text=message.text)

    await message.answer(text='<i>Вопрос отправлен</i>')

@router.message((F.reply_to_message) & (F.chat.id == id_admin))
async def answer(message: types.Message):
    chat_id = await rq.create_answer(message.reply_to_message.text)
    from tp_main2 import bot
    await bot.send_message(chat_id=chat_id, text=f"<b>Тебе пришел ответ от техподдержки:</b>\n\n{message.text}")
    await message.answer("<i>Ответ отправлен</i>")