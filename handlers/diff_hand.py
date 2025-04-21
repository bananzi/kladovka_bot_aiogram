# импорты локальных файлов
from database import requests as rq
from filters.user_filters import UserInCourse
from text import all_quests

# Импорты необходимых библиотек
from aiogram import Bot, F, Router
from aiogram.types import Message
from datetime import datetime
from os import mkdir, path
from pathlib import Path

from utils.mailing import mail_sertain_text

dowload_anwers = {
    "ok": "Ответ загружен. Для выхода в меню используй команду /menu",
    "error": "Произошла ошибка загрузки, попробуй снова. Если ошибка повториться, пожалуйста, сообщи в техническую поддержку на вкладке /menu"
}

router = Router()
router.message.filter(UserInCourse())

def make_dir():
    now_datetime = str(datetime.today()).split(' ')
    BASE_DIR = Path(__file__).resolve().parent.parent
    download_path = f"{BASE_DIR}/tmp/{now_datetime[0]}"
    if not path.exists(download_path):
        mkdir(download_path)
    return now_datetime, download_path

@router.message(F.photo)
async def download_photo(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()
    try:
        await bot.download(
            message.photo[-1],
            destination=f"{download_path}/{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.jpg"
        )
        await bot.send_message(chat_id=user_id, text=dowload_anwers["ok"])
        await ending_answer(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers["error"])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке фото")

@router.message(F.text)
async def download_text(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()

    try:
        with open(f"{download_path}/{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.txt", "w") as file:
            file.write(message.text)
        await bot.send_message(chat_id=user_id, text=dowload_anwers['ok'])
        await ending_answer(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers['error'])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке текста")

@router.message(F.video)
async def download_video(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()

    try:
        file_id = message.video.file_id 
        file = await bot.get_file(file_id) 
        await bot.download_file(file.file_path, f"{download_path}/{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.mp4")
        await bot.send_message(chat_id=user_id, text=dowload_anwers['ok'])
        await ending_answer(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers['error'])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке видео")


async def ending_answer(tg_id):
    await rq.add_total_completed(tg_id)
    await rq.set_already_completed(tg_id)
    await last_answer(tg_id=tg_id)


async def last_answer(tg_id):
    really_end = await rq.it_user_end(tg_id)
    if really_end:
        quest = all_quests[f"quest_{await rq.info_user_in_course(tg_id)}"]
        if await rq.is_user_completed_all(tg_id):
            if quest == all_quests["quest_0"]:
                await send_promo(tg_id, is_probn=True)
            else:
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