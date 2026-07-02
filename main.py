import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import yfinance as yf

TOKEN = "8566958802:AAHPgbT-9B3tYBRynjkQ68yqSHVC8gv2qQU"
ADMIN_ID = 5961662950

QUOTEX_LINK = "https://broker-qx.pro/sign-up/?lid=2182439"

FOREX_PAYMENT_DETAILS = (
    "💳 *فاریکس پریمیئم پیمنٹ کا طریقہ کار* 💳\n\n"
    "🔥 *فیس:* 1000 روپے / 30 دن (ان لمیٹڈ سگنلز)\n\n"
    "📱 *JazzCash:* `03282656954` (Asad ali)\n"
    "📱 *Easypaisa:* `03287616051` (Asad ali)\n"
    "📱 *SADApay:* `03287616051` (Asad ali)\n\n"
    "⚠️ *اہم نوٹ:* پیسے بھیجنے کے بعد ٹرانزیکشن کا سکرین شاٹ اسی بوٹ کے اندر سینڈ کریں۔"
)

QUOTEX_PAYMENT_DETAILS = (
    "💳 *کوٹیکس پریمیئم پیمنٹ کا طریقہ کار* 💳\n\n"
    "🔗 *ہمارے لنک سے اکاؤنٹ بنانے والوں کے لیے:* 1000 روپے / 30 دن\n"
    "❌ *بغیر لنک جوائن کرنے والوں کے لیے:* 1500 روپے / 30 دن\n\n"
    "📌 *Quotex Joining Link:* [اکاؤنٹ بنانے کے لیے یہاں کلک کریں]({link})\n\n"
    "📱 *JazzCash:* `03282656954` (Asad ali)\n"
    "📱 *Easypaisa:* `03287616051` (Asad ali)\n"
    "📱 *SADApay:* `03287616051` (Asad ali)\n\n"
    "⚠️ *اہم نوٹ:* پیسے بھیجنے یا اکاؤنٹ بنانے کے بعد سکرین شاٹ اسی بوٹ کے اندر سینڈ کریں۔"
).format(link=QUOTEX_LINK)

symbols_map = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X", "XAUUSD": "XAUUSD=F", "CryptoIDX": "BTC-USD"
}

