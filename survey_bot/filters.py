from aiogram.filters import Filter
from aiogram.types import Message
from config import settings

class IsAdmin(Filter):
    """Пропускает только администраторов, указанных в настройках."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in settings.ADMIN_IDS