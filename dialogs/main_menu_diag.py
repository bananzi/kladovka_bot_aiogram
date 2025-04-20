from typing import Dict
from pathlib import Path
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.kbd import Button, Row, Url, Start, Cancel  # noqa: F401
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const

# Локальные
from dialogs.payment_diag import PaymentMenu
from dialogs.settings_diag import Settings
from dialogs.tp_diag import TPBot
from database import requests as rq

from utils.scheduler_func import remove_schedule_task
from utils import mailing
BASE_DIR = Path(__file__).resolve().parent.parent


async def test_clear_all(callback, button: Button,
                         dialog_manager: DialogManager):
    await remove_schedule_task(dialog_manager.dialog_data["user_id"])
    await rq.for_test_clear_courses(dialog_manager.dialog_data["user_id"])
    await rq.for_test_clear_TimeMailing(dialog_manager.dialog_data["user_id"])


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
        dialog_manager.dialog_data['already_recieved'] = False
    else:
        dialog_manager.dialog_data['is_paid'] = user_from_Courses.is_paid
        dialog_manager.dialog_data['already_recieved'] = user_from_Courses.already_received
        dialog_manager.dialog_data['is_testing'] = True if (user_from_Courses.payment_period == 3) and\
            (user_from_Courses.is_paid) else False
    return {}


def not_yet_testing(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возращает True, если пользователь не на тесте и не на оплаченном курсе.'''
    return not (data['dialog_data']["is_testing"] or data['dialog_data']["is_paid"])


def not_yet_paid(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возвращает True, если пользователь НЕ в оплаченном курсе.'''
    return not data['dialog_data']["is_paid"]


def user_already_in_course(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возвращает True, если есть запись, что он на каком-либо курсе, в т.ч. тестовый.'''
    return data['dialog_data']["is_paid"]


def may_send_answer(data: Dict, widget: Whenable, manager: DialogManager):
    '''Возвращает True, если пользователь уже получил сегодня задание, и теперь может отослать ответ.'''
    return data['dialog_data']["already_recieved"] and data["dialog_data"]["is_paid"]


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


async def start_settings_diag(callback, button: Button,
                              dialog_manager: DialogManager):
    '''Функция стартует диалог с настройками'''
    await dialog_manager.start(Settings.START, data=dialog_manager.dialog_data)


async def sub_set_payment(callback, button: Button,
                          dialog_manager: DialogManager):
    '''Функция для записи на пробный период.'''
    await rq.set_payment(dialog_manager.dialog_data['user_id'], course_id=0, duration_days_pay=3)
    await dialog_manager.start(state=PaymentMenu.SELECT_TIME)
    # await dialog_manager.switch_to(state=MainMenu.START, show_mode=ShowMode.SEND)


async def test_period_wind(callback, button: Button,
                           dialog_manager: DialogManager):
    '''Открывает окно пробного периода.'''
    await dialog_manager.switch_to(MainMenu.TEST_QUEST)


async def back_main(callback, button: Button,
                    dialog_manager: DialogManager):
    '''Возвращает в окно главного меню.'''
    await dialog_manager.switch_to(MainMenu.START)


async def testing_add_day(callback, button: Button, dialog_manager: DialogManager):
    '''Функция для ручного добавления дня курса в БД и моментальной отсылки задания'''
    # print(dialog_manager.dialog_data["user_id"])
    user_id = dialog_manager.dialog_data["user_id"]
    # await rq.add_day(user_id)
    await mailing.mailing(user_id)


class MainMenu(StatesGroup):
    START = State()
    TEST_QUEST = State()
    PRE_CHANGE_TIME = State()
    CHANGE_TIME = State()
    PRE_CHANGE_DAY = State()
    CHANGE_DAY = State()


main_menu = Dialog(
    Window(
        Const("Главное меню"),

        Row(
            Button(Const("Купить курс"), id="pay",
                   on_click=start_pay_diag),
            Url(Const("Тех.поддержка"), url=Const("https://t.me/kladovationDesign_bot")),
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
            Button(Const("Настройки"), id="change_time",
                   on_click=start_settings_diag, when=user_already_in_course),
        ),
        # Row(
        #     Button(Const("test text"),
        #            id="test_text",
        #            on_click=testing_add_day)
        # ),
        # Row(
        #     Button(Const("clear all"), id="clear_course",
        #            on_click=test_clear_all),
        # ),
        getter=get_id,
        state=MainMenu.START
    ),
    Window(
        StaticMedia(
            path=f"{BASE_DIR}/utils/tmp/Обложка 0_0.png"
        ),
        Const("Пробный период длится 3 дня.\n\n\
Далее ты сможешь выбрать дату старта, время и дни, когда будешь получать задания ⏰\n\n\
Помни, что задание можно выполнить только до 23:59 того дня, в которое ты его получил.\n\
Ты сможешь в любой момент перейти с пробного периода на платный курс.\n\n\
Давай начнем! 👾"),
        Button(Const("Начнём!"), id="trial", on_click=sub_set_payment),
        Button(Const("Вернуться в главное меню"),
               id='back_main', on_click=back_main),
        state=MainMenu.TEST_QUEST,
    ),
)
