import asyncio
import logging

from aiocron import crontab
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src import schedules
from src.handlers import bot, router
from src.webserver import start_server


async def start_bot():
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)

    crontab("* * * * *", func=schedules.update_spins_left)
    crontab("1 0 * * *", func=schedules.update_spins_limit)
    crontab("* * * * *", func=schedules.update_fake_autospins)
    crontab("* * * * *", func=schedules.send_spin_warnings)
    crontab("1 0 * * 1", func=schedules.start_tournament)
    crontab("1 19 * * 0", func=schedules.end_tournament)
    crontab("*/10 * * * *", func=schedules.unload_to_google_sheets)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


async def main():
    bot_task = asyncio.create_task(start_bot())
    web_server_task = asyncio.create_task(start_server())

    await asyncio.gather(bot_task, web_server_task)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
