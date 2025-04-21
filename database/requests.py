import secrets
import string

import datetime
from database.models import async_session
from database.models import User, Course, PrePayment, TimeMailing, PromoCode, UsedPromo
from sqlalchemy import select, update, and_, delete
from sqlalchemy.exc import IntegrityError

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
    :tg_id: id проверяемого пользователя на наличие оплаты.
    
    Проверяет, есть ли у пользователя активная подписка на платный курс.
    Возвращает True, если пользователь уже оплатил.
    '''
    try:
        async with async_session() as session:
            active_payment = await session.scalar(select(Course).where(
                (Course.tg_id == tg_id) & (Course.is_paid.is_(True)) & (Course.course_id != 0))
            )
            return active_payment is not None  # Если запись есть, значит подписка активна
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

async def is_user_in_test_period(tg_id) -> bool:
    '''
    :tg_id: id проверяемого пользователя.

    Проверяет, на пробном курсе человек или нет.
    Возвращает True, если пользователь на пробном.
    '''
    try:
        async with async_session() as session:
            user_is_testing = await session.scalar(select(Course).where(
                (Course.tg_id == tg_id) & (Course.is_paid.is_(True) & (Course.course_id == 0))
            ))
            return user_is_testing is not None  # Если запись есть, значит подписка активна
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()


async def set_payment(tg_id, course_id, duration_days_pay):
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
                await session.execute(
                    delete(Course).where(Course.tg_id == tg_id)
                )
                session.add(Course(
                    tg_id=tg_id,
                    is_paid=True,
                    course_id=course_id,
                    payment_period=duration_days_pay,
                    start_period=datetime.date.today() + datetime.timedelta(days=1),
                    end_period=datetime.date.today() + datetime.timedelta(days=duration_days_pay),
                    day_number=1,
                    total_completed=0
                ))
                await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию


async def set_pre_pay(tg_id, period):
    '''
    В данный момент лишняя функция.
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
                session.add(TimeMailing(
                    tg_id=tg_id, time_hour=selected_time_hour, time_minute=selected_time_minute))
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
            # now_date = datetime.date.today()
            update_paid = update(Course).where(Course.payment_period < Course.day_number).values(
                {"is_paid": False})
            await session.execute(update_paid)

            update_recieved = update(Course).values(
                {
                    "already_received": False,
                    "already_completed": False
                }
            )
            await session.execute(update_recieved)

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
                if int(i.day_number) == (int(i.payment_period) + 1):
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


async def info_user_in_course(tg_id):
    '''
    :tg_id: id проверяемого пользователя

    Возвращает номер курса (course_id), на котором находится пользователь.
    '''
    try:
        async with async_session() as session:
            db_current_user = await session.scalars(select(Course).where(Course.tg_id == tg_id))
            for i in db_current_user:
                course_id = int(i.course_id)
            return course_id
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
                list_current_job.append(
                    (user.tg_id, user.time_hour, user.time_minute, user.stop_until, user.day_sending))
            return list_current_job
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию


