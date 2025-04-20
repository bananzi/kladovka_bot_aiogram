# Импорты библиотек
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import PreCheckoutQuery, Message, ContentType

# импорты локальных файлов

from database import tp_models
from database import tp_requests as rq
from init_tp import initialise
from utils.mailing import mail_sertain_text
# импорт конфига
from config_reader import config


bot = Bot(
        token=config.tp_bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )


async def main():
    await tp_models.async_main()
    # print(await rq.get_paid_user_id_day(11))

    # Объект бота
    
    # Диспетчер
    dp = Dispatcher()

    initialise(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Константы для авто-перезапуска
MAX_RETRIES = 5  # Максимальное количество попыток перезапуска
RETRY_DELAY = 5  # Задержка перед повторным запуском (в секундах)


async def run_bot():
    '''
    Запускает бота с автоматическим перезапуском при потере соединения.
    '''
    retries = 0
    while retries < MAX_RETRIES:
        try:
            await main()  # Запуск основной логики бота
        except TelegramNetworkError as e:
            retries += 1
            logging.error(
                f"Ошибка сети: {e}. Попытка {retries}/{MAX_RETRIES}. Перезапуск через {RETRY_DELAY} секунд...")
            # Ожидание перед повторным запуском
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {e}. Бот остановлен.")
            break  # Остановить бота при критической ошибке

    logging.error("Превышено количество попыток перезапуска. Остановка бота.")

if __name__ == "__main__":
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    asyncio.run(run_bot())