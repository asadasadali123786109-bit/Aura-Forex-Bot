import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import yfinance as yf
import pandas as pd

TOKEN = "8566958802:AAHPgbT-9B3tYBRynjkQ68yqSHVC8gv2qQU"
ADMIN_ID = 5961662950

user_signals = {}
premium_users = set()

symbols_map = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "XAU/USD": "GC=F"
}


# ================= MARKET DATA ENGINE (NO API KEY NEEDED) =================

def get_market_data(symbol_name):
    try:
        ticker_symbol = symbols_map.get(symbol_name)
        ticker = yf.Ticker(ticker_symbol)
        
        df = ticker.history(period="5d", interval="1m")
        
        if df.empty:
            return None, None, None
            
        price = float(df['Close'].iloc[-1])
        
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        ema = float(df['EMA_20'].iloc[-1])
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        rsi = float(df['RSI'].iloc[-1])
        
        return round(rsi, 2), round(price, 4), round(ema, 4)
    except:
        return None, None, None


# ================= SIGNAL ENGINE =================

def signal_engine(rsi, price, ema):
    if rsi is None or price is None or ema is None:
        return "NO DATA"

    if rsi < 35 and price > ema:
        return "🟢 BUY (Strong)"

    if rsi > 65 and price < ema:
        return "🔴 SELL (Strong)"

    if rsi < 50:
        return "🟢 BUY (Trend)"
    else:
        return "🔴 SELL (Trend)"


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 WELCOME\n\n"
        "Use /signal for trading signals\n"
        "Free users: 3 signals only"
    )


# ================= PAYMENT TEXT =================

payment_text = (
    "💎 PREMIUM UPGRADE (1000 PKR)\n\n"
    "💳 JazzCash:\n"
    "03282656954\n\n"
    "💳 Easypaisa:\n"
    "03287616051\n\n"
    "💳 SadaPay:\n"
    "03287616051\n\n"
    "👤 Account Name:\n"
    "Asad Ali\n\n"
    "📤 Payment ke baad screenshot isi bot ko send karein\n"
    "Admin verify kar ke Premium activate karega"
)


# ================= SIGNAL COMMAND =================

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # PREMIUM USER
    if user_id in premium_users:
        msg = "💎 PREMIUM SIGNALS\n\n"
        for s in symbols_map.keys():
            rsi, price, ema = get_market_data(s)
            sig = signal_engine(rsi, price, ema)
            msg += f"{s}\nRSI: {rsi if rsi else 'None'}\nSignal: {sig}\n\n"
        await update.message.reply_text(msg)
        return

    # FREE USER
    if user_id not in user_signals:
        user_signals[user_id] = 0

    if user_signals[user_id] >= 3:
        await update.message.reply_text(payment_text)
        return

    user_signals[user_id] += 1

    msg = "📊 FREE SIGNALS\n\n"
    for s in symbols_map.keys():
        rsi, price, ema = get_market_data(s)
        sig = signal_engine(rsi, price, ema)
        msg += f"{s}\nRSI: {rsi if rsi else 'None'}\nSignal: {sig}\n\n"

    await update.message.reply_text(msg)


# ================= SCREENSHOT HANDLER =================

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "No Username"

    keyboard = [[
        InlineKeyboardButton("✅ Approve Premium", callback_data=f"approve_{user.id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=(
            f"💰 Payment Screenshot\n\n"
            f"👤 {user.first_name}\n"
            f"🆔 {user.id}\n"
            f"📛 @{username}"
        ),
        reply_markup=reply_markup
    )

    await update.message.reply_text(
        "✅ Screenshot received. Admin will verify soon."
    )


# ================= APPROVE BUTTON =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    if query.data.startswith("approve_"):
        user_id = int(query.data.split("_")[1])
        premium_users.add(user_id)

        await context.bot.send_message(
            chat_id=user_id,
            text="🎉 PREMIUM ACTIVATED!\nNow you have unlimited signals."
        )
        await query.edit_message_caption("✅ Approved")


# ================= MANUAL APPROVE =================

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) == 0:
        await update.message.reply_text("/approve USER_ID")
        return

    user_id = int(context.args[0])
    premium_users.add(user_id)

    await context.bot.send_message(
        chat_id=user_id,
        text="🎉 Premium Activated!"
    )
    await update.message.reply_text("✅ Approved")


# ================= BOT SETUP =================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("approve", approve))

app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
app.add_handler(CallbackQueryHandler(button_handler))

print("BOT RUNNING...")
app.run_polling()
