from aiogram import Bot, Dispatcher
from aiogram import Dispatcher
import asyncio
from settings.config import BOT_TOKEN
from handlers.commands import start, setup, upload, information, mailing
from handlers.commands.start import set_bot_commands


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.start_router)
    dp.include_router(setup.setup_router)
    dp.include_router(upload.upload_router)
    dp.include_router(information.information_router)
    dp.include_router(mailing.mailing_router)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
