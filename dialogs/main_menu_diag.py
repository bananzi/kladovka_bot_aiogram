
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Url, Start, Cancel  # noqa: F401
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const

from datetime import datetime
from os import mkdir, path
from pathlib import Path
from typing import Dict
# Локальные
from dialogs.payment_diag import PaymentMenu
from dialogs.settings_diag import Settings
from dialogs.tp_diag import TPBot
from database import requests as rq

from utils.scheduler_func import remove_schedule_task
from utils import mailing

BASE_DIR = Path(__file__).resolve().parent.parent


async def test_clear_all(callback: CallbackQuery, button: Button,
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

async def save_feedback(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    '''Запускает сохранение переданного отзыва'''
    try:
        user_id = dialog_manager.dialog_data["user_id"]
        now_datetime = str(datetime.today()).split(' ')
        download_path = f"{BASE_DIR}/tmp/feedback"
        if not path.exists(download_path):
            mkdir(download_path)
        full_path = Path(download_path + "/" + f"{user_id}-{now_datetime[1].replace(':','_').replace('.','_')}.txt")

        with full_path.open("w", encoding="utf-8") as file:
            file.write(message.text)

        await message.answer("Спасибо за твой отзыв, нам приятно получать обратную связь о нашем боте и курсах ❤️")
        await dialog_manager.switch_to(MainMenu.START)
    except Exception as e:
        await message.answer("Извини, но возникла ошибка при сохранении.\n\n \
Попробуй ещё раз с начала. Если не исправится, то напиши, пожалуйста, об этом в техподдержку.")
        print(f"У пользователя {user_id} возникла ошибка \"{e} при сохранении отзыва\"")


async def done_main(callback: CallbackQuery, button: Button,
                    dialog_manager: DialogManager):
    '''Завершает диалог, чтобы пользователь смог отправить ответ на задание через diff_hand.'''
    await callback.message.delete()
    await callback.message.answer(text="Сейчас вы сможете отправить свой ответ на задание. Для возврата в главное меню ипользуйте команду /menu")
    await dialog_manager.done()


async def start_pay_diag(callback: CallbackQuery, button: Button,
                         dialog_manager: DialogManager):
    '''Функция стартует диалог с оплатой'''
    await dialog_manager.start(PaymentMenu.START, data=dialog_manager.dialog_data)


async def start_settings_diag(callback: CallbackQuery, button: Button,
                              dialog_manager: DialogManager):
    '''Функция стартует диалог с настройками'''
    await dialog_manager.start(Settings.START, data=dialog_manager.dialog_data)


async def sub_set_payment(callback: CallbackQuery, button: Button,
                          dialog_manager: DialogManager):
    '''Функция для записи на пробный период.'''
    await rq.set_payment(dialog_manager.dialog_data['user_id'], course_id=0, duration_days_pay=3)
    await dialog_manager.start(state=PaymentMenu.SELECT_TIME)
    # await dialog_manager.switch_to(state=MainMenu.START, show_mode=ShowMode.SEND)


async def probn_period_wind(callback: CallbackQuery, button: Button,
                           dialog_manager: DialogManager):
    '''Открывает окно пробного периода.'''
    await dialog_manager.switch_to(MainMenu.TEST_QUEST)


async def feedback_wind(callback: CallbackQuery, button: Button,
                        dialog_manager: DialogManager):
    '''Открывает окно для отзыва'''
    await dialog_manager.switch_to(MainMenu.FEEDBACK)

async def back_main(callback, button: Button,
                    dialog_manager: DialogManager):
    '''Возвращает в окно главного меню.'''
    await dialog_manager.switch_to(MainMenu.START)

###Функцции для тестов
async def testing_add_day(callback, button: Button, dialog_manager: DialogManager):
    '''Функция для ручного добавления дня курса в БД и моментальной отсылки задания'''
    # print(dialog_manager.dialog_data["user_id"])
    user_id = dialog_manager.dialog_data["user_id"]
    # await rq.add_day(user_id)
    await mailing.mailing(user_id)

async def create_promo(callback, button, dialog_manager: DialogManager):
    await rq.auto_create_promocode(100, False, for_user_id=605954613)
    return
###

class MainMenu(StatesGroup):
    START = State()
    TEST_QUEST = State()
    PRE_CHANGE_TIME = State()
    CHANGE_TIME = State()
    PRE_CHANGE_DAY = State()
    CHANGE_DAY = State()
    FEEDBACK = State()


main_menu = Dialog(
    Window(
        Const("Главное меню"),

        Row(
            Button(Const("Купить курс"), id="pay",
                   on_click=start_pay_diag),
            
        ),
        Row(
            Button(Const("Тестовый период"),
                   id="test_quest", on_click=probn_period_wind, when=not_yet_testing),
        ),
        Row(
            Button(Const(text="Отправить ответ на задание"),
                   id="send", on_click=done_main, when=may_send_answer),
        ),
        Row(
            Button(Const("Настройки"), id="change_time",
                   on_click=start_settings_diag, when=user_already_in_course),
        ),
         Row(
            Url(Const("Наш канал"), url=Const("https://t.me/kladovka_design_bot")),
        ),
         Row(
            Url(Const("Тех.поддержка"), url=Const("https://t.me/KladovkaDesignHelp_bot")),
            Button(Const("Оставить отзыв"), id="feedback", on_click=feedback_wind)
        ),
        ##Кнопки для тестов
        # Row(
        #     Button(Const("create rand promo"), id="create_promo", on_click=create_promo)
        # ),
        # Row(
        #     Button(Const("test text"),
        #            id="test_text",
        #            on_click=testing_add_day)
        # ),
        # Row(
        #     Button(Const("clear all"), id="clear_course",
        #            on_click=test_clear_all),
        # ),
        ###
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
    Window(
        Const("Сейчас ты можешь написать свой отзыв о нашем боте и курсах.\n\n\
Мы постараемся учесть твои пожелания \
и исправить наши недочёты. Будем рады положительным отзывам о курсах и о самом боте (Во втором случае разработчику бота, возможно, будет выделена печенька 🍪)"),
        MessageInput(save_feedback),
        state=MainMenu.FEEDBACK
    )
)
