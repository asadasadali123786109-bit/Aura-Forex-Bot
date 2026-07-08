from telegram import Update
from telegram.ext import ContextTypes

from utils.keyboard import forex_menu


async def forex_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📊 اپنا Forex Pair منتخب کریں۔",
        reply_markup=forex_menu()
    )
