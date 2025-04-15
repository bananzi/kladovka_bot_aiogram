
# Импорты библиотек
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram_dialog import setup_dialogs
# импорты локальных файлов
from database import models, requests
# импорт конфига
from config_reader import config
# импорт диалогов
from dialogs import main_menu_diag, payment_diag, tp_diag, admin_diag, settings_diag

# импорт хендлеров
from handlers import start_hand, diff_hand, callback_hand, ids_hand, admin_start_hand, admin_download
# импорт мидлварей
from middlewares import slowpoke


def initialise(dp: Dispatcher):
    dp.include_routers(ids_hand.router, admin_start_hand.router, admin_download.router, start_hand.router,)
    dp.include_routers(main_menu_diag.main_menu)
    dp.include_routers(payment_diag.payment_menu)
    dp.include_routers(tp_diag.tp_bot_menu)
    dp.include_routers(settings_diag.settings)
    dp.include_router(admin_diag.admin_menu)
    dp.include_routers(callback_hand.router,
                        diff_hand.router)
    # Подключение диалогов
    
    
    
    setup_dialogs(dp)
    dp.message.middleware(slowpoke.SlowpokeMiddleware())