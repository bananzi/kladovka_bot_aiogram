from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ContentType, LabeledPrice, PreCheckoutQuery, CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities.modes import StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Cancel, Checkbox

from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const, Format

from database import requests as rq
from utils import mailing, scheduler_func
from text import all_quests

list_course = {1: "Как вдохновляться чужим?", }
PRICE_LIST = {
    1: LabeledPrice(label="1 Курс", amount=100_00),  # 500 RUB
}

TRANSLATE_DAYS = {
    "mon": "Пн",
    "tue": "Вт",
    "wed": "Ср",
    "thu": "Чт",
    "fri": "Пт",
    "sat": "Сб",
    "sun": "Вс",
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
    await dialog_manager.start(PaymentMenu.SELECT_TIME)
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
    dialog_manager.dialog_data["user_time_hour"] = user_input[0]
    dialog_manager.dialog_data["user_time_minute"] = user_input[1]
    # await rq.set_time_mailing(tg_id=user_id, selected_time_hour=user_input[0], selected_time_minute=user_input[1])
    # await scheduler_func.update_schedule_task(tg_id=user_id, new_hour=int(user_input[0]), new_minute=int(user_input[1]), perenos=0, day=0)
    # await scheduler_func.add_schedule_task(tg_id=user_id, hour=int(user_input[0]), minute=int(user_input[1]))
    await dialog_manager.switch_to(PaymentMenu.SELECT_DAY_OF_WEEK)


# Обработчик для переключения состояния CheckBox
async def toggle_day(callback, button: Button, dialog_manager: DialogManager):
    # id кнопки соответствует обозначению дня: "mon", "tue", и т.д.
    day = button.widget_id
    # Получаем текущее множество выбранных дней из dialog_data (инициализируется как set)
    selected_days = dialog_manager.dialog_data.get("selected_days", set())
    if day in selected_days:
        selected_days.remove(day)
        new_state = False
        await callback.answer(f"День {TRANSLATE_DAYS[str(day)]} снят")
    else:
        selected_days.add(day)
        new_state = True
        await callback.answer(f"День {TRANSLATE_DAYS[str(day)]} выбран")
    dialog_manager.dialog_data["selected_days"] = selected_days
    # Обновляем визуальное состояние виджета, вызывая set_checked
    checkbox = dialog_manager.find(day)
    await checkbox.set_checked(new_state)
    # Обновляем окно для отображения изменений
    await dialog_manager.update(data=dialog_manager.dialog_data)


# Обработчик кнопки «Готово»
async def on_submit(callback, button: Button, dialog_manager: DialogManager):
    selected_days = dialog_manager.dialog_data.get("selected_days", set())
    user_id = callback.from_user.id
    dialog_manager.dialog_data["user_id"] = user_id

    if len(selected_days) < 2:
        await callback.answer("Выбери минимум 2 дня!", show_alert=True)
        return
    # Продолжаем работу, зная, что выбрано минимум 2 дня
    await final_saving_time_and_days(callback=callback, dialog_manager=dialog_manager)


async def final_saving_time_and_days(callback: CallbackQuery, dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data["user_id"]
    user_time_hour = dialog_manager.dialog_data["user_time_hour"]
    user_time_minute = dialog_manager.dialog_data["user_time_minute"]
    selected_days = dialog_manager.dialog_data["selected_days"]
    try:
        await scheduler_func.update_schedule_task(user_id, user_time_hour, user_time_minute, selected_days, 0, 0)
        await callback.message.answer("Твоё время и дни сохранены.")
    except Exception as e:
        print(
            f"У пользователя {user_id} возникла ошибка <<{e}>> при сохранении времени и дней рассылки.")
        await callback.answer("Возникли проблемы при сохранении данных. Попробуй изменить данные через настройки в главном меню. Если продолжатся ошибки или ты не видишь этой кнопки, то сообщи об этом в тех. поддержку.")
    from dialogs.main_menu_diag import MainMenu
    await dialog_manager.start(state=MainMenu.START, data=dialog_manager.dialog_data,
                               mode=StartMode.RESET_STACK, show_mode=ShowMode.DELETE_AND_SEND)


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
    SELECT_DAY_OF_WEEK = State()


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
            "Ты выбрал курс\n\
«Как вдохновляться чужим?»\n\n\
В этом курсе ты будешь на протяжении 7 дней получать задания в выбранное время и даты."
        ),
        Row(
            Button(Const(text="Описание курса"),
                   id="about_one", on_click=wind_about_one)
        ),
        Row(
            Button(Const("Купить курс"), id="payone", on_click=pre_pay),
        ),
        Row(
            Button(Const("Вернуться назад"),
                   id="payzero", on_click=wind_zero)
        ),
        state=PaymentMenu.FIRST_COURSE
    ),
    Window(
        StaticMedia(path="utils/tmp/Обложка 1_0.jpg"),
        Const(text=str(all_quests["quest_1"][0]["text"])),
        Row(Button(Const("Купить курс"), id="pay_from_about_one", on_click=pre_pay)),
        Row(
            Button(Const("Вернуться в меню курса"),
                   id="cancel_about_one", on_click=wind_one)
        ),
        state=PaymentMenu.ABOUT_FIRST
    ),
    # Window(
    #     Const(
    #         "Ты выбрал курс ... . Здесь ты будешь ежедневно в выбранное тобой время получать задания на тему ... ."
    #     ),
    #     Row(
    #         Button(Const("Купить курс"), id="payone", on_click=pre_pay),
    #     ),
    #     Row(
    #         Cancel(Const("Вернуться к выбору тарифа"))
    #     ),
    #     state=PaymentMenu.BLANK_COURSE
    # ),
    Window(
        Const("Выбери время, в которое тебе будет удобно получать задания ⏰\n\n\
Помни, что задание можно выполнить только до 23:59 того дня, в которое ты его получил.\n\n\
Для выбора напиши время в формате «час:минуты» (например, 22:07), в которое ты хочешь, чтобы приходили задания."),
        MessageInput(process_selecting_time),
        state=PaymentMenu.SELECT_TIME
    ),
    Window(
        Const("А теперь выбери дни, в которые тебе будет удобно получать задания ⏰\n\n\
Помни, что задание можно выполнить только до 23:59 того дня, в которое ты его получил.\n\n\
Для выбора выдели минимум два дня недели, пользуяюсь кнопками ниже."),
        Row(
            Checkbox(
                checked_text=Const("✅ Пн"),
                unchecked_text=Const("❌ Пн"),
                id="mon",
                default=False,
                on_click=toggle_day
            ),
            Checkbox(
                checked_text=Const("✅ Вт"),
                unchecked_text=Const("❌ Вт"),
                id="tue",
                default=False,
                on_click=toggle_day
            ),
            Checkbox(
                checked_text=Const("✅ Ср"),
                unchecked_text=Const("❌ Ср"),
                id="wed",
                default=False,
                on_click=toggle_day
            ),
        ),
        Row(
            Checkbox(
                checked_text=Const("✅ Чт"),
                unchecked_text=Const("❌ Чт"),
                id="thu",
                default=False,
                on_click=toggle_day
            ),
            Checkbox(
                checked_text=Const("✅ Пт"),
                unchecked_text=Const("❌ Пт"),
                id="fri",
                default=False,
                on_click=toggle_day
            ),
            Checkbox(
                checked_text=Const("✅ Сб"),
                unchecked_text=Const("❌ Сб"),
                id="sat",
                default=False,
                on_click=toggle_day
            ),
            Checkbox(
                checked_text=Const("✅ Вс"),
                unchecked_text=Const("❌ Вс"),
                id="sun",
                default=False,
                on_click=toggle_day
            ),
        ),
        Button(Const("Готово"), id="submit", on_click=on_submit),
        state=PaymentMenu.SELECT_DAY_OF_WEEK
    )
)
