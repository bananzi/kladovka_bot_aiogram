import datetime
from database.models import async_session
from database.models import User, Course, PrePayment, TimeMailing
from sqlalchemy import select, update, and_


async def set_user(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:

                session.add(User(tg_id=tg_id))
                await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def is_user_paid(tg_id) -> bool:
    """ Проверяет, есть ли у пользователя активная подписка. """
    try:
        async with async_session() as session:
            active_payment = await session.scalar(select(Course).where(
                (Course.tg_id == tg_id) & (Course.is_paid.is_(True))
            ))
            return active_payment is not None  # Если запись есть, значит подписка активна
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

async def set_payment(tg_id,course_id, duration_days_pay):
    try:
        async with async_session() as session:
            already_pay = await session.scalar(select(Course).where(
                (Course.tg_id == tg_id) & (Course.course_id == course_id)
            ))
            if not already_pay:

                session.add(Course(
                    tg_id=tg_id,
                    is_paid=True,
                    course_id=course_id,  # Новый параметр
                    payment_period=duration_days_pay,
                    start_period=datetime.date.today() + datetime.timedelta(days=1),
                    end_period=datetime.date.today() + datetime.timedelta(days=duration_days_pay),
                    day_number=0
                ))
                await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def set_pre_pay(tg_id, period):
    try:
        async with async_session() as session:
            user = await session.scalar(select(PrePayment).where(PrePayment.tg_id == tg_id))

            if not user:
                session.add(PrePayment(tg_id=tg_id, need_period=period))
            else:
                update_query = update(PrePayment).where(PrePayment.id == user.id).values(
                    {"need_period": period})
                await session.execute(update_query)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def set_time_mailing(tg_id, selected_time: int):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))

            if not user:
                session.add(TimeMailing(tg_id = tg_id, time_hour = selected_time))
            else:
                update_query = update(TimeMailing).where(TimeMailing.id == user.id).values(
                    {"time_hour": selected_time})
                await session.execute(update_query)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def add_day(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalars(select(Course).where(Course.tg_id == tg_id))
            for i in user:
                update_query = update(Course).where(Course.id == i.id).values(
                    {"day_number": i.day_number + 1})
            await session.execute(update_query)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию


async def get_paid_user_id_day(tg_id):
    all_paid_users = await get_all_paid_users()
    paid_users_id_day = []
    for user in all_paid_users:
        paid_users_id_day.append((user.tg_id, user.day_number))
    return paid_users_id_day

# async def get_paid_users_id_day():
#     all_paid_users = await get_all_paid_users()
#     paid_users_id_day = []
#     for user in all_paid_users:
#         paid_users_id_day.append((user.tg_id, user.day_number))
#     return paid_users_id_day


async def get_all_paid_users():
    try:
        async with async_session() as session:
            now_date = datetime.date.today() + datetime.timedelta(days=1)
            return await session.scalars(select(Course).where(Course.is_paid).where(Course.start_period <= now_date))

    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def get_user_in_course(tg_id):
    try:
        async with async_session() as session:
            return await session.scalar(select(Course).where(Course.tg_id == tg_id))
    finally:
        await session.close()  # Закрываем сессию



async def update_payments():
    try:
        async with async_session() as session:
           # users = await get_all_paid_users()
            now_date = datetime.date.today()
            update_query = update(Course).where(Course.end_period == now_date).values(
                {"is_paid": False})
            await session.execute(update_query)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def get_end_users():
    try:
        async with async_session() as session:
            end_users = []
            now_date = datetime.date.today()
            db_end_users = await session.scalars(select(Course).where(Course.end_period == now_date))
            for user in db_end_users:
                end_users.append(user.tg_id)
            return end_users
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def it_user_end(tg_id):
    try:
        async with async_session() as session:
            this_user = await session.scalars(select(Course).where(Course.tg_id == tg_id))
            for i in this_user:
                if int(i.day_number) == int(i.payment_period):
                    return True
            return False
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def what_day_user(tg_id):
    try:
        async with async_session() as session:
            db_current_user = await session.scalars(select(Course).where(Course.tg_id == tg_id))
            for i in db_current_user:
                current_day = int(i.day_number)
            return current_day
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def get_schedules_list():
    try:
        async with async_session() as session:
            list_current_job = []
            db_list_jobs = await session.scalars(select(TimeMailing))
            for user in db_list_jobs:
                list_current_job.append((user.tg_id, user.time_hour))
            return list_current_job
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию
