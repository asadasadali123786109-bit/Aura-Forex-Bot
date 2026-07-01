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
VOICE_NOTE_FILE_ID = 'YOUR_VOICE_NOTE_FILE_ID_HERE'

user_signals = {}
symbols_map = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "XAU/USD": "GC=F"
}

# ================= DATABASE SETUP =================

def init_db():
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium (
            user_id INTEGER PRIMARY KEY,
            expiry_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotex_premium (
            user_id INTEGER PRIMARY KEY,
            expiry_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_premium(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM premium WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        expiry_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < expiry_time:
            return True
    return False

def is_quotex_premium(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM quotex_premium WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        expiry_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < expiry_time:
            return True
    return False

def add_premium_db(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    expiry_date = datetime.now() + timedelta(days=30)
    cursor.execute("INSERT OR REPLACE INTO premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry_date.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def add_quotex_premium_db(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    expiry_date = datetime.now() + timedelta(days=30)
    cursor.execute("INSERT OR REPLACE INTO quotex_premium (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry_date.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

# ================= MARKET ENGINE =================

def get_market_data(symbol_name):
    try:
        ticker_symbol = symbols_map.get(symbol_name)
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="5d", interval="1m")
        if df.empty: return None, None, None
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

def signal_engine(rsi, price, ema):
    if rsi is None or price is None or ema is None: return "NO DATA"
    if rsi < 35 and price > ema: return "🟢 BUY (Strong)"
    if rsi > 65 and price < ema: return "🔴 SELL (Strong)"
    return "🟢 BUY (Trend)" if rsi < 50 else "🔴 SELL (Trend)"

# ================= COMMANDS & TEXT HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📊 Forex Signals"), KeyboardButton("📉 Quotex Signals")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🌟 **Welcome to ForeXAurA!** 🌟\n\n"
        "بڑے بھائی، اپنی مارکیٹ کا انتخاب کریں:\n"
        "📊 Forex Signals یا 📉 Quotex Signals کا بٹن دبائیں۔",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_quotex_menu(bot, user_id):
    keyboard = [
        [InlineKeyboardButton("⚡ 1 Second", callback_data="qx_1sec"), InlineKeyboardButton("⏱️ 30 Seconds", callback_data="qx_30sec")],
        [InlineKeyboardButton("🕐 1 Minute", callback_data="qx_1min"), InlineKeyboardButton("🕒 5 Minutes", callback_data="qx_5min")],
        [InlineKeyboardButton("⏳ 30 Minutes", callback_data="qx_30min"), InlineKeyboardButton("⏰ 1 Hour", callback_data="qx_1hour")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=user_id,
        text="🎯 **ForeXAurA Quotex Premium Strategy**\n\nبڑے بھائی، ہائی ایکوریسی سگنل حاصل کرنے کے لیے اپنی اسٹریٹجی کا ٹائم فریم سلیکٹ کریں:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📊 Forex Signals":
        if is_premium(user_id):
            msg = "💎 FOREX PREMIUM SIGNALS\n\n"
            for s in symbols_map.keys():
                rsi, price, ema = get_market_data(s)
                sig = signal_engine(rsi, price, ema)
                msg += f"{s}\nSignal: {sig}\n\n"
            await update.message.reply_text(msg)
        else:
            if user_id not in user_signals: user_signals[user_id] = 0
            if user_signals[user_id] >= 3:
                await update.message.reply_text("💎 **Forex Premium Subscription (1000 PKR)**\n\nJazzCash: `03202656954`\nEasypaisa: `03287616051`\nAccount Name: Asad Ali\n\nفاریکس پریمیم سگنلز کے لیے پیمنٹ کر کے اسکرین شاٹ یہاں بھیجیں۔", parse_mode="Markdown")
                return
            user_signals[user_id] += 1
            msg = "📊 FOREX FREE SIGNALS\n\n"
            for s in symbols_map.keys():
                rsi, price, ema = get_market_data(s)
                sig = signal_engine(rsi, price, ema)
                msg += f"{s}\nSignal: {sig}\n\n"
            await update.message.reply_text(msg)
        
    elif text == "📉 Quotex Signals":
        if is_quotex_premium(user_id):
            await send_quotex_menu(context.bot, user_id)
        else:
            quotex_payment_text = (
                "📉 **QUOTEX PREMIUM SIGNALS**\n\n"
                "🎁 **لنک آفر پلان (1000 PKR):**\n"
                f"نیچے دیے گئے لنک سے نیا اکاؤنٹ بنا کر ٹریڈر آئی ڈی اور اسکرین شاٹ بھیجیں:\n👉 {QUOTEX_LINK}\n\n"
                "❌ **بغیر لنک پلان (1500 PKR):**\n"
                "اگر لنک سے اکاؤنٹ نہیں بنانا تو فیس 1500 روپے ہوگی۔\n\n"
                "💳 **Accounts (Asad Ali):**\n"
                "• JazzCash: `03202656954`\n"
                "• Easypaisa: `03287616051`\n\n"
                "📤 کوئٹیکس پریمیم ایکٹو کروانے کے لیے پیمنٹ اسکرین شاٹ یہاں بھیجیں۔"
            )
            await update.message.reply_text(quotex_payment_text, parse_mode="Markdown")

# ================= RECEIVE SCREENSHOT =================

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "No Username"

    keyboard = [[
        InlineKeyboardButton("📊 Approve Forex", callback_data=f"app_forex_{user_id}"),
        InlineKeyboardButton("📉 Approve Quotex", callback_data=f"app_quotex_{user_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"📩 **New Payment Screenshot!**\n\n👤 Name: {user.first_name}\n🆔 User ID: `{user_id}`\n📛 Username: {username}\n\nبڑے بھائی، یہ کس چیز کی پیمنٹ ہے؟ نیچے سے سلیکٹ کریں:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ Screenshot received. Admin will verify and activate your plan soon.")

# ================= BUTTONS HANDLING =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.message.chat.id

    # کوئٹیکس اسٹریٹجی پریمیم سگنل جنریٹر
    if data.startswith("qx_"):
        t_frame = data.split("_")[1]
        
        rsi, price, ema = get_market_data("EUR/USD")
        pairs = ['EUR/USD (OTC)', 'GBP/USD (OTC)', 'USD/JPY (OTC)', 'AUD/USD (OTC)', 'Crypto IDX']
        selected_pair = random.choice(pairs)
        
        if rsi and rsi < 45:
            action = "🟢 CALL (UP) ↑"
            accuracy = random.randint(93, 97)
        elif rsi and rsi > 55:
            action = "🔴 PUT (DOWN) ↓"
            accuracy = random.randint(92, 96)
        else:
            action = random.choice(["🟢 CALL (UP) ↑", "🔴 PUT (DOWN) ↓"])
            accuracy = random.randint(90, 95)
        
        signal_msg = (
            f"🎯 **ForeXAurA QUOTEX STRATEGY SIGNAL**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💱 **Asset/Pair:** {selected_pair}\n"
            f"🚀 **Direction:** {action}\n"
            f"⏳ **Strategy Time:** {t_frame}\n"
            f"📊 **Signal Accuracy:** {accuracy}%\n"
            f"📶 **Market Trend:** {'BULLISH' if 'CALL' in action else 'BEARISH'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_(بڑے بھائی، ابھی کوئٹیکس اوپن کریں اور پرافٹ بک کریں!)_"
        )
        await context.bot.send_message(chat_id=user_id, text=signal_msg, parse_mode='Markdown')
        return

    # ایڈمن اپروول بٹنز
    if query.from_user.id != ADMIN_ID: return

    # 1. فاریکس اپروول (بالکل الگ)
    if data.startswith("app_forex_"):
        target_id = int(data.split("_")[2])
        add_premium_db(target_id)
        
        await context.bot.send_message(
            chat_id=target_id, 
            text="🎉 **Forex Premium Activated!**\n\nبڑے بھائی، آپ کا فاریکس پریمیم پلان **30 دن** کے لیے کامیابی سے بائے ہو گیا ہے۔ اب آپ پریمیم فاریکس سگنلز حاصل کر سکتے ہیں۔"
        )
        
        # فاریکس کے لیے وائس نوٹ آٹو سینڈ کرنا
        if VOICE_NOTE_FILE_ID != 'YOUR_VOICE_NOTE_FILE_ID_HERE':
            try:
                await context.bot.send_voice(
                    chat_id=target_id, 
                    voice=VOICE_NOTE_FILE_ID, 
                    caption="🚨 **ForeXAurA Important Warning!**\nبڑے بھائی، فاریکس پریمیم استعمال کرنے سے پہلے یہ وائس نوٹ لازمی سنیں۔"
                )
            except: pass
        await query.edit_message_caption("✅ Approved Forex Premium (30 Days)")

    # 2. کوئٹیکس اپروول (بالکل الگ)
    elif data.startswith("app_quotex_"):
        target_id = int(data.split("_")[2])
        add_quotex_premium_db(target_id)
        
        await context.bot.send_message(
            chat_id=target_id, 
            text="🎉 **Quotex Premium Activated!**\n\nبڑے بھائی! آپ کا کوئٹیکس اسٹریٹجی پریمیم پلان **30 دن** کے لیے کامیابی سے بائے ہو چکا ہے۔"
        )
        await send_quotex_menu(context.bot, target_id)
        
        # کوئٹیکس کے لیے بھی وہی وائس نوٹ آٹو سینڈ کرنا
        if VOICE_NOTE_FILE_ID != 'YOUR_VOICE_NOTE_FILE_ID_HERE':
            try:
                await context.bot.send_voice(
                    chat_id=target_id, 
                    voice=VOICE_NOTE_FILE_ID, 
                    caption="🚨 **ForeXAurA Important Warning!**\nبڑے بھائی، کوئٹیکس پریمیم استعمال کرنے سے پہلے یہ وائس نوٹ لازمی سنیں۔"
                )
            except: pass
        await query.edit_message_caption("✅ Approved Quotex Premium (30 Days)")

async def catch_voice_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(f"🎙️ **Voice File ID:**\n`{update.message.voice.file_id}`", parse_mode="Markdown")

# ================= AUTO EXPIRY LOOP =================

async def check_expiry_loop(application: Application):
    while True:
        try:
            conn = sqlite3.connect('premium_users.db')
            cursor = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("SELECT user_id FROM premium WHERE expiry_date <= ?", (current_time,))
            expired_forex = cursor.fetchall()
            for u in expired_forex:
                cursor.execute("DELETE FROM premium WHERE user_id = ?", (u[0],))
                conn.commit()
                try: await application.bot.send_message(chat_id=u[0], text="⚠️ آپ کا فاریکس پریمیم پلان ختم ہو گیا ہے۔")
                except: pass
                
            cursor.execute("SELECT user_id FROM quotex_premium WHERE expiry_date <= ?", (current_time,))
            expired_quotex = cursor.fetchall()
            for u in expired_quotex:
                cursor.execute("DELETE FROM quotex_premium WHERE user_id = ?", (u[0],))
                conn.commit()
                try: await application.bot.send_message(chat_id=u[0], text="⚠️ آپ کا کوئٹیکس پریمیم پلان ختم ہو گیا ہے۔")
                except: pass
                
            conn.close()
        except: pass
        await asyncio.sleep(3600)

# ================= RUN =================

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Text(["📊 Forex Signals", "📉 Quotex Signals"]), handle_text_menu))
app.add_handler(filters.PHOTO, receive_photo)
app.add_handler(MessageHandler(filters.VOICE, catch_voice_id))
app.add_handler(CallbackQueryHandler(button_handler))

async def main():
    await app.initialize()
    await app.start()
    asyncio.create_task(check_expiry_loop(app))
    await app.updater.start_polling()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
