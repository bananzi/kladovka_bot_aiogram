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
from text import quest_1
from utils.scheduler_func import update_schedule_task


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
    '''Завершает диалог, чтобы пользователь смог отправить ответ на задание через diferent_hand.'''
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
        await message.answer("Некорректный формат времени. Введите в формате ЧЧ:ММ (например, 08:30).")
        return

    new_hour, new_minute = map(int, new_time.split(":"))
    
    tg_id = message.from_user.id  # ID пользователя
    await update_schedule_task(tg_id, new_hour, new_minute)  # Обновляем расписание

    await message.answer(f"Время рассылки изменено на {new_hour}:{new_minute}")
    await dialog_manager.switch_to(MainMenu.START)  # Возвращаем пользователя в меню

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
    await dialog_manager.switch_to(MainMenu.CHANGE_TIME)


async def test_text(callback, button: Button, dialog_manager: DialogManager):
    keyboard5 = InlineKeyboardBuilder()
    keyboard5.row(types.InlineKeyboardButton(
        text="Читать задание",
        url=quest_1[4]["url"])
    )
    await callback.message.answer_photo(
        FSInputFile(
            path=f"D:\\code\\podsobka\\utils\\tmp\\{quest_1[4]["photo"]}"),
        caption=quest_1[4]["text"],
        reply_markup=keyboard5.as_markup()
    )
    keyboard6 = InlineKeyboardBuilder()
    keyboard6.row(types.InlineKeyboardButton(
        text="Читать задание",
        url=quest_1[5]["url"])
    )
    await callback.message.answer_photo(
        FSInputFile(
            path=f"D:\\code\\podsobka\\utils\\tmp\\{quest_1[5]["photo"]}"),
        caption=quest_1[5]["text"],
        reply_markup=keyboard6.as_markup()
    )
    return


class MainMenu(StatesGroup):
    START = State()
    TEST_QUEST = State()
    CHANGE_TIME = State()


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
                   id="test_text", on_click=test_text)
        ),
        getter=get_id,
        state=MainMenu.START
    ),
    Window(
        StaticMedia(
            path="D:\\code\\podsobka\\utils\\tmp\\Пробный период.png"
        ),
        Const("Пробный период длится 3 дня. Выбери время, в которое тебе будет удобно получать задания⏰. Помни, что задание можно выполнить только до 23.59 того дня, в которое ты его получил.\nДавай начнем!"),
        Button(Const("Начнём!"), id="trial", on_click=sub_set_payment),
        Button(Const("Вернуться меню"), id='back_main', on_click=back_main),
        state=MainMenu.TEST_QUEST,
    ),
    Window(
        Const("Введи новое время в формате ЧЧ:ММ (например, 08:30):"),
        MessageInput(process_new_time),
        state=MainMenu.CHANGE_TIME
    ),
)
