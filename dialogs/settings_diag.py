from datetime import datetime, timedelta
import re


from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager

from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Checkbox

from aiogram_dialog.widgets.text import Const
from aiogram_dialog.api.entities.modes import ShowMode, StartMode

# Локальные
from database import requests as rq

from utils.scheduler_func import update_schedule_days, update_schedule_time, update_schedule_stop_until

TRANSLATE_DAYS = {
    "mon": "Пн",
    "tue": "Вт",
    "wed": "Ср",
    "thu": "Чт",
    "fri": "Пт",
    "sat": "Сб",
    "sun": "Вс",
}


async def get_from_start_data(dialog_manager: DialogManager, **kwargs):
    '''
    Геттер id при старте диалога из start_data. Проверка на наличие оплаченного курса у пользователя.
    Если так, то в диалоге меняются кнопки.
    '''
    dialog_manager.dialog_data.update(dialog_manager.start_data)
    return {}


async def get_true(dialog_manager: DialogManager, **kwargs):
    if await rq.is_already_recieved(dialog_manager.dialog_data["user_id"]):
        return {
            "already_recieved": True,
            "not_already_recieved": False
        }
    else:
        return {
            "already_recieved": False,
            "not_already_recieved": True
        }


async def back_main(callback, button: Button, dialog_manager: DialogManager):
    '''Возврат в главное меню'''
    from dialogs.main_menu_diag import MainMenu
    await dialog_manager.start(MainMenu.START, data=dialog_manager.dialog_data)


async def back_settings(callback, button: Button, dialog_manager: DialogManager):
    await dialog_manager.switch_to(Settings.START)


async def start_change_time(callback, button: Button, dialog_manager: DialogManager):
    '''Открывает окно изменения времени.'''
    await dialog_manager.switch_to(Settings.PRE_CHANGE_TIME)


async def start_pre_change_day(callback, button: Button, dialog_manager: DialogManager):
    '''Открывает окно выборов для работы с изменением дней рассылки.'''
    await dialog_manager.switch_to(Settings.PRE_CHANGE_DAYS)


async def start_change_stop_until(callback, button: Button, dialog_manager: DialogManager):
    '''Открывает окно для приостановки рассылки'''
    await dialog_manager.switch_to(Settings.CHANGE_STOP_UNTIL)


async def start_change_days(callback, button: Button, dialog_manager: DialogManager):
    '''Открывает окно для изменения дней рассылки'''
    await dialog_manager.switch_to(Settings.CHANGE_DAYS_OF_WEEK)


async def pre_change_time(callback, button: Button, dialog_manager: DialogManager):
    '''Делает предварительную обработку какую кнопку нажал пользователь, а затем запускает основное окно смены времени.'''
    perenos = button.widget_id.split("_")[1]
    dialog_manager.dialog_data['switch_time'] = perenos
    await dialog_manager.switch_to(Settings.CHANGE_TIME)


async def process_new_time(message: Message,
                           message_input: MessageInput,
                           dialog_manager: DialogManager,):
    '''
    :message: Время введённое пользователем

    Проверяет и обновляет время. Время должно быть в формате ЧЧ:ММ.
    '''
    new_time = message.text.strip()
    # Проверяем, корректен ли ввод
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", new_time):
        await message.answer("Некорректный формат времени. Введи в формате ЧЧ:ММ (например, 08:30).")
        return

    new_hour, new_minute = map(int, new_time.split(":"))
    perenos = int(dialog_manager.dialog_data["switch_time"])
    tg_id = message.from_user.id  # ID пользователя

    await update_schedule_time(tg_id, new_hour, new_minute, perenos)
    await message.answer(f"Готово! Мы изменили время, в которое ты будешь получать задания: <b>{new_time}</b>")
    # Возвращаем пользователя в меню
    await dialog_manager.switch_to(Settings.START)


async def process_new_stop_until(message: Message,
                                 message_input: MessageInput,
                                 dialog_manager: DialogManager,):
    '''
    :message: Дата введённая пользователем.

    Проверяет и обновляет отсрочку высылки заданий для пользователя.
    '''
    new_stop_until = message.text.strip()
    if not re.match(r"^(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-\d{4}$", new_stop_until):
        await message.answer("Некорректный формат даты. Введи в формате ДД-ММ-ГГГГ (например, 05-07-2004).")
        return

    try:
        input_date = datetime.strptime(new_stop_until, "%d-%m-%Y").date()
        today = datetime.today().date()
        max_allowed_date = today + timedelta(days=14)
        if input_date > max_allowed_date:
            await message.answer("Ты ввёл дату больше, чем через 14 дней от сегодня. Выбери дату ближе.")
            return
    except ValueError:
        await message.answer("Некорректная дата. Проверь правильность написания и что этот день существует.")
        return

    dialog_manager.dialog_data["switch_day"] = new_stop_until
    tg_id = message.from_user.id  # ID пользователя
    await update_schedule_stop_until(tg_id, new_stop_until)
    await message.answer(f"Готово! Ты получишь следующие после перерыва задание не раньше <b>«{input_date}»</b>. Увидимся!")
    # await message.answer(f"Время рассылки изменено на {new_hour}:{new_minute}. А дата на {new_day}")
    await dialog_manager.switch_to(Settings.START)


