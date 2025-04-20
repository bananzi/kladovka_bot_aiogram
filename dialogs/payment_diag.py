import datetime
import re
from pathlib import Path
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, LabeledPrice, CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities.modes import StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Cancel, Checkbox

from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const

from config_reader import config
from database import requests as rq
from utils import scheduler_func
from text import all_quests

list_course = {1: "Как вдохновляться чужим?", }
PRICE_LIST = {
    1: LabeledPrice(label="1 Курс", amount=360_00),  # 500 RUB
}
BASE_DIR = Path(__file__).resolve().parent.parent
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


async def pre_pay(callback: CallbackQuery, button: Button,
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
    if await rq.is_user_in_test_period(user_id):
        await callback.message.answer("Сейчас ты проходишь пробный период,"
                                      " но уже можешь перейти на полный курс — просто оформи оплату и продолжай прокачку без ограничений 💪")
    # Тут будет процесс оплаты, а затем ->
    await process_payment(callback=callback, button=button, dialog_manager=dialog_manager)

    await callback.message.answer(text='Оплати квитанцию выше, затем ты сможешь продолжить')


async def process_payment(callback: CallbackQuery, button: Button,
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

    # # ДЛЯ ОБХОДА ОПЛАТЫ ДЛЯ ТЕСТОВ!!!!!!
    # ###
    # await rq.set_payment(tg_id=user_id, course_id=course_id, duration_days_pay=course_lenght)
    # await callback.answer(f"Оплата прошла успешно! Вы приобрели курс {course_id}.")
    # await dialog_manager.start(PaymentMenu.SELECT_TIME)
    # ###

    # Вызов оплаты

    await callback.message.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Оплата курса",
        description="Подписка на курс",
        # ID курса передаётся в payload
        payload=(str(course_id)+"_"+str(course_lenght)),
        provider_token=config.payment_token.get_secret_value(),
        currency="RUB",
        prices=[PRICE_LIST[course_id]],
        start_parameter="payment",
        # Можно запрашивать email, если нужно
    )


async def is_recieved_today():
    ...


async def process_selecting_time(message: Message,
                                 message_input: MessageInput,
                                 dialog_manager: DialogManager,):
    '''
    :message: Сообщение в формате "ЧЧ:ММ" от пользователя.

    Проверки... Создание job для этого пользователя для рассылки. Запись в БД. Продолжение на выбор дней рассылки.
    '''
    try:
        user_input_raw = message.text.strip()
        if len(user_input_raw.split(":")) != 2:
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «ЧЧ:ММ».')
            return
        else:
            user_input = user_input_raw.split(":")

        if not (0 <= int(user_input[0]) <= 23):
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «ЧЧ:ММ».')
            return
        elif not (0 <= int(user_input[1]) <= 59):
            await message.answer(text='Введённое значение указано не в верном формате, проверь его. Оно должно быть «ЧЧ:ММ».')
            return
    except ValueError as e:
        await message.answer(text='Введённое значение указано не в верном формате, проверь его')
        print(e)
        return

    user_id = message.from_user.id
    dialog_manager.dialog_data["user_time_hour"] = user_input[0]
    dialog_manager.dialog_data["user_time_minute"] = user_input[1]
    await message.answer(f"Готово! Мы сохранили время, в которое ты будешь получать задания: <b>{user_input[0]}:{user_input[1]}</b>")
    # await rq.set_time_mailing(tg_id=user_id, selected_time_hour=user_input[0], selected_time_minute=user_input[1])
    # await scheduler_func.update_schedule_task(tg_id=user_id, new_hour=int(user_input[0]), new_minute=int(user_input[1]), perenos=0, day=0)
    # await scheduler_func.add_schedule_task(tg_id=user_id, hour=int(user_input[0]), minute=int(user_input[1]))
    await dialog_manager.switch_to(PaymentMenu.SELECT_DAY_OF_WEEK, show_mode=ShowMode.DELETE_AND_SEND)


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
async def on_submit(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    selected_days = dialog_manager.dialog_data.get("selected_days", set())
    user_id = callback.from_user.id
    dialog_manager.dialog_data["user_id"] = user_id

    if len(selected_days) < 2:
        await callback.answer("Выбери минимум 2 дня!", show_alert=True)
        return
    
    await callback.message.answer(f"Готово! Мы изменили дни, в которые ты будешь получать задания: \
<b>{", ".join([TRANSLATE_DAYS[k] for k in TRANSLATE_DAYS if k in selected_days])}</b>")
    
    # Продолжаем работу, зная, что выбрано минимум 2 дня
    await dialog_manager.switch_to(PaymentMenu.SELECT_START_DATE, show_mode=ShowMode.DELETE_AND_SEND)


async def process_selecting_start_date(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    choice = button.widget_id.split("_")[1]
    if choice == "today":
        dialog_manager.dialog_data["user_selected_start_date"] = 0
        await callback.message.answer("Готово! Ты получишь первое задание как только придёт выбранное время.")
        await final_saving_time_and_days(message=callback.message, dialog_manager=dialog_manager)
    elif choice == "tomorrow":
        dialog_manager.dialog_data["user_selected_start_date"] = 1
        await callback.message.answer("Готово! Ты получишь первое задание не раньше, чем <b>завтра</b>.")
        await final_saving_time_and_days(message=callback.message, dialog_manager=dialog_manager)
    elif choice == "select":
        await dialog_manager.switch_to(PaymentMenu.SELECT_START_DATE_USER, show_mode=ShowMode.DELETE_AND_SEND)


async def process_selecting_start_date_user(message: Message,
                                            message_input: MessageInput,
                                            dialog_manager: DialogManager):
    new_stop_until = message.text.strip()
    if not re.match(r"^(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-\d{4}$", new_stop_until):
        await message.answer("Некорректный формат даты. Введи в формате ДД-ММ-ГГГГ (например, 05-07-2004).")
        return

    try:
        input_date = datetime.datetime.strptime(
            new_stop_until, "%d-%m-%Y").date()
        today = datetime.datetime.today().date()
        max_allowed_date = today + datetime.timedelta(days=7)
        if input_date > max_allowed_date:
            await message.answer("Ты ввёл дату больше, чем через 7 дней от сегодня. Выбери дату ближе.")
            return
    except ValueError:
        await message.answer("Некорректная дата. Проверь правильность написания и что этот день существует.")
        return
    dialog_manager.dialog_data["user_selected_start_date"] = new_stop_until

    await message.answer(f"Готово! Ты получишь первое задание не раньше <b>{input_date}</b>")
    await final_saving_time_and_days(message=message, dialog_manager=dialog_manager)


async def final_saving_time_and_days(message: Message, dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data["user_id"]
    user_time_hour = dialog_manager.dialog_data["user_time_hour"]
    user_time_minute = dialog_manager.dialog_data["user_time_minute"]
    selected_days = dialog_manager.dialog_data["selected_days"]
    selected_start_date = dialog_manager.dialog_data["user_selected_start_date"]
    try:
        perenos = selected_start_date if (selected_start_date == 0) or (selected_start_date == 1) else 2
        await scheduler_func.update_schedule_task(user_id, user_time_hour, user_time_minute, selected_days, selected_start_date, perenos)
        result_answer = f"Готово! Всё сохранено. Ты будешь получать задания в <b>{user_time_hour}:{user_time_minute}</b>"\
                             f" по <b>{", ".join([TRANSLATE_DAYS[k] for k in TRANSLATE_DAYS if k in selected_days])}</b>"
        if selected_start_date == 1:
            result_answer += " не раньше <b>завтрашнего дня</b>."
        elif selected_start_date == 0:
            result_answer += ", когда наступит выбранное время."
        else:
            result_answer += f" не раньше <b>{selected_start_date}</b>."
        
        await message.answer(result_answer)

        from dialogs.main_menu_diag import MainMenu
        await dialog_manager.start(state=MainMenu.START, data=dialog_manager.dialog_data,
                               mode=StartMode.RESET_STACK, show_mode=ShowMode.DELETE_AND_SEND)
    except Exception as e:
        print(f"У пользователя {user_id} возникла ошибка «{e}» при сохранении времени и дней рассылки.")
        await message.answer("Возникли проблемы при сохранении данных. Попробуй заполнить данные ещё раз. Если проблема останется, то, пожалуйста, обратись в техническую поддержку.")
        await dialog_manager.switch_to(PaymentMenu.SELECT_TIME, show_mode=ShowMode.DELETE_AND_SEND)
        #await message.answer("Возникли проблемы при сохранении данных. Попробуй изменить данные через настройки в главном меню. Если продолжатся ошибки или ты не видишь этой кнопки, то сообщи об этом в тех. поддержку.")
    
    


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
    SELECT_START_DATE = State()
    SELECT_START_DATE_USER = State()


payment_menu = Dialog(
    Window(
        Const("У нас есть выбор из этих курсов: \n"),
        Const(f"{',\n'.join(f"«{item}»" for item in list_course.values())}\n"),
        Const("Ты в любой момент сможешь перейти с пробного периода на платный курс.\n"
              " После оплаты тебе будет предложено выбрать время и дни получения заданий,"
              " а также дату до которой ты не будешь получать первое задание"),
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
        StaticMedia(path=str(BASE_DIR / "utils" / "tmp" / "Обложка 1_0.jpg")),
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
        StaticMedia(path=str(BASE_DIR / "utils" / "tmp" / "Обложка 1_0.jpg")),
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
    ),
    Window(
        Const("Выбери дату старта курса\n\n\
Ты можешь начать курс сегодня — если выбрал время позже текущего момента.\n\n\
А можешь запланировать старт на завтра или любую удобную дату в течение ближайшей недели 💫"),
        Button(Const("Сегодня"), id="start_today",
               on_click=process_selecting_start_date),
        Button(Const("Завтра"), id="start_tomorrow",
               on_click=process_selecting_start_date),
        Button(Const("Выбрать дату"), id="start_select",
               on_click=process_selecting_start_date),
        state=PaymentMenu.SELECT_START_DATE
    ),
    Window(
        Const("Теперь введи дату начала 📆\n"
              "Формат: <b>дд-мм-гггг</b>\n\n"
              "Важно: дата должна быть не позднее, чем через 7 дней от сегодня"),
        MessageInput(process_selecting_start_date_user),
        state=PaymentMenu.SELECT_START_DATE_USER
    )
)
