from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ContentType, LabeledPrice, PreCheckoutQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities.modes import StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Cancel
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const

from database import requests as rq
from utils import mailing, scheduler_func
from text import all_quests

list_course = {1: "Как вдохновляться чужим?",}
PRICE_LIST = {
    1: LabeledPrice(label="1 Курс", amount=100_00),  # 500 RUB
}


async def get_id(dialog_manager: DialogManager, **kwargs):
    '''
    Геттер id при старте диалога и запихивает его в dialog_data.
    '''
    dialog_manager.dialog_data['user_id'] = dialog_manager.start_data['user_id']
    return {}


async def pre_pay(callback, button: Button,
                  dialog_manager: DialogManager):
    '''
    Старт процесса оплаты. Где идёт проверка на уже наличие курса и запуск основной функции.
    '''
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
    '''
    Процесс оплаты... Проверки... Высылка счёта...
    '''
    user_id = dialog_manager.dialog_data['user_id']
    course_id = dialog_manager.dialog_data.get("course_id")
    course_lenght = dialog_manager.dialog_data.get("course_lenght")

    if not course_id:
        await callback.message.answer("Ошибка: курс не выбран!")
        return

    if await rq.is_user_paid(user_id):
        await callback.message.answer("У тебя уже есть активная подписка!")
        return
    # Записываем оплату

    # ДЛЯ ОБХОДА ОПЛАТЫ ДЛЯ ТЕСТОВ!!!!!!
    ###
    await rq.set_payment(tg_id=user_id, course_id=course_id, duration_days_pay=course_lenght)
    await callback.answer(f"Оплата прошла успешно! Вы приобрели курс {course_id}.")
    await dialog_manager.start(PaymentMenu.SELECT_TIME, mode=StartMode.RESET_STACK)
    ###


    # Переключаем пользователя в окно выбора времени

    # await callback.message.bot.send_invoice(
    #     chat_id=callback.message.chat.id,
    #     title="Оплата курса",
    #     description="Подписка на курс",
    #     # ID курса передаётся в payload
    #     payload=(str(course_id)+"_"+str(course_lenght)),
    #     provider_token=config.payment_token.get_secret_value(),
    #     currency="RUB",
    #     prices=[PRICE_LIST[course_id]],
    #     start_parameter="payment",
    #     # Можно запрашивать email, если нужно
    # )


async def is_recieved_today():
    ...


async def process_selecting_time(message: Message,
                                 message_input: MessageInput,
                                 dialog_manager: DialogManager,):
    '''
    :message: Сообщение в формате "час:минуты" от пользователя.

    Проверки... Создание job для этого пользователя для рассылки. Запись в БД. Возврат в гравное меню.
    '''
    try:
        user_input_raw = message.text.strip()
        if len(user_input_raw.split(":")) != 2:
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «час:минуты».')
            return
        else:
            user_input = user_input_raw.split(":")

        if not (0 <= int(user_input[0]) <= 23):
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «час:минуты».')
            return
        elif not (0 <= int(user_input[1]) <= 59):
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «час:минуты».')
            return

    except ValueError as e:
        await message.answer(text='Введённое значение указано не в верном формате, проверь его')
        print(e)
        return
    user_id = message.from_user.id
    await rq.set_time_mailing(tg_id=user_id, selected_time_hour=user_input[0], selected_time_minute=user_input[1])
    await scheduler_func.update_schedule_task(tg_id=user_id, new_hour=int(user_input[0]), new_minute=int(user_input[1]), perenos=0, day=0)
    # await scheduler_func.add_schedule_task(tg_id=user_id, hour=int(user_input[0]), minute=int(user_input[1]))
    await mailing.mail_sertain_text(tg_id=user_id, text='Твоё время сохранено. Чтобы вернуться в главное меню отправьте команду /menu')
    await dialog_manager.reset_stack()


async def wind_zero(callback, button: Button, dialog_manager: DialogManager):
    await dialog_manager.switch_to(PaymentMenu.START)


async def wind_one(callback, button: Button,
                   dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 1
    dialog_manager.dialog_data['course_lenght'] = 7
    await dialog_manager.switch_to(PaymentMenu.FIRST_COURSE)

async def wind_about_one(callback, button: Button, dialog_manager: DialogManager):
    await dialog_manager.switch_to(PaymentMenu.ABOUT_FIRST)


async def wind_blank(callback, button: Button,
                     dialog_manager: DialogManager):
    dialog_manager.dialog_data['course_id'] = 0
    dialog_manager.dialog_data['course_lenght'] = 0

    await dialog_manager.switch_to(PaymentMenu.BLANK_COURSE)


class PaymentMenu(StatesGroup):
    START = State()
    FIRST_COURSE = State()
    ABOUT_FIRST = State()
    BLANK_COURSE = State()
    SELECT_TIME = State()


payment_menu = Dialog(
    Window(
        Const("У нас есть выбор из этих курсов: \n"),
        Const(f"{',\n'.join(f"«{item}»" for item in list_course.values())}\n"),
        Const(
            "Более подробное описание того, что ты получишь на каждом из курсов, ты сможешь увидеть, перейдя по одной из кнопок:"
        ),

        Button(Const(f"{list_course[1]}"), id="first_couse",
               on_click=wind_one),
        # Button(Const(f"{list_course[4]}"), id="blank_couse",
        #        on_click=wind_blank),
        Row(
            Cancel(Const("Вернуться в главное меню"))
        ),

        getter=get_id,
        state=PaymentMenu.START
    ),
    Window(
        StaticMedia(path="utils/tmp/Обложка 1_0.jpg"),
        Const(
            "Ты выбрал курс «Как вдохновляться чужим?». Здесь ты будешь ежедневно в выбранное тобой время получать задания."
        ),
        Row(
            Button(Const(text="Описание курса"), id="about_one", on_click=wind_about_one)
        ),
        Row(
            Button(Const("Оплатить"), id="payone", on_click=pre_pay),
        ),
        Row(
            Button(Const("Вернуться к выбору тарифа"),
                   id="payzero", on_click=wind_zero)
        ),
        state=PaymentMenu.FIRST_COURSE
    ),
    Window(
        StaticMedia(path="utils/tmp/Обложка 1_0.jpg"),
        Const(text=str(all_quests["quest_1"][0]["text"])),
        Row(
            Button(Const("Вернуться в меню курса"), id="cancel_about_one", on_click=wind_one)
            ),
        state=PaymentMenu.ABOUT_FIRST
    ),
    # Window(
    #     Const(
    #         "Ты выбрал курс ... . Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему ... ."
    #     ),
    #     Row(
    #         Button(Const("Оплатить"), id="payone", on_click=pre_pay),
    #     ),
    #     Row(
    #         Cancel(Const("Вернуться к выбору тарифа"))
    #     ),
    #     state=PaymentMenu.BLANK_COURSE
    # ),
    Window(
        Const("Выбери время, в которое тебе будет удобно получать задания⏰. \nПомни, что задание можно выполнить только до 23.59 того дня, в которое ты его получил.\n\n Для этого напиши время в формате «час:минуты» (Например 22:15), в которое ты хочешь, чтобы приходили задания"),
        MessageInput(process_selecting_time),
        state=PaymentMenu.SELECT_TIME
    )
)
