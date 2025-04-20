import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pathlib import Path

from database import requests as rq
from text import all_quests
from config_reader import config
from utils import scheduler_func


global bot
bot = Bot(token=config.bot_token.get_secret_value(),
          default=DefaultBotProperties(
          parse_mode=ParseMode.HTML
          ))


async def mail_sertain_text(tg_id, text: str):
    '''
    :tg_id: id пользователя.
    :text: текст сообщения.

    Функция отправляет заданный текст заданному пользователю.
    '''
    try:
        await bot.send_message(chat_id=tg_id, text=text)
        await asyncio.sleep(1)
    except Exception:
        await asyncio.sleep(1)


async def mail_sertain_photo(chat_id, path: str):
    '''
    :tg_id: id пользователя.
    :path: путь до файла с фото без корневой папки проекта.

    Функция отправляет заданное фото заданному пользователю.
    '''
    BASE_DIR = Path(__file__).resolve().parent.parent
    source = f"{BASE_DIR}/{path}"
    # print(source)
    await bot.send_photo(chat_id=chat_id, photo=FSInputFile(path=source))


async def mail_file(id, file_path):
    '''
    :tg_id: id пользователя.
    :file_path: путь до файла фиг знает в каком формате.

    Функция отправляет заданный файл заданному пользователю.
    '''
    await bot.send_document(
        chat_id=id,
        document=FSInputFile(path=file_path)
    )


async def mail_and_text_photo_url(tg_id, quest, current_day):
    '''
    :tg_id: id пользователя для отправки
    :quest: словарь с необходимым курсом
    :current_day: текущий день(=номер задания)

    Отсылает пользователю сообщение с картинкой и кнопкой-ссылкой
    '''
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="Читать задание",
        url=quest[current_day]["url"])
    )
    BASE_DIR = Path(__file__).resolve().parent.parent
    await bot.send_photo(
        chat_id=tg_id,
        photo=FSInputFile(
            path=f"{BASE_DIR}/utils/tmp/{quest[current_day]["photo"]}"),
        caption=quest[current_day]["text"],
        reply_markup=keyboard.as_markup()
    )


async def mailing(tg_id):
    '''
    :tg_id: id пользователя для отправки ему задания

    Отправляет задание пользователю исходя из дня на курсе.
    '''
    # 1) Сделать отправку задания лично одному человеку - done
    # 2) Сделать прибавку номера дня для одного человека ( await rq.add_day() ) - done
    # 3) Сделать обновление конца курса эффективным - done
    # 4) Сделать оповещение, что курс окончен для одног человека - done
    current_day = await rq.what_day_user(tg_id)
    really_end = await rq.it_user_end(tg_id)
    quest = all_quests[f"quest_{await rq.info_user_in_course(tg_id)}"]
    #print(quest)
    has_photo = True if quest[current_day]["photo"] != 0 else False
    has_url = True if quest[current_day]["url"] != 0 else False

    if not really_end:
        if has_photo and has_url:
            await mail_and_text_photo_url(tg_id=tg_id, quest=quest, current_day=current_day)
        if not (has_photo and has_url):
            await mail_sertain_text(tg_id=tg_id, text="Если увидели это, напишите @Bananzi")
        await rq.set_already_received(tg_id)
        
        await rq.add_day(tg_id)
    elif quest == all_quests["quest_0"]:
        await end_mailing_probn(tg_id)
        await scheduler_func.remove_schedule_task(tg_id)
        await rq.remove_user_schedule(tg_id)
    else:
        await end_mailing(tg_id)
        await scheduler_func.remove_schedule_task(tg_id)
        await rq.remove_user_schedule(tg_id)


async def end_mailing_probn(tg_id):
    '''
    Отправка пользователю оповещения, что пробный курс завершён.
    '''
    await mail_sertain_text(tg_id=tg_id, text="Это было финальное задание из пробного курса 🎉\n\n\
Если тебе понравилось — выбирай один из других курсов в боте. Мы будем рады продолжить путь вместе и помогать тебе расти дальше 💡")
    if await rq.is_user_completed_all(tg_id):
        await send_promo(tg_id, is_probn=True)

async def end_mailing(tg_id):
    '''
    Отправка пользователю оповещения, что его курс завершён (Кроме пробного).
    '''
    await mail_sertain_text(tg_id=tg_id, text="Это было финальное задание 🎉\n\n\
Если тебе понравилось — выбирай один из других курсов в боте. Мы будем рады продолжить путь вместе и помогать тебе расти дальше 💡")
    if await rq.is_user_completed_all(tg_id):
        await send_promo(tg_id, is_probn=False)

async def send_promo(tg_id, is_probn):
    '''
    :tg_id: id пользователя для которого делаем и отсылаем промокод.
    '''

    tmp_promo = await rq.auto_create_promocode(discount=100, one_time=True, for_user_id=tg_id, prefix=f"{tg_id}-")
    if is_probn:
        result = f"Поздравляю!\n\
Ты закончил тестовый период! Ты прислал ответы на все задания, поэтому получаешь скидку на наш любой курс! \
Вот твой промокод: <code>{tmp_promo}</code> (Ты можешь его скопировать, нажав на него)."
    else:
        result = f"Поздравляю!\n\
Ты закончил наш первый курс! Ты прислал ответы на все задания, поэтому получаешь скидку на наш любой другой курс! \
Они уже в разработке, поэтому готовься к скорому продолжению самосовершенствования! \
Вот твой промокод: <code>{tmp_promo}</code> (Ты можешь его скопировать, нажав на него)."
    await mail_sertain_text(tg_id=tg_id, text=result)