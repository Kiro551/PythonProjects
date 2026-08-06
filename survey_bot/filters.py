from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from config import settings

class IsAdmin(Filter):
    """Пропускает только администраторов, указанных в настройках."""
    async def __call__(self, event) -> bool:
        return event.from_user.id in settings.ADMIN_IDS