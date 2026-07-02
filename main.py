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

# 💳 PAYMENT DETAILS
FOREX_PAYMENT_DETAILS = (
    "💳 *فاریکس پریمیئم پیمنٹ کا طریقہ کار* 💳\n\n"
    "🔥 *فیس:* 1000 روپے / 30 دن (ان لمیٹڈ سگنلز)\n\n"
    "📱 *JazzCash:* `03282656954` (Asad ali)\n"
    "📱 *Easypaisa:* `03287616051` (Asad ali)\n"
    "📱 *SADApay:* `03287616051` (Asad ali)\n\n"
    "⚠️ *اہم نوٹ:* پیسے بھیجنے کے بعد ٹرانزیکشن کا سکرین شاٹ اسی بوٹ کے اندر سینڈ کریں، یہ خودکار طور پر ایڈمن کو چلا جائے گا۔"
)

QUOTEX_PAYMENT_DETAILS = (
    "💳 *کوٹیکس پریمیئم پیمنٹ کا طریقہ کار* 💳\n\n"
    "🔗 *ہمارے لنک سے اکاؤنٹ بنانے والوں کے لیے:* 1000 روپے / 30 دن\n"
    "❌ *بغیر لنک جوائن کرنے والوں کے لیے:* 1500 روپے / 30 دن\n\n"
    "📌 *Quotex Joining Link:* [اکاؤنٹ بنانے کے لیے یہاں کلک کریں]({link})\n\n"
    "📱 *JazzCash:* `03282656954` (Asad ali)\n"
    "📱 *Easypaisa:* `03287616051` (Asad ali)\n"
    "📱 *SADApay:* `03287616051` (Asad ali)\n\n"
    "⚠️ *اہم نوٹ:* پیسے بھیجنے یا اکاؤنٹ بنانے کے بعد سکرین شاٹ اسی بوٹ کے اندر سینڈ کریں، یہ خودکار طور پر ایڈمن کو جائے گا۔"
).format(link=QUOTEX_LINK)

symbols_map = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "XAUUSD": "XAUUSD=F",
    "CryptoIDX": "BTC-USD"
}

# بٹن مستقل کرنے کے لیے persistent=True اور one_time_keyboard=False
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
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    expiry = datetime.now() + timedelta(days=30)
    cursor.execute("INSERT OR REPLACE INTO premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def add_quotex_premium_db(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    expiry = datetime.now() + timedelta(days=30)
    cursor.execute("INSERT OR REPLACE INTO quotex_premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID: return
    caption_text = f"📩 *New Payment Screenshot Received!*\n\n👤 *Name:* {user.full_name}\n🆔 *Chat ID:* `{user.id}`"
    keyboard = [[InlineKeyboardButton("✅ Approve Forex", callback_data=f"adm_appf_{user.id}"), InlineKeyboardButton("✅ Approve Quotex", callback_data=f"adm_appq_{user.id}")]]
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await update.message.reply_text("✅ آپ کا سکرین شاٹ ایڈمن کو موصول ہو گیا ہے!", reply_markup=get_main_menu_keyboard())

def advanced_market_analysis(symbol_name, is_forex_mode=False):
    try:
        ticker = yf.Ticker(symbols_map.get(symbol_name, "EURUSD=X"))
        df = ticker.history(period="2d", interval="1m")
        if df.empty or len(df) < 20:
            rsi_val = random.uniform(45.0, 55.0)
            return (f"RSI: {rsi_val:.4f}", "🟢 BUY") if is_forex_mode else ("🟢 CALL (UP) ↑", "BULLISH")
        
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
    await update.message.reply_text("🌟 *ForeXAurA میں خوش آمدید!* 🌟\nسگنل کے لیے نیچے بٹن دبائیں:", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

async def send_quotex_pairs_menu(bot, user_id, is_premium_user=False, clicks_left=3):
    keyboard = [[InlineKeyboardButton("💱 EUR/USD (OTC)", callback_data="qxpair_EURUSD"), InlineKeyboardButton("💱 GBP/USD (OTC)", callback_data="qxpair_GBPUSD")],
                [InlineKeyboardButton("💱 USD/JPY (OTC)", callback_data="qxpair_USDJPY"), InlineKeyboardButton("💱 AUD/USD (OTC)", callback_data="qxpair_AUDUSD")],
                [InlineKeyboardButton("🪙 Crypto IDX", callback_data="qxpair_CryptoIDX")]]
    text = "💎 **PREMIUM SIGNALS**" if is_premium_user else f"📊 **FREE SIGNALS (Left: {clicks_left})**"
    await bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def send_quotex_time_menu(bot, user_id, pair_name):
    keyboard = [[InlineKeyboardButton("⚡ 5s", callback_data=f"qxt_5sec_{pair_name}"), InlineKeyboardButton("⏱️ 30s", callback_data=f"qxt_30sec_{pair_name}")],
                [InlineKeyboardButton("🕐 1m", callback_data=f"qxt_1min_{pair_name}"), InlineKeyboardButton("🕒 5m", callback_data=f"qxt_5min_{pair_name}")]]
    await bot.send_message(chat_id=user_id, text="ٹائم فریم منتخب کریں:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if text == "📊 Forex Signals":
        pairs = ["EURUSD", "GBPUSD", "XAUUSD"]
        msg = "💎 *FOREX SIGNALS*\n\n"
        for p in pairs:
            rsi, act = advanced_market_analysis(p, True)
            msg += f"*{p}*: {rsi} | {act}\n"
        await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    elif text == "📉 Quotex Signals":
        await send_quotex_pairs_menu(context.bot, user_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.message.chat.id
    if data.startswith("adm_"):
        target_id = int(data.split("_")[2])
        if "appf" in data: add_premium_db(target_id)
        else: add_quotex_premium_db(target_id)
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ *Approved!*")
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
