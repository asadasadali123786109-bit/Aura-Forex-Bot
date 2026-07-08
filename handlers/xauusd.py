from telegram import Update
from telegram.ext import ContextTypes

async def xauusd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🥇 XAU/USD (GOLD)\n\n"

        "🟢 Signal : BUY\n\n"

        "📍 Entry : 3348.20\n"
        "🎯 Take Profit : 3353.50\n"
        "🛑 Stop Loss : 3345.80\n\n"

        "⏰ Time Frame : 5 Minutes\n\n"

        "📊 Confidence : 87%\n\n"

        "Indicators\n"
        "✅ RSI Bullish\n"
        "✅ EMA Trend Up\n"
        "✅ MACD Buy\n"
        "✅ Strong Trend\n\n"

        "⚠️ Risk : Low"
    )
