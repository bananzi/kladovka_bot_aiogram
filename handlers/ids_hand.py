# Импорты необходимых библиотек
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message

router = Router()

@router.message(Command("id"))
async def my_id(message: Message):
    await message.reply(text=f"Ваш id: {message.from_user.id}")

