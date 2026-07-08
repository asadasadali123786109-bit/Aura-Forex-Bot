from telegram import Update
from telegram.ext import ContextTypes

async def forex_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Today's Forex Signals\n\n"

        "🥇 XAU/USD (Gold)\n"
        "➡️ BUY 🟢\n"
        "⏰ Time: 5M\n\n"

        "💶 EUR/USD\n"
        "➡️ BUY 🟢\n"
        "⏰ Time: 5M\n\n"

        "💷 GBP/USD\n"
        "➡️ SELL 🔴\n"
        "⏰ Time: 5M\n\n"

        "🇺🇸 USD/JPY\n"
        "➡️ BUY 🟢\n"
        "⏰ Time: 5M\n\n"

        "🇦🇺 AUD/USD\n"
        "➡️ SELL 🔴\n"
        "⏰ Time: 5M\n\n"

        "🇺🇸 USD/CAD\n"
        "➡️ BUY 🟢\n"
        "⏰ Time: 5M\n\n"

        "🇳🇿 NZD/USD\n"
        "➡️ SELL 🔴\n"
        "⏰ Time: 5M"
    )