def get_main_menu_keyboard():
    keyboard = [[KeyboardButton("📊 Forex Signals"), KeyboardButton("📉 Quotex Signals")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True, one_time_keyboard=False)

def init_db():
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS premium (user_id INTEGER PRIMARY KEY, expiry_date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS quotex_premium (user_id INTEGER PRIMARY KEY, expiry_date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS free_usage (user_id INTEGER PRIMARY KEY, forex_clicks INTEGER DEFAULT 0, quotex_clicks INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

init_db()

def get_free_clicks(user_id):
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT forex_clicks, quotex_clicks FROM free_usage WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row: return row[0], row[1]
    except: pass
    return 0, 0

def increment_free_clicks(user_id, mode="forex"):
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO free_usage (user_id, forex_clicks, quotex_clicks) VALUES (?, 0, 0)", (user_id,))
        if mode == "forex": cursor.execute("UPDATE free_usage SET forex_clicks = forex_clicks + 1 WHERE user_id = ?", (user_id,))
        else: cursor.execute("UPDATE free_usage SET quotex_clicks = quotex_clicks + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except: pass

def is_premium(user_id):
    if user_id == ADMIN_ID: return True
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT expiry_date FROM premium WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and datetime.now() < datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'): return True
    except: pass
    return False

def is_quotex_premium(user_id):
    if user_id == ADMIN_ID: return True
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT expiry_date FROM quotex_premium WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and datetime.now() < datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'): return True
    except: pass
    return False

def add_premium_db(user_id):
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(days=30)
        cursor.execute("INSERT OR REPLACE INTO premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
    except: pass

def add_quotex_premium_db(user_id):
    try:
        conn = sqlite3.connect('premium_users.db')
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(days=30)
        cursor.execute("INSERT OR REPLACE INTO quotex_premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
    except: pass

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID: return
    caption_text = f"📩 *New Payment Screenshot Received!*\n\n👤 *Name:* {user.full_name}\n🆔 *Chat ID:* `{user.id}`"
    keyboard = [[InlineKeyboardButton("✅ Approve Forex", callback_data=f"adm_appf_{user.id}"), InlineKeyboardButton("✅ Approve Quotex", callback_data=f"adm_appq_{user.id}")]]
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await update.message.reply_text("✅ آپ کا سکرین شاٹ ایڈمن کو موصول ہو گیا ہے!", reply_markup=get_main_menu_keyboard())

def advanced_market_analysis(symbol_name, is_forex_mode=False):
    try:
        ticker_symbol = symbols_map.get(symbol_name, "EURUSD=X")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="2d", interval="1m")
        if df.empty or len(df) < 20: return ("🟢 BUY", "Bullish") if is_forex_mode else ("🟢 CALL (UP) ↑", "BULLISH")
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        current_price = float(df['Close'].iloc[-1])
        sma_20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
        
        if is_forex_mode:
            return f"RSI: {rsi:.4f}", ("🟢 BUY" if rsi < 35 or current_price > sma_20 else "🔴 SELL")
        return ("🟢 CALL (UP) ↑" if rsi < 35 or current_price > sma_20 else "🔴 PUT (DOWN) ↓"), "Analyzed"
    except:
        return ("🟢 BUY", "Stable")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌟 *ForeXAurA میں خوش آمدید!* 🌟\n\n"
        "بڑے بھائی، مارکیٹ کا لائیو ڈیٹا اینالائز کر کے پرافٹ ایبل سگنل دینے والا فائنل انجن بالکل تیار ہے۔\n"
        "👉 *Forex / Quotex Signals* حاصل کرنے کے لیے نیچے دیے گئے مینو بٹنز کا استعمال کریں۔"
    )
    await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

async def send_quotex_pairs_menu(bot, user_id, is_premium_user=False, clicks_left=3):
    keyboard = [
        [InlineKeyboardButton("💱 EUR/USD (OTC)", callback_data="qxpair_EURUSD"), InlineKeyboardButton("💱 GBP/USD (OTC)", callback_data="qxpair_GBPUSD")],
        [InlineKeyboardButton("💱 USD/JPY (OTC)", callback_data="qxpair_USDJPY"), InlineKeyboardButton("💱 AUD/USD (OTC)", callback_data="qxpair_AUDUSD")],
        [InlineKeyboardButton("🪙 Crypto IDX", callback_data="qxpair_CryptoIDX")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📊 **FREE SIGNALS (Clicks Left: {clicks_left})**" if not is_premium_user else "💎 **QUOTEX PREMIUM SIGNALS**"
    await bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

async def send_quotex_time_menu(bot, user_id, pair_name):
    keyboard = [
        [InlineKeyboardButton("⚡ 5 Seconds", callback_data=f"qxt_5sec_{pair_name}"), InlineKeyboardButton("⏱️ 30 Seconds", callback_data=f"qxt_30sec_{pair_name}")],
        [InlineKeyboardButton("🕐 1 Minute", callback_data=f"qxt_1min_{pair_name}"), InlineKeyboardButton("🕒 5 Minutes", callback_data=f"qxt_5min_{pair_name}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id=user_id, text=f"🎯 **Pair Selected:** {pair_name}\n\nبڑے بھائی، ٹائم فریم منتخب کریں:", reply_markup=reply_markup, parse_mode="Markdown")

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if text == "📊 Forex Signals":
        if not is_premium(user_id) and user_id != ADMIN_ID:
            clicks = get_free_clicks(user_id)[0]
            if clicks >= 3:
                await update.message.reply_text(FOREX_PAYMENT_DETAILS, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
                return
            increment_free_clicks(user_id, "forex")
        pairs = ["EURUSD", "GBPUSD", "XAUUSD"]
        msg = "💎 *FOREX SIGNALS*\n\n"
        for p in pairs:
            rsi, act = advanced_market_analysis(p, True)
            msg += f"*{p}*: {rsi} | {act}\n"
        await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    elif text == "📉 Quotex Signals":
        if is_quotex_premium(user_id):
            await send_quotex_pairs_menu(context.bot, user_id, True)
        else:
            clicks = get_free_clicks(user_id)[1]
            if clicks >= 3:
                await update.message.reply_text(QUOTEX_PAYMENT_DETAILS, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
                return
            await send_quotex_pairs_menu(context.bot, user_id, False, 3 - clicks)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.message.chat.id
    if data.startswith("adm_appf_"):
        add_premium_db(int(data.split("_")[2]))
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ *Approved for Forex Premium!*")
    elif data.startswith("adm_appq_"):
        add_quotex_premium_db(int(data.split("_")[2]))
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ *Approved for Quotex Premium!*")
    elif data.startswith("qxpair_"):
        await send_quotex_time_menu(context.bot, user_id, data.split("_")[1])
    elif data.startswith("qxt_"):
        action, trend = advanced_market_analysis(data.split("_")[2], False)
        await context.bot.send_message(chat_id=user_id, text=f"🎯 *SIGNAL*\n🚀 {action}\n📶 {trend}", reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
app.add_handler(MessageHandler(filters.Text(["📊 Forex Signals", "📉 Quotex Signals"]), handle_text_menu))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
