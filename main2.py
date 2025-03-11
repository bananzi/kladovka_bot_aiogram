# Импорты библиотек
import asyncio
import logging
import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import PreCheckoutQuery, Message, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import UnknownIntent

# импорты локальных файлов
from database import models
from database import requests as rq
from dialogs.payment_diag import PaymentMenu
from init_routers import initialise
from utils.mailing import mailing, mail_sertain_text
# импорт конфига
from config_reader import config


async def on_unknown_intent(event, dialog_manager: DialogManager):
    chat_id = event.update.callback_query.from_user.id
    logging.error("Restarting dialog: %s" +
                  f"; user: {chat_id}", event.exception)
    await mail_sertain_text(chat_id=chat_id,
                            text="Произошла небольшая ошибка на сервере, вероятнее всего бот был перезапущен. Если вы хотите увидеть приветсвенное сообщение, то введите /start. Если вы хотите войти в главное меню, то введите /menu. \n В случае, если проблема повторилась, советуем обратиться в техническую поддержку @Bananzi.")


async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


async def process_successful_payment(message: Message, dialog_manager: DialogManager):
    course_id = int(message.successful_payment.invoice_payload)
    user_id = message.from_user.id

    # Записываем оплату
    await rq.set_payment(tg_id=user_id, course_id=course_id, duration_days_pay=7)
    await message.answer(f"Оплата прошла успешно! Вы приобрели курс {course_id}.")

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

    await scheduler_func.import_scheduler_tasks()

    initialise(dp)
    dp.pre_checkout_query.register(
        pre_checkout_query)  # Регистрируем обработчик получаения оплаты
    dp.message.register(process_successful_payment, F.content_type == ContentType.SUCCESSFUL_PAYMENT)  # Регистрируем обработчик успешной оплаты

    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    from utils import scheduler_func
    asyncio.run(main())
