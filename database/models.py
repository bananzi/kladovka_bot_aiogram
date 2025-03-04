from sqlalchemy import BigInteger, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine


engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    tg_id = mapped_column(BigInteger, primary_key=True)


class Course(Base):
    __tablename__ = 'courses'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))  # Связь с пользователем
    course_id: Mapped[int] = mapped_column()  # Новый параметр: ID курса
    is_paid: Mapped[bool] = mapped_column(insert_default=True)

    payment_period: Mapped[int] = mapped_column()
    start_period: Mapped[str] = mapped_column(String(20))
    end_period: Mapped[str] = mapped_column(String(20))

    day_number: Mapped[int] = mapped_column()


class PrePayment(Base):
    __tablename__ = 'prepayments'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    need_period: Mapped[int] = mapped_column()


class TimeMailing(Base):
    __tablename__ = 'timeMailings'
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    time_hour = mapped_column(Integer)


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
