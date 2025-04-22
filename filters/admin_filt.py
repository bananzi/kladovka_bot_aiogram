from typing import Union, Dict, Any

from aiogram.filters import BaseFilter
from aiogram.types import Message
admin_ids = {605954613: "Александр", 581700023: "Софья"}
skip = False
class ItsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        id_user = message.from_user.id
        if not skip:
            if id_user in admin_ids:
                return {"name_admin": admin_ids[id_user], "id_admin": id_user}
        return False
