from sqlalchemy import BigInteger, String, Integer, ForeignKey, Boolean
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
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    course_id: Mapped[int] = mapped_column()
    is_paid: Mapped[bool] = mapped_column(insert_default=True)

    payment_period: Mapped[int] = mapped_column()
    start_period: Mapped[str] = mapped_column(String(20))
    end_period: Mapped[str] = mapped_column(String(20))

    day_number: Mapped[int] = mapped_column()
    already_received: Mapped[bool] = mapped_column(insert_default=False)

    total_completed: Mapped[int] = mapped_column()
    already_completed: Mapped[bool] = mapped_column(insert_default=False)



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
    time_minute = mapped_column(Integer)
    day_sending = mapped_column(String(40), default="mon,tue,wed,thu,fri")
    stop_until = mapped_column(String(20), default=None)

class PromoCode(Base):
    __tablename__ = "promocodes"
    id = mapped_column(Integer, primary_key=True)
    code = mapped_column(String, unique=True)
    discount = mapped_column(Integer)  # или discount_rub
    one_time = mapped_column(Boolean, default=True)  # одноразовый для всех
    for_user_id = mapped_column(BigInteger, nullable=True)  # если промо для конкретного пользователя
    is_active = mapped_column(Boolean, default=True)

class UsedPromo(Base):
    __tablename__ = "used_promocodes"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(BigInteger)
    promocode_id = mapped_column(Integer, ForeignKey("promocodes.id"))

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
