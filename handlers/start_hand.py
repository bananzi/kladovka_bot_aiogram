### Импорты необходимых библиотек
from aiogram import types, Router, F, Bot

from aiogram.filters.command import Command
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.types.callback_query import CallbackQuery 
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities.modes import StartMode, ShowMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
### импорты локальных файлов
from text import hello
import database.requests as rq
from dialogs.main_menu_diag import MainMenu


router = Router()
# Хэндлер на команду /start
@router.message(Command('start'))
async def cmd_start(message: types.Message, dialog_manager: DialogManager):
    await rq.set_user(message.from_user.id)
    if dialog_manager.has_context():
        await dialog_manager.done()

    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(
        text="Круто!",
        callback_data="kruto!")
    )

    await message.answer_photo(FSInputFile(f"D:\\code\\podsobka\\utils\\tmp\\{hello[1][1]}"), caption=f"{hello[1][0]}")
    await message.answer(text=f"{hello[2]}", reply_markup=markup.as_markup())
    return

    

@router.message(Command('menu'))
async def cmd_menu(message: types.Message, dialog_manager: DialogManager):
    try:
        await dialog_manager.done()
    except:
        pass
    await dialog_manager.start(MainMenu.START, data={"user_id": message.from_user.id}, show_mode=ShowMode.EDIT)

@router.callback_query(F.data == "kruto!")
async def hello_words(callback_query: CallbackQuery, bot: Bot):
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(
        text="Готов!",
        callback_data="gotov!")
    )
    # Убираем inline-кнопку, редактируя сообщение
    await callback_query.message.edit_reply_markup(reply_markup=None)
    # Отвечаем на callback, чтобы кнопка не оставалась выделенной
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer(text=f"{hello[3]}", reply_markup=markup.as_markup())

@router.callback_query(F.data == "gotov!")
async def hello_words_end(callback_query: CallbackQuery, dialog_manager: DialogManager, bot: Bot):
    # Убираем inline-кнопку, редактируя сообщение
    await callback_query.message.edit_reply_markup(reply_markup=None)
    # Отвечаем на callback, чтобы кнопка не оставалась выделенной
    await bot.answer_callback_query(callback_query.id)
    
    await dialog_manager.start(MainMenu.START, data={"user_id": callback_query.message.from_user.id}, show_mode=ShowMode.SEND) 