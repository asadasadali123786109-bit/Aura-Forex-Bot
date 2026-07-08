from telegram.ext import Application, CommandHandler

from config import BOT_TOKEN
from database import create_tables
from handlers.start import start
from logger import logger


def main():
    create_tables()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    logger.info("Aura Forex Bot Started")

    app.run_polling()


if __name__ == "__main__":
    main()
