from tortoise import Tortoise

from .settings import get_orm_configuration


async def init() -> None:
    await Tortoise.init(get_orm_configuration())
