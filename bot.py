import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import BOT_TOKEN
from src.handlers import setup_handlers
from src.middlewares import setup_middleware

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

setup_middleware(dp)
setup_handlers(dp)


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
