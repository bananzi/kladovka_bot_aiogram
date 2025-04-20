from database.tp_models import async_session
from database.tp_models import User
from sqlalchemy import select, update, and_, delete


async def create_question(tg_id, text):
    '''
    :tg_id: id пользователя, которое мы записываем в таблицу User.
    :text: текст вопроса пользователя.
    '''
    try:
        async with async_session() as session:
            user = User(
                tg_id = tg_id,
                question = text
            )
            session.add(user)
            await session.commit()
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию


async def create_answer(text):
    '''
    :tg_id: id пользователя, которое мы записываем в таблицу User.
    :text: текст вопроса пользователя.
    '''
    try:
        async with async_session() as session:
            query = select(User.tg_id).where(User.question == text)
            data = await session.execute(query)
            chat_id = data.scalar()

            query2 = delete(User).where(User.question == text)
            data = await session.execute(query2 )
            await session.commit()

            return chat_id
    except Exception as e:
        await session.rollback()  # Откатываем сессию при ошибке
        raise e  # Поднимаем исключение дальше
    finally:
        await session.close()  # Закрываем сессию