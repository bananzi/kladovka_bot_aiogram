from typing import Union, Dict, Any
from aiogram.filters import BaseFilter
from aiogram.types import Message

from database import requests as rq

class UserInCourse(BaseFilter):
    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        user_id = message.from_user.id
        # if user_id == 605954613:
        #     return False
        return {"user_id": user_id}