# импорты локальных файлов
from filters.user_filters import UserInCourse
from filters.admin_filt import ItsAdmin
from database.requests import set_already_completed, add_total_completed
# Импорты необходимых библиотек
from aiogram import Bot, F, Router
from aiogram.types import Message
from datetime import datetime
import time
from pathlib import Path
from os import mkdir, path

dowload_anwers = {
    "ok": "Ответ загружен. Для выхода в меню используй команду /menu",
    "error": "Произошла ошибка загрузки, попробуй снова. Если ошибка повториться, пожалуйста, сообщи в техническую поддержку на вкладке /menu"
}

router = Router()
router.message.filter(UserInCourse())

def make_dir():
    now_datetime = str(datetime.today()).split(' ')
    BASE_DIR = Path(__file__).resolve().parent.parent
    download_path = f"{BASE_DIR}\\tmp\\{now_datetime[0]}"
    if not path.exists(download_path):
        mkdir(download_path)
    return now_datetime, download_path

@router.message(F.photo)
async def download_photo(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()
    try:
        await bot.download(
            message.photo[-1],
            destination=f"{download_path}\\{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.jpg"
        )
        await bot.send_message(chat_id=user_id, text=dowload_anwers["ok"])
        await add_total_completed(user_id)
        await set_already_completed(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers["error"])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке фото")

@router.message(F.text)
async def download_text(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()

    try:
        with open(f"{download_path}\\{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.txt", "w") as file:
            file.write(message.text)
        await bot.send_message(chat_id=user_id, text=dowload_anwers['ok'])
        await add_total_completed(user_id)
        await set_already_completed(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers['error'])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке текста")

@router.message(F.video)
async def download_video(message: Message, bot: Bot, user_id: int):
    now_datetime, download_path = make_dir()

    try:
        file_id = message.video.file_id 
        file = await bot.get_file(file_id) 
        await bot.download_file(file.file_path, f"{download_path}\\{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.mp4")
        await bot.send_message(chat_id=user_id, text=dowload_anwers['ok'])
        await add_total_completed(user_id)
        await set_already_completed(user_id)
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=dowload_anwers['error'])
        print(f"{user_id} получил ошибку <<{e}>> при загрузке видео")