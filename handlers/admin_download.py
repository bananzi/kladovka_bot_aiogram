# импорты локальных файлов
from filters.admin_filt import ItsAdmin
from utils import mailing
# Импорты необходимых библиотек
import shutil
from aiogram import Bot, F, Router
from aiogram.types import Message, FSInputFile
from datetime import date
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from pathlib import Path
from os import mkdir, path, remove

router = Router()
router.message.filter(ItsAdmin())


def append_zero(a: int):
    return str(a) if a > 9 else f"0{str(a)}"


async def download_zip(admin_id, start_y, start_m, start_d, end_y, end_m, end_d):
    '''
    :admin_id: id админа, который хочет загручить архив ответов.
    :start_y: год начала ответов
    :start_m: месяц начала ответов
    :start_d: день начала ответов
    :end_y: год конца ответов
    :end_m: месяц конца ответов
    :end_d: день конца ответов

    Отправляет админу архив с ответами пользователей в заданном временом промежутке.
    '''
    BASE_DIR = Path(__file__).resolve().parent.parent
    source1 = f"{BASE_DIR}\\tmp"
    distinate = f"{BASE_DIR}\\tmp_archivus"
    mkdir(distinate)
    # print(f'{BASE_DIR}\n{distinate}')
    # Создание архивов по выбранным датам
    while int(start_y) <= int(end_y):
        while int(start_m) <= int(end_m):
            while int(start_d) <= int(end_d):
                need_y = str(start_y)
                need_m = append_zero(start_m)
                need_d = append_zero(start_d)

                # print(f"{source1}\\{need_y}-{need_m}-{need_d}")
                try:
                    need_source = f"{source1}\\{need_y}-{need_m}-{need_d}"
                    need_distinate = f"{distinate}\\{need_y}-{need_m}-{need_d}"
                    shutil.copytree(need_source, need_distinate)
                    # print(f"{need_y}-{need_m}-{need_d}------------ok")
                except Exception as e:
                    print(e)
                start_d += 1
            start_d = 1
            start_m += 1
        start_m = 1
        start_y += 1

    # Создание окончательного архива дл пересылки
    source2 = f'{BASE_DIR}\\tmp_archivus'     # str
    arch = shutil.make_archive(f"archivus\\{date.today()}", "zip", source2)
    await mailing.mail_file(id=admin_id, file_path=arch)
    remove(arch)
    remove(distinate)
    return

# @router.message(AdminDialog.download, F.text)
# async def download_text(message: Message, bot: Bot, user_id: int, state: FSMContext):


async def download_zippp(message: Message):
    '''
    :message: Сообщение от админа в формате yy-mm-dd_yy-mm-dd, где это временой отрезок для ответов пользователей.

    Функция обрабатывает запрос админа для закачки архива с ответами и запускает соответсвующую функцию.
    '''
    chat_id = message.from_user.id
    mess = message.text.split('_')
    start = mess[0]
    end = mess[1]

    start_y, start_m, start_d = start.split('-')
    end_y, end_m, end_d = end.split('-')
    if not (len(start_y) == 4 and len(end_y) == 4
            and 1 <= int(start_m) <= 12 and 1 <= int(end_m) <= 12
            and 1 <= int(start_d) <= 31 and 1 <= int(end_d) <= 31):
        mailing.mail_sertain_text(
            chat_id, text="Неверный формат или значения, перепроверьте. Указывайте числа в формате 09 или 11.")
    else:
        await download_zip(message.from_user.id, int(start_y), int(start_m), int(start_d), int(end_y), int(end_m), int(end_d))
