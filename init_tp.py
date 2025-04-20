from aiogram import Dispatcher


# импорт хендлеров
from handlers import tp_handler
# импорт мидлварей
from middlewares import slowpoke


def initialise(dp: Dispatcher):
    dp.include_routers(tp_handler.router)
    # Подключение диалогов

    dp.message.middleware(slowpoke.SlowpokeMiddleware())