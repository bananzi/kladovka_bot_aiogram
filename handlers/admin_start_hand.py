from typing import Any
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.filters.callback_data import CallbackData

from aiogram_dialog import setup_dialogs, DialogManager

from filters.admin_filt import ItsAdmin
from dialogs import admin_diag, main_menu_diag

router = Router()
router.message.filter(ItsAdmin())


@router.message(Command("start"))
async def start_adm(message: Message, name_admin: str, dialog_manager: DialogManager, id_admin: int):
    await message.answer(text=f"Здравствуйте администратор, {name_admin}")
    #router.include_router(admin_diag.admin_menu)
    #dialog_manager.update
    #setup_dialogs(router.parent_router)
    await dialog_manager.start(admin_diag.AdminDialog.START, data={"id_admin": id_admin})
    
