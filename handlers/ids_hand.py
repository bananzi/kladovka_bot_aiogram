# импорты локальных файлов
from keyboards import start_keyb, return_keyb

# Импорты необходимых библиотек
from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.types import Message

router = Router()

@router.message(Command("id"))
async def my_id(message: Message):
    await message.reply(text=f"Ваш id: {message.from_user.id}")