async def update_user_schedule(tg_id, new_hour: str, new_minute: str, new_days, new_stop_until):
    '''
    :tg_id: id пользователя, которому нужно изменить время в БД
    :`new_hour, new_minute`: Новое время

    Функция обновляет время у пользователя в БД `TimeMailing`.
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if not user:
                session.add(TimeMailing(
                    tg_id=tg_id,
                    time_hour=new_hour,
                    time_minute=new_minute,
                    day_sending=new_days,
                    stop_until=new_stop_until if new_stop_until != 0 else None))
            else:
                user.time_hour = new_hour
                user.time_minute = new_minute
                user.day_sending = new_days if new_days != 0 else user.day_sending
                user.stop_until = new_stop_until if new_stop_until != 0 else None
            await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def update_mailing_time(tg_id, new_hour, new_minute, perenos=0):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                user.time_hour = new_hour
                user.time_minute = new_minute
                user.stop_until = (datetime.date.today() + \
                        datetime.timedelta(days=1)).strftime("%d-%m-%Y") if perenos == 1 else user.stop_until
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def update_mailing_days(tg_id, new_days_sending):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                user.day_sending = new_days_sending
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def update_mailing_stop_until(tg_id, new_stop_until):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                user.stop_until = new_stop_until
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def get_info_timemailing(tg_id, need_fields=None):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                all_fields = {
                    "tg_id": user.tg_id,
                    "time_hour": user.time_hour,
                    "time_minute": user.time_minute,
                    "day_sending": user.day_sending,
                    "stop_until": user.stop_until,
                }
                if need_fields:
                    return {field: all_fields[field] for field in need_fields if field in all_fields}
                else:
                    return all_fields
    finally:
        await session.close()  # Закрываем сессию


async def remove_user_schedule(tg_id):
    '''
    :tg_id: id пользователя запись времени рассылки, которого нужно удалить из таблицы TimeMailing

    Функция удаляет строку с переданным пользователем из `TimeMailing`.
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                await session.execute(
                    delete(TimeMailing).where(TimeMailing.tg_id == tg_id)
                )
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def set_already_received(tg_id):
    '''
    :tg_id: id пользователя, которому нужно поставить флаг, что он сегодня уже получил задание.

    Функция ставит флаг already_recieved на `True` для пользователя в `Course`
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            if user:
                user.already_received = True
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def is_already_recieved(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            if user:
                return user.already_received
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def set_already_completed(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            if user:
                user.already_completed = True
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def add_total_completed(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            if user:
                if not (user.already_completed):
                    user.total_completed += 1
                    await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def for_test_clear_courses(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            if user:
                await session.execute(
                    delete(Course).where(Course.tg_id == tg_id)
                )
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def for_test_clear_TimeMailing(tg_id):
    try:
        async with async_session() as session:
            user = await session.scalar(select(TimeMailing).where(TimeMailing.tg_id == tg_id))
            if user:
                await session.execute(
                    delete(TimeMailing).where(TimeMailing.tg_id == tg_id)
                )
                await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def get_promocode_by_code(code: str):
    '''
    :code: проверяемый код на существование и, что он активен
    '''
    try:
        async with async_session() as session:
            result = await session.scalar(
                select(PromoCode).where(PromoCode.code == code, PromoCode.is_active == True)  # noqa: E712
            )
            return result
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию

async def code_was_used(user_id: int, promo_id: int) -> bool:
    '''
    :user_id: id пользователя, применяющий промокод.
    :promo_id: id промокода, который хочет использовать пользователь.   

    Проверяет использовал ли пользователь уже этот промокод. Возвращает True, если это так, иначе False.
    '''
    try:
        async with async_session() as session:
            result = await session.scalar(
                select(UsedPromo).where(
                    UsedPromo.user_id == user_id,
                    UsedPromo.promocode_id == promo_id
                )
            )
            return result is not None
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию


async def mark_promocode_used(user_id: int, promo_id: int):
    '''
    :user_id: id пользователя, который уже использовал промокод.
    :promo_id: id промокода, который использовал пользователь.

    Помечает промокод использованным переданным пользователем.
    '''
    try:
        async with async_session() as session:
            usage = UsedPromo(user_id=user_id, promocode_id=promo_id)
            session.add(usage)
            await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию

async def create_promocode(code: str, discount: int, one_time=True, for_user_id=None):
    async with async_session() as session:
        promo = PromoCode(
            code=code,
            discount=discount,
            one_time=one_time,
            for_user_id=for_user_id,
            is_active=True,
        )
        session.add(promo)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return None  # Код уже существует
        return promo


def generate_promocode(length=8, prefix=""):
    charset = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(charset) for _ in range(length))
    return f"{prefix}{code}"


async def generate_unique_promocode(session, prefix="", length=8):
    while True:
        code = generate_promocode(length, prefix)
        exists = await session.scalar(
            select(PromoCode).where(PromoCode.code == code)
        )
        if not exists:
            return code


async def auto_create_promocode(discount, one_time=True, for_user_id=None, prefix=""):
    try:
        async with async_session() as session:
            code = await generate_unique_promocode(session, prefix)
            promo = PromoCode(
                code=code,
                discount=discount,
                one_time=one_time,
                for_user_id=for_user_id,
                is_active=True,
            )
            session.add(promo)
            await session.commit()
            return code
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию

async def is_user_completed_all(tg_id):
    '''
    :tg_id: id проверяемого пользователя в Course.

    Возвращает True, если пользователь отправил ответов ровно столько сколько и заданий всего.
    '''
    try:
        async with async_session() as session:
            user = await session.scalar(select(Course).where(Course.tg_id == tg_id))
            #print(user, user.total_completed, user.payment_period, user.total_completed == user.payment_period)
            if user and user.total_completed == user.payment_period:
                return True
            return False
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()  # Закрываем сессию