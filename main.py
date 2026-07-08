from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from database import create_tables
from handlers.start import start
from handlers.forex import forex_signals
from logger import logger


def main():
    create_tables()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(filters.Regex("^📊 Forex Signals$"), forex_signals)
    )

    logger.info("Aura Forex Bot Started")

    app.run_polling()


if __name__ == "__main__":
    main()