# Обработчик для переключения состояния CheckBox
async def toggle_day(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    # id кнопки соответствует обозначению дня: "mon", "tue", и т.д.
    day = button.widget_id
    # Получаем текущее множество выбранных дней из dialog_data (инициализируется как set)
    selected_days : set = dialog_manager.dialog_data.get("selected_days", set())
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
    checkbox : Checkbox = dialog_manager.find(day)
    await checkbox.set_checked(new_state)
    # Обновляем окно для отображения изменений
    await dialog_manager.update(data=dialog_manager.dialog_data)


async def on_submit(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    selected_days = dialog_manager.dialog_data.get("selected_days", set())
    user_id = callback.from_user.id
    dialog_manager.dialog_data["user_id"] = user_id

    if len(selected_days) < 2:
        await callback.answer("Выбери минимум 2 дня!", show_alert=True)
        return
    
    await callback.message.answer(f"Готово! Мы сохранили дни, в которые ты будешь получать задания: \
<b>{", ".join([TRANSLATE_DAYS[k] for k in TRANSLATE_DAYS if k in selected_days])}</b>")
    # Продолжаем работу, зная, что выбрано минимум 2 дня
    try:
        await update_schedule_days(user_id, selected_days)
        await callback.message.answer("Твой выбор дней сохранён.")
    except Exception as e:
        print(
            f"У пользователя {user_id} возникла ошибка <<{e}>> при изменении перерыва.")
        await callback.answer("Возникли проблемы при сохранении данных. Попробуй изменить данные через настройки в главном меню. Если продолжатся ошибки или ты не видишь этой кнопки, то сообщи об этом в тех. поддержку.")
    await dialog_manager.start(state=Settings.START, data=dialog_manager.dialog_data,
                               mode=StartMode.RESET_STACK, show_mode=ShowMode.DELETE_AND_SEND)


class Settings(StatesGroup):
    START = State()
    PRE_CHANGE_TIME = State()
    CHANGE_TIME = State()
    PRE_CHANGE_DAYS = State()
    CHANGE_STOP_UNTIL = State()
    CHANGE_DAYS_OF_WEEK = State()


settings = Dialog(
    Window(
        Const("Это настройки.\n\n\
Здесь ты можешь изменить время рассылки и дни, в которые ты хочешь получать задания.\n\
Также здесь ты можешь взять перерыв от заданий на небольшой срок."),
        Row(
            Button(Const("Смена времени рассылки"),
                   id="start_change_time", on_click=start_change_time)
        ),
        Row(
            Button(Const("Смена дней рассылки"),
                   id="start_pre_change_days", on_click=start_pre_change_day),
        ),
        Row(
            Button(Const("Взять перерыв"), id="start_change_stop_until_settings",
                   on_click=start_change_stop_until),
        ),
        Row(
            Button(Const("Вернуться в главное меню"),
                   id="back_main_menu_from_settings", on_click=back_main)
        ),
        getter=get_from_start_data,
        state=Settings.START
    ),
    Window(
        Const("Ты еще не получал задание сегодня.\n\n\
Ты можешь поменять время на сегодня ИЛИ на завтра (если меняешь на завтра, то сегодня задание уже не придет).",
              when="not_already_recieved"),
        Const("Ты уже получил задание сегодня, поэтому ты можешь выбрать время высылки задания, которое будет работать начиная с завтра.", when="already_recieved"),
        Row(
            Button(Const("Сегодня"), id="perenos_0",
                   on_click=pre_change_time, when="not_already_recieved"),
            Button(Const("Завтра"), id="perenos_1", on_click=pre_change_time),
        ),
        # Button(Const("Выбрать дату"), id="perenos_2", on_click=pre_change_time),
        Button(Const("Вернуть в главное меню"),
               id="return_main_from_settings", on_click=back_main),
        state=Settings.PRE_CHANGE_TIME,
        getter=get_true
    ),
    Window(
        Const("Введи новое время в формате ЧЧ:ММ (например, 08:07):"),
        MessageInput(process_new_time),
        state=Settings.CHANGE_TIME
    ),
    Window(
        Const("Здесь ты можешь изменить дни рассылки заданий, а также взять перерыв и перестать получать задания на некоторый срок."),
        Row(
            Button(Const("Изменить дни рассылки"),
                   id="start_change_days_settings", on_click=start_change_days)
        ),
        Row(
            Button(Const("Вернуться в настройки"),
                   id="back_settings", on_click=back_settings)
        ),
        state=Settings.PRE_CHANGE_DAYS
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
            )
        ),
        Button(Const("Готово"), id="submit", on_click=on_submit),
        state=Settings.CHANGE_DAYS_OF_WEEK
    ),
    Window(
        Const("Введи дату, до которой ты не хочешь получать задание включительно (Если укажешь дату до сегодняшней, то задания будут приходить как и прежде).\
Введи в формате ДД-ММ-ГГГГ (например, 05-07-2004).\n\n\
Максимальный срок на который ты можешь отложить задание - это две недели. Количество переносов неограниченно. \n\
Ты в любой момент можешь изменить свой выбор и получить задание раньше этой даты или позже."),
        MessageInput(process_new_stop_until),
        Button(Const("Вернуться в меню без изменений"), id="back_settings", on_click=back_settings),
        state=Settings.CHANGE_STOP_UNTIL
    )
)
