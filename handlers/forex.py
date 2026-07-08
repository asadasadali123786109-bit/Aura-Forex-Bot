from telegram import Update
from telegram.ext import ContextTypes

async def forex_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Forex Signals\n\n"
        "Pair: EUR/USD\n"
        "Direction: BUY 🟢\n"
        "Time: 5 Minutes\n"
        "Accuracy: 92%"
    )
