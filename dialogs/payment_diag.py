from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ContentType
from aiogram.types import LabeledPrice, PreCheckoutQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities.modes import StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Cancel
from aiogram_dialog.widgets.text import Const


from database import requests as rq
from utils import mailing, scheduler_func
from config_reader import config

list_course = {1: "1 Курс",
               2: "2 Курс",
               3: "3 Курс",
               4: "... Курс"}
PRICE_LIST = {
    1: LabeledPrice(label="1 Курс", amount=500_00),  # 500 RUB
    2: LabeledPrice(label="2 Курс", amount=1500_00),  # 1500 RUB
    3: LabeledPrice(label="3 Курс", amount=2500_00)   # 2500 RUB
}


async def get_id(dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data['user_id'] = dialog_manager.start_data['user_id']
    return {}


async def pre_pay(callback, button: Button,
                  dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data['user_id']
    course_id = dialog_manager.dialog_data['course_id']
    # Проверяем, есть ли активная подписка
    if await rq.is_user_paid(user_id):
        await callback.message.answer(text="У тебя уже есть активная подписка! Дождись её окончания, прежде чем покупать новый курс.")
        return
    # Тут будет процесс оплаты, а затем ->
    await process_payment(callback=callback, button=button, dialog_manager=dialog_manager)

    await callback.message.answer(text='Оплати квитанцию выше, затем ты сможешь продолжить')
    


async def process_payment(callback, button: Button,
                          dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data['user_id']
    course_id = dialog_manager.dialog_data.get("course_id")

    if not course_id:
        await callback.message.answer("Ошибка: курс не выбран!")
        return

    if await rq.is_user_paid(user_id):
        await callback.message.answer("У тебя уже есть активная подписка!")
        return

    await callback.message.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Оплата курса",
        description="Подписка на курс",
        payload=str(course_id),  # ID курса передаётся в payload
        provider_token=config.payment_token.get_secret_value(),
        currency="RUB",
        prices=[PRICE_LIST[course_id]],
        start_parameter="payment",
        # Можно запрашивать email, если нужно
    )

async def process_selecting_time(message: Message,
                                 message_input: MessageInput,
                                 dialog_manager: DialogManager,):
    user_input = message.text
    try:
        if not (0 <= int(user_input) <= 23):

            await message.answer(text='Введённое значение указано не в верном формате, проверьте')
            return
    except ValueError as e:
        await message.answer(text='Введённое значение указано не в верном формате, проверьте')
        print(e)
        return
    user_id = message.from_user.id
    await rq.set_time_mailing(tg_id=user_id, selected_time=user_input)
    await scheduler_func.add_schedule_task(tg_id=user_id, hour=int(user_input))
    await mailing.mail_sertain_text(chat_id=user_id, text='Ваше время сохранено.')
    await dialog_manager.done()


# Переделать логику оплаты, с учётом, что теперь у нас не периоды, а конкретные курсы
async def wind_one(callback, button: Button,
                   dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 1
    await dialog_manager.switch_to(PaymentMenu.FIRST_COURSE)


async def wind_two(callback, button: Button,
                   dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 2
    await dialog_manager.switch_to(PaymentMenu.SECOND_COURSE)


async def wind_three(callback, button: Button,
                     dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 3
    await dialog_manager.switch_to(PaymentMenu.THIRD_COURSE)


async def wind_blank(callback, button: Button,
                     dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 4
    await dialog_manager.switch_to(PaymentMenu.BLANK_COURSE)


class PaymentMenu(StatesGroup):
    START = State()
    FIRST_COURSE = State()
    SECOND_COURSE = State()
    THIRD_COURSE = State()
    BLANK_COURSE = State()
    SELECT_TIME = State()


payment_menu = Dialog(
    Window(
        Const("У нас есть выбор из этих курсов: \n"),
        Const(f"{',\n'.join(list_course.values())}"),
        Const(
            "Более подробное описание того, что ты получишь на каждом из курсов, ты сможешь увидеть, перейдя по одной из кнопок:"
        ),

        Button(Const(f"{list_course[1]}"), id="one_week",
               on_click=wind_one),
        Button(Const(f"{list_course[2]}"), id="one_mounth",
               on_click=wind_two),
        Button(Const(f"{list_course[3]}"), id="two_mounth",
               on_click=wind_three),
        Button(Const(f"{list_course[4]}"), id="two_mounth",
               on_click=wind_blank),
        Row(
            Cancel(Const("Вернуться в главное меню"))
        ),

        getter=get_id,
        state=PaymentMenu.START
    ),
    Window(
        Const(
            "Ты выбрал курс *Номер 1*. Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему *Тема 1*."
        ),
        Row(
            Button(Const("Оплатить"), id="payone", on_click=pre_pay),
        ),
        Row(
            Cancel(Const("Вернуться к выбору тарифа"))
        ),
        state=PaymentMenu.FIRST_COURSE
    ),
    Window(
        Const(
            "Ты выбрал курс *Номер 2*. Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему *Тема 2*."
        ),
        Row(
            Button(Const("Запишите меня"), id="paytwo", on_click=pre_pay),
        ),
        Row(
            Cancel(Const("Вернуться к выбору тарифа"))
        ),
        state=PaymentMenu.SECOND_COURSE
    ),
    Window(
        Const(
            "Ты выбрал курс *Номер 3*. Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему *Тема 3*."
        ),
        Row(
            Button(Const("Запишите меня"), id="paythree", on_click=pre_pay),
        ),
        Row(
            Cancel(Const("Вернуться к выбору тарифа"))
        ),
        state=PaymentMenu.THIRD_COURSE
    ), Window(
        Const(
            "Ты выбрал курс ... . Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему ... ."
        ),
        Row(
            Button(Const("Оплатить"), id="payone", on_click=pre_pay),
        ),
        Row(
            Cancel(Const("Вернуться к выбору тарифа"))
        ),
        state=PaymentMenu.BLANK_COURSE
    ),
    Window(
        Const("Выбери время, в которое тебе будет удобно получать задания⏰. \nПомни, что задание можно выполнить только до 23.59 того дня, в которое ты его получил.\n\n Для этого напиши одно число - час(от 0 до 23), в который ты хочешь, чтобы приходили задания"),
        MessageInput(process_selecting_time),
        state=PaymentMenu.SELECT_TIME
    )
)
