from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from config import BOT_TOKEN
from database import create_tables
from logger import logger


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "السلام علیکم!\n\nAura Forex Bot میں خوش آمدید۔"
    )


def main():
    create_tables()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    logger.info("Bot Started")

    app.run_polling()


if __name__ == "__main__":
    main()
