# Импорты библиотек
import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# импорты локальных файлов
from utils import mailing
from database import requests as rq


schedule_logger = logging.getLogger('schedule')
schedule_logger.setLevel(level=logging.DEBUG)

scheduler = None


def initialize_scheduler():
    '''
    Инициализация модуля scheduler 
    '''

    global scheduler
    if scheduler is None:
        schedule_logger.info("Инициализация scheduler...")
        scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        scheduler.start()
        schedule_logger.info("Scheduler успешно запущен!")


async def import_scheduler_tasks():
    '''
    Импорт списка для рассылки из БД. Создание job для sheduler рассылки и обновления окончивших курс.
    '''
    list_jobs = await rq.get_schedules_list()
    for job in list_jobs:
        perenos = 0 if job[3] is None else 2
        await add_schedule_task(user_id=job[0], hour=job[1], minute=job[2], perenos=perenos, new_stop_until=job[3], new_day_sending=job[4])
    scheduler.add_job(rq.update_payments, trigger='cron',
                      hour=0, start_date=datetime.datetime.today()-datetime.timedelta(days=1))
    scheduler.print_jobs()


async def add_schedule_task(user_id, hour, minute, perenos: int, new_stop_until: str, new_day_sending: str):
    '''
    :tg_id: id пользователя для рассылки.
    :hour, minute: Выбранное время.
    :perenos: Отвечает за выбор пользователя по переносу отправки задания.
    :new_date: Новые дни старта рассылки/приостоновление рассылки до этой даты.
    :new_day_sending: Выбранные дни для рассылки заданий.

    Функция для добавления в рассылку пользователя по выбранному им времени.
    '''

    if perenos == 0:
        start = datetime.datetime.today()-datetime.timedelta(days=1)
    elif perenos == 1:
        start = datetime.datetime.today()+datetime.timedelta(days=1)
    else:
        day, month, year = map(int, new_stop_until.split("-"))
        start = datetime.datetime(year, month, day) - datetime.timedelta(days=1)

    job_id = f"job_{user_id}"
    scheduler.add_job(
        mailing.mailing,
        trigger='cron',
        hour=hour,
        minute=minute,
        day_of_week=new_day_sending,
        start_date=start,
        id=job_id,
        kwargs={"tg_id": user_id}
    )
    schedule_logger.info(f"Для пользователя {user_id} добавлена новая job: {scheduler.get_job(job_id)}")


async def remove_schedule_task(tg_id):
    '''
    :tg_id: id пользователя, у которого нужно удалить job рассылки.

    Функция удаляет job для данного пользователя.
    '''
    job_id = f"job_{tg_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        schedule_logger.info(f"Удалена старая job для пользователя {tg_id}")

async def update_schedule_task(tg_id, new_hour, new_minute, new_days_sending: set, new_stop_until: str, perenos: int = 0):
    '''
    :tg_id: id пользователя, у которого нужно обносить время рассылки.
    :new_hour: Новый выранный час.
    :new_minute: Новые выбранные минуты.
    :new_days: Новые дни для рассылки.
    :perenos: Переменная для обозначения какой тип переноса перед нами. `0` - без переноса, 
    `1` - перенос на завтра, `2` - перенос на новую дату.

    Функция позволяющая обновить время рассылки пользователя.
    '''
    new_days_sending = ", ".join(new_days_sending)
    # Удаляем старую задачу
    await remove_schedule_task(tg_id)

    # Обновляем запись в БД
    await rq.update_user_schedule(tg_id, new_hour, new_minute, new_days_sending, new_stop_until)

    # Добавляем новую задачу
    await add_schedule_task(tg_id, new_hour, new_minute, perenos, new_stop_until, new_days_sending)


async def update_schedule_time(tg_id, new_hour, new_minute, perenos):
    '''
    :tg_id: id пользователя, у которого нужно обновить время рассылки.
    :new_hour: Новый выранный час.
    :new_minute: Новые выбранные минуты.
    :perenos: Переменная для обозначения какой тип переноса перед нами. `0` - без переноса, 
    `1` - перенос на завтра

    Функция обновляющее только `время` рассылки.
    '''
    await rq.update_mailing_time(tg_id, new_hour, new_minute, perenos)

    await remove_schedule_task(tg_id)

    user_info = await rq.get_info_timemailing(tg_id, ["tg_id", "time_hour", "time_minute", "stop_until", "day_sending"])
    await add_schedule_task(
        user_id=user_info["tg_id"], hour=user_info["time_hour"],
        minute=user_info["time_minute"], perenos=perenos,
        new_stop_until=user_info["stop_until"],
        new_day_sending=user_info["day_sending"]
    )


async def update_schedule_days(tg_id, new_days_sending):
    '''
    :tg_id: id пользователя, у которого нужно обновить дни рассылки или приостановить высылку.
    :new_days: Новые дни для рассылки.

    Функция обновляющее только `дни` рассылки и/или приостановку рассылки.
    '''
    new_days_sending = ", ".join(new_days_sending)
    await rq.update_mailing_days(tg_id, new_days_sending)

    await remove_schedule_task(tg_id)

    user_info = await rq.get_info_timemailing(tg_id, ["tg_id", "time_hour", "time_minute", "stop_until", "day_sending"])
    await add_schedule_task(
        user_id=user_info["tg_id"],
        hour=user_info["time_hour"],
        minute=user_info["time_minute"],
        perenos=0 if user_info["stop_until"] == None else 2,
        new_stop_until=user_info["stop_until"],
        new_day_sending=user_info["day_sending"]
    )


async def update_schedule_stop_until(tg_id, new_stop_until):
    '''
    :tg_id: id пользователя, у которого нужно обновить дни рассылки или приостановить высылку.
    :new_stop_until: Дата до которой не будут присылаться задания.

    Функция обновляющее только `дни` рассылки и/или приостановку рассылки.
    '''

    await rq.update_mailing_stop_until(tg_id, new_stop_until)

    await remove_schedule_task(tg_id)

    user_info = await rq.get_info_timemailing(tg_id, ["tg_id", "time_hour", "time_minute", "stop_until", "day_sending"])
    await add_schedule_task(
        user_id=user_info["tg_id"], hour=user_info["time_hour"],
        minute=user_info["time_minute"], perenos=2,
        new_stop_until=user_info["stop_until"],
        new_day_sending=user_info["day_sending"]
    )


async def what_next_date_job(tg_id):
    next_date = scheduler.get_job(f"job_{tg_id}").next_run_time
    date_str = next_date.strftime("%d.%m.%Y")
    weekday_str = next_date.strftime("%A")
    return (date_str, weekday_str)