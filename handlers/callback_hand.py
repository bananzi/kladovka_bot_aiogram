# импорты локальных файлов
from config_reader import config
from text import quests
from keyboards import start_keyb, return_keyb
# Импорты необходимых библиотек
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.filters.callback_data import CallbackData

router = Router()
@router.callback_query(start_keyb.StartCallbackFactory.filter())
async def callback_start(
        callback: types.CallbackQuery,
        callback_data: start_keyb.StartCallbackFactory
):
    returnButton = return_keyb.get_return_keyboard_fab()
    if callback_data.action == "payment":
        await callback.message.answer(text="Тут будут варианты тарифов или другие кнопки", reply_markup=returnButton)
    elif callback_data.action == "helpbot":
        await callback.message.answer(text="Тут будет информация о переходе в бота поддержки", reply_markup=returnButton)
    else:
        await callback.message.answer(text="Предлагаем вам ознакомиться с примером задания, которое вы получите на курсе")
        await callback.message.answer(text=quests[0], reply_markup=returnButton)
    await callback.answer()


# @router.callback_query(return_keyb.ReturnCallbackFactory.filter())
# async def callback_return_start(
#     callback: types.CallbackQuery,
#     callback_data: return_keyb.ReturnCallbackFactory
# ):
#     await callback.answer()
#     await mes_start(callback.message)
