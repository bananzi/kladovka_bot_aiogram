from typing import Dict
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, Cancel  # noqa: F401
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const
from aiogram.types import FSInputFile
from aiogram_dialog.api.entities.modes import ShowMode

# Локальные
from dialogs.payment_diag import PaymentMenu
from dialogs.tp_diag import TPBot
from database import requests as rq

from utils.scheduler_func import update_schedule_task
from utils import mailing


async def get_id(dialog_manager: DialogManager, **kwargs):
    '''
    Геттер id при старте диалога из start_data. Проверка на наличие оплаченного курса у пользователя.
    Если так, то в диалоге меняются кнопки.
    '''
    dialog_manager.dialog_data['user_id'] = dialog_manager.start_data['user_id']
    user_from_Courses = await rq.get_user_in_course(dialog_manager.start_data['user_id'])
    if not user_from_Courses:
        dialog_manager.dialog_data['is_paid'] = False
        dialog_manager.dialog_data['is_testing'] = False
    else:
        dialog_manager.dialog_data['is_paid'] = user_from_Courses.is_paid
        dialog_manager.dialog_data['is_testing'] = True if user_from_Courses.payment_period == 3 else False
    return {}


def not_yet_testing(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возращает True, если пользователь не на тесте и не на оплаченном курсе.'''
    return not (data['dialog_data']["is_testing"] or data['dialog_data']["is_paid"])


def not_yet_paid(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возвращает True, если пользователь НЕ в оплаченном курсе.'''
    return not data['dialog_data']["is_paid"]


def may_send_answer(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возвращает True, если есть запись, что он на каком-лтбо курсе, в т.ч. тестовый.'''
    return data['dialog_data']["is_paid"]


async def done_main(callback, button: Button,
                    dialog_manager: DialogManager):
    '''Завершает диалог, чтобы пользователь смог отправить ответ на задание через diff_hand.'''
    await callback.message.delete()
    await callback.message.answer(text="Сейчас вы сможете отправить свой ответ на задание. Для возврата в главное меню ипользуйте команду /menu")
    await dialog_manager.done()


async def start_pay_diag(callback, button: Button,
                         dialog_manager: DialogManager):
    '''Функция стартует диалог с оплатой'''
    await dialog_manager.start(PaymentMenu.START, data=dialog_manager.dialog_data)


async def sub_set_payment(callback, button: Button,
                          dialog_manager: DialogManager):
    '''Функция для записи на пробный период.'''
    await rq.set_payment(dialog_manager.dialog_data['user_id'], course_id=0, duration_days_pay=3)
    await dialog_manager.start(state=PaymentMenu.SELECT_TIME)
    # await dialog_manager.switch_to(state=MainMenu.START, show_mode=ShowMode.SEND)


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

    # Обновляем расписание
    if perenos != 2:
        
        await update_schedule_task(tg_id, new_hour, new_minute, perenos, 0)
    else:

        dialog_manager.dialog_data["new_hour"] = new_hour
        dialog_manager.dialog_data["new_minute"] = new_minute
        await dialog_manager.switch_to(MainMenu.CHANGE_DAY)
        return
    await message.answer(f"Время рассылки изменено на {new_hour}:{new_minute}. ")

    # Возвращаем пользователя в меню
    await dialog_manager.switch_to(MainMenu.START)

async def process_new_time_and_day(message: Message,
                           message_input: MessageInput,
                           dialog_manager: DialogManager,):
    new_day = message.text.strip()
    if not re.match(r"^(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-\d{4}$", new_day):
        await message.answer("Некорректный формат даты. Введи в формате ДД-ММ-ГГГГ (например, 05-07-2004).")
        return
    dialog_manager.dialog_data["switch_day"] = new_day
    new_hour = dialog_manager.dialog_data["new_hour"]
    new_minute = dialog_manager.dialog_data["new_minute"]
    perenos = dialog_manager.dialog_data["switch_time"]
    tg_id = message.from_user.id  # ID пользователя
    await update_schedule_task(tg_id, new_hour, new_minute, perenos, new_day)

    await message.answer(f"Время рассылки изменено на {new_hour}:{new_minute}. А дата на {new_day}")
    await dialog_manager.switch_to(MainMenu.START)

async def test_period_wind(callback, button: Button,
                           dialog_manager: DialogManager):
    '''Открывает окно пробного периода.'''
    await dialog_manager.switch_to(MainMenu.TEST_QUEST)


async def back_main(callback, button: Button,
                    dialog_manager: DialogManager):
    '''Возвращает в окно главного меню.'''
    await dialog_manager.switch_to(MainMenu.START)


async def start_change_time(callback, button: Button, dialog_manager):
    '''Открывает окно изменения времени.'''
    await dialog_manager.switch_to(MainMenu.PRE_CHANGE_TIME)

async def pre_change_time(callback, button: Button, dialog_manager: DialogManager):
    print("kek_pre_change_time_1")
    perenos = button.widget_id.split("_")[1]
    dialog_manager.dialog_data['switch_time'] = perenos
    await dialog_manager.switch_to(MainMenu.CHANGE_TIME)

async def testing_add_day(callback, button: Button, dialog_manager: DialogManager):
    '''Функция для ручного добавления дня курса в БД и моментальной отсылки задания'''

    # print(dialog_manager.dialog_data["user_id"])
    user_id = dialog_manager.dialog_data["user_id"]
    # await rq.add_day(user_id)
    await mailing.mailing(user_id)


class MainMenu(StatesGroup):
    START = State()
    TEST_QUEST = State()
    CHANGE_TIME = State()
    PRE_CHANGE_TIME = State()
    CHANGE_DAY = State()


main_menu = Dialog(
    Window(
        Const("Главное меню"),

        Row(
            Button(Const("Купить курс"), id="pay",
                   on_click=start_pay_diag, when=not_yet_paid),
            Start(Const("Тех.поддержка"), id="help", state=TPBot.START),
        ),
        Row(
            Button(Const("Тестовый период"),
                   id="test_quest", on_click=test_period_wind, when=not_yet_testing),

        ),
        Row(
            Button(Const(text="Отправить ответ на задание"),
                   id="send", on_click=done_main, when=may_send_answer),
        ),
        Row(
            Button(Const("Изменить время рассылки"), id="change_time",
                   on_click=start_change_time, when=may_send_answer)
        ),
        Row(
            Button(Const("test text"),
                   id="test_text",
                   on_click=testing_add_day)
        ),
        getter=get_id,
        state=MainMenu.START
    ),
    Window(
        StaticMedia(
            path="D:\\code\\podsobka\\utils\\tmp\\Обложка 0_0.png"
        ),
        Const("Пробный период длится 3 дня. Выбери время, в которое тебе будет удобно получать задания⏰. Помни, что задание можно выполнить только до 23.59 того дня, в которое ты его получил.\nДавай начнем!"),
        Button(Const("Начнём!"), id="trial", on_click=sub_set_payment),
        Button(Const("Вернуться меню"), id='back_main', on_click=back_main),
        state=MainMenu.TEST_QUEST,
    ),
    Window(
        Const("Ты ещё не получал задание сегодня, поэтому ты можешь выбрать, когда получить задание: сегодня, завтра или выбери дату на выбор."),
        Button(Const("Сегодня"), id="perenos_0", on_click=pre_change_time),
        Button(Const("Завтра"), id="perenos_1", on_click=pre_change_time),
        Button(Const("Выбрать дату"), id="perenos_2", on_click=pre_change_time),
        state=MainMenu.PRE_CHANGE_TIME
    ),
    Window(
        Const("Введи новое время в формате ЧЧ:ММ (например, 08:30):"),
        MessageInput(process_new_time),
        state=MainMenu.CHANGE_TIME
    ),
    Window(
        Const("Выберите дату на которую ты хочешь перенести задание (Если укажешь дату до сегодняшней, то задания будут приходить как и прежде). Введи в формате ДД-ММ-ГГГГ (например, 05-07-2004)."),
        MessageInput(process_new_time_and_day),
        state=MainMenu.CHANGE_DAY
    )
)
