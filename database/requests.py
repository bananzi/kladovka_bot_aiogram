import datetime
from database.models import async_session
from database.models import User, Course, PrePayment, TimeMailing
from sqlalchemy import select, update, and_


async def set_user(tg_id):
    '''
    :tg_id: id пользователя, которое мы записываем в таблицу User, если его там нет.
    '''
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
    '''
    :tg_id: id проверяемого пользователя на наличие оплаты.\n
    Проверяет, есть ли у пользователя активная подписка.
    Возвращает True, если пользователь уже оплатил.
    '''
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
    '''
    :tg_id: id ползователя
    :course_id: id курса
    :duration_days_pay: длительность курса в днях

    Добавляет запись в БД о пользователе, который зачислен в выбранный курс.
    '''
    try:
        async with async_session() as session:
            already_pay = await session.scalar(select(Course).where(
                (Course.tg_id == tg_id) & (Course.course_id == course_id)
            ))
            if not already_pay:

                session.add(Course(
                    tg_id=tg_id,
                    is_paid=True,
                    course_id=course_id,
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
    '''
    В данный момент лишняя функция
    '''
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

async def set_time_mailing(tg_id, selected_time_hour: int,  selected_time_minute: int):
    '''
    :tg_id: id пользователя.
    :selected_time_hour: Выбранный пользователем час.
    :selected_time_minute: Выбранные пользователем минуты в часе.

    Добавляет/обновляет запись в БД TimeMailing данные о вемени для рассылки для пользователя.
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))

            if not user:
                session.add(TimeMailing(tg_id = tg_id, time_hour = selected_time_hour, time_minute = selected_time_minute))
            else:
                update_query = update(TimeMailing).where(TimeMailing.id == user.id).values(
                    {"time_hour": selected_time_hour,
                     "time_minute": selected_time_minute})
                await session.execute(update_query)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def add_day(tg_id):
    '''
    :tg_id: id пользователя

    Добавляет день ???
    '''
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
    '''
    В данный момент бесполезная функция
    '''
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
    '''
    В данный момент бесполезная функция
    '''
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
    '''
    :tg_id: id искомого пользователя.

    Возвращает строку с пользователем если он \"на курсе\". Иначе пустой возврат.
    '''
    try:
        async with async_session() as session:
            return await session.scalar(select(Course).where(Course.tg_id == tg_id))
    finally:
        await session.close()  # Закрываем сессию



async def update_payments():
    '''
    Обновляет данные в БД, если срок курса у пользоватя вышел, то ставит в столбец is_paid значение False.
    '''
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
    '''
    Возращает список с tg_id пользователей, у которых закончился курс.
    '''
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
    '''
    :tg_id: id искомого пользователя.

    Возращает True, если курс у пользователя закончился по количеству дней. Иначе False.
    '''
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
    '''
    :tg_id: id пользователя для узнавания дня.

    Возвращает номер дня курса для переданного пользователя.
    '''
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
    '''
    Возвращает список записанных времени рассылок в БД.

    :return: (tg_id, hour, minute)
    '''
    try:
        async with async_session() as session:
            list_current_job = []
            db_list_jobs = await session.scalars(select(TimeMailing))
            for user in db_list_jobs:
                list_current_job.append((user.tg_id, user.time_hour, user.time_minute))
            return list_current_job
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию

async def update_user_schedule(tg_id, new_hour, new_minute):
    '''
    :tg_id: id пользователя, которому нужно изменить время в БД
    :`new_hour, new_minute`: Новое время

    Функция обновляет время у пользователя в БД `TimeMailing`.
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                user.time_hour = new_hour
                user.time_minute = new_minute
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию
