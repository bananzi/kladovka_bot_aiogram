import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
from pathlib import Path

from database import requests as rq
from text import quests
from config_reader import config


global bot
bot = Bot(token=config.bot_token.get_secret_value())


async def mail_sertain_text(chat_id, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        await asyncio.sleep(1)
    except Exception:
        await asyncio.sleep(1)


async def mail_sertain_photo(chat_id, path: str):
    BASE_DIR = Path(__file__).resolve().parent.parent
    source = f"{BASE_DIR}\\{path}"
    print(source)
    await bot.send_photo(chat_id=chat_id, photo=FSInputFile(path=source))

async def mail_file(id, file_path):
    await bot.send_document(
        chat_id=id,
        document=FSInputFile(path=file_path)
    )


async def mailing(tg_id):
    # 1) Сделать отправку задания лично одному человеку - done
    # 2) Сделать прибавку номера дня для одного человека ( await rq.add_day() ) - done
    # 3) Сделать обновление конца курса эффективным - done
    # 4) Сделать оповещение, что курс окончен для одног человека - done

    current_day = await rq.what_day_user(tg_id)
    really_end = await rq.it_user_end(tg_id)

    if not really_end:
        if quests[current_day]["photo"] != 0:
            await mail_sertain_photo(chat_id=tg_id, path=f"utils\\tmp\\{quests[current_day][1]}")
        await mail_sertain_text(chat_id=tg_id, text=quests[current_day][0])
        
        # await bot.close()  XX
        await rq.update_payments() 
        await rq.add_day(tg_id)
    else:
        await end_mailing(tg_id)



async def end_mailing(tg_id):
        await mail_sertain_text(chat_id=tg_id, text="Это последнее пробное задание, если вам понравился наш формат можем предложить вам перейти на окно оплаты в главном меню /menu")
