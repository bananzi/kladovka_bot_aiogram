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
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import UnknownIntent

# импорты локальных файлов

from database import models
from database import requests as rq
from dialogs.payment_diag import PaymentMenu
from init_routers import initialise
from utils.scheduler_func import initialize_scheduler, import_scheduler_tasks
from utils.mailing import mail_sertain_text
# импорт конфига
from config_reader import config


async def on_unknown_intent(event, dialog_manager: DialogManager):
    '''
    Обработка моментов, когда пользователь тыкает на кнопку после перезапуска бота. (Может ещё что вылавливает)
    '''
    chat_id = event.update.callback_query.from_user.id
    logging.error("Restarting dialog: %s" +
                  f"; user: {chat_id}", event.exception)
    await mail_sertain_text(tg_id=chat_id,
                            text="Произошла небольшая ошибка на сервере, вероятнее всего бот был перезапущен. Если ты хочешь увидеть приветсвенное сообщение, то введи /start. Если ты хочешь войти в главное меню, то введи /menu. \n В случае, если проблема повторилась, советуем обратиться в техническую поддержку.")


async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    '''
    Проверка оплаты от телеграмма
    '''
    await pre_checkout_query.answer(ok=True)


async def process_successful_payment(message: Message, dialog_manager: DialogManager):
    '''
    Процесс после оплаты. Мы заносим в БД купленный пользователем номер курса.\n
    И даём ему выбрать время в окне PaymentMenu.SELECT_TIME
    '''
    course_id, course_lenght = map(
        int, message.successful_payment.invoice_payload.split("_"))
    user_id = message.from_user.id

    # Записываем оплату
    await rq.set_payment(tg_id=user_id, course_id=course_id, duration_days_pay=course_lenght)
    await message.answer(f"Оплата прошла успешно! Ты приобрёл курс {course_id}.")
    promo_id = dialog_manager.dialog_data.get("promo_id")
    if promo_id:
        await rq.mark_promocode_used(user_id, promo_id)
    # Переключаем пользователя в окно выбора времени
    await dialog_manager.start(PaymentMenu.SELECT_TIME, mode=StartMode.RESET_STACK)


async def main():
    await models.async_main()
    # print(await rq.get_paid_user_id_day(11))

    # Объект бота
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    # Диспетчер
    dp = Dispatcher()

    initialize_scheduler()
    logging.info("Импорт задач в scheduler...")
    await import_scheduler_tasks()
    logging.info("Импорт завершён!")

    initialise(dp)
    dp.pre_checkout_query.register(
        pre_checkout_query)  # Регистрируем обработчик получаения оплаты
    dp.message.register(process_successful_payment,
                        # Регистрируем обработчик успешной оплаты
                        F.content_type == ContentType.SUCCESSFUL_PAYMENT)

    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
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
