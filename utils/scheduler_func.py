# Импорты библиотек
import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# импорты локальных файлов
from utils.mailing import mailing, mail_sertain_text
from database import requests as rq
# импорт конфига
from config_reader import config


scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
schedule_logger = logging.getLogger('schedule')
schedule_logger.setLevel(level=logging.DEBUG)
scheduler.start()
#scheduler.print_jobs()


async def import_scheduler_tasks():
    list_jobs = await rq.get_schedules_list()
    for job in list_jobs:
        await add_schedule_task(tg_id=job[0], hour=job[1])
    scheduler.add_job(rq.update_payments, trigger='cron',
                 hour=0, start_date=datetime.datetime.today()-datetime.timedelta(days=1))
    
    scheduler.print_jobs()

async def add_schedule_task(tg_id, hour):
    scheduler.add_job(mailing, trigger='cron',
                 hour=hour, day_of_week='mon-fri',start_date=datetime.datetime.today()-datetime.timedelta(days=1), kwargs={"tg_id": tg_id})