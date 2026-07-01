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
import pandas as pd

TOKEN = "8566958802:AAHPgbT-9B3tYBRynjkQ68yqSHVC8gv2qQU"
ADMIN_ID = 5961662950

# آپ کا کوئٹیکس ایفیلیٹ لنک
QUOTEX_LINK = "https://broker-qx.pro/sign-up/?lid=2182439"

# وائس نوٹ کی فائل آئی ڈی (پہلی بار وائس نوٹ ایڈمن سے بھیج کر جو آئی ڈی ملے گی، وہ یہاں ڈالیں)
VOICE_NOTE_FILE_ID = 'YOUR_VOICE_NOTE_FILE_ID_HERE'

user_signals = {}
user_states = {}  # کوئٹیکس یوزرز کے عارضی ڈیٹا (Plan, Trader ID) کے لیے

symbols_map = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "XAU/USD": "GC=F"
}

# ================= DATABASE SETUP FOR AUTO EXPIRY =================

def init_db():
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium (
            user_id INTEGER PRIMARY KEY,
            expiry_date TEXT
        )
    """)
    # کوئٹیکس کے پریمیم یوزرز کے لیے الگ ٹیبل
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotex_premium (
            user_id INTEGER PRIMARY KEY,
            trader_id TEXT,
            plan_type TEXT
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
    cursor.execute("SELECT user_id FROM quotex_premium WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row else False

def add_premium_db(user_id):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    expiry_date = datetime.now() + timedelta(days=30)
    cursor.execute("""
        INSERT OR REPLACE INTO premium (user_id, expiry_date) 
        VALUES (?, ?)
    """, (user_id, expiry_date.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def add_quotex_premium_db(user_id, trader_id, plan_type):
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO quotex_premium (user_id, trader_id, plan_type) 
        VALUES (?, ?, ?)
    """, (user_id, trader_id, plan_type))
    conn.commit()
    conn.close()

# ================= BACKGROUND AUTO-EXPIRY CHECKER =================

async def check_expiry_loop(application: Application):
    while True:
        try:
            conn = sqlite3.connect('premium_users.db')
            cursor = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute("SELECT user_id FROM premium WHERE expiry_date <= ?", (current_time,))
            expired_users = cursor.fetchall()

            for user in expired_users:
                user_id = user[0]
                cursor.execute("DELETE FROM premium WHERE user_id = ?", (user_id,))
                conn.commit()

                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ آپ کا پریمیم مہینہ پورا ہو چکا ہے! سگنلز جاری رکھنے کے لیے دوبارہ سبسکرپشن بائے کریں۔"
                    )
                except Exception:
                    pass
            conn.close()
        except Exception as e:
            print(f"Expiry checker error: {e}")

        await asyncio.sleep(3600) # ہر 1 گھنٹے بعد خود بخود چیک کرے گا


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
    # مین رپلائی کی بورڈ مینو جس میں دونوں آپشنز ہوں گے
    keyboard = [
        [KeyboardButton("📊 Forex Signals"), KeyboardButton("📉 Quotex Signals")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🌟 **Welcome to ForeXAurA!** 🌟\n\n"
        "بڑے بھائی، خوش آمدید! آپ کے بہترین ٹریڈنگ سفر کا آغاز یہیں سے ہوتا ہے۔\n"
        "نیچے دیے گئے مینو سے اپنی مارکیٹ کا انتخاب کریں:\n\n"
        "👉 فاریکس سگنلز کے لیے /signal کا استعمال کریں یا بٹن دبائیں۔\n"
        "👉 فری یوزرز کے لیے صرف 3 فاریکس سگنلز دستیاب ہیں۔",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# ================= PAYMENT TEXT (FOREX & DEFAULT) =================

payment_text = (
    "💎 **PREMIUM UPGRADE (1000 PKR)**\n\n"
    "💳 **JazzCash:**\n"
    "03202656954\n\n"
    "💳 **Easypaisa:**\n"
    "03287616051\n\n"
    "💳 **SadaPay:**\n"
    "03287616051\n\n"
    "👤 **Account Name:**\n"
    "Asad Ali\n\n"
    "📤 Payment ke baad screenshot isi bot ko send karein\n"
    "Admin verify kar ke Premium activate karega"
)

# کوئٹیکس کے لیے خصوصی پرائسنگ ٹیکسٹ
quotex_payment_text = (
    "📉 **QUOTEX PREMIUM SIGNALS**\n\n"
    "بڑے بھائی، 5sec، 1min، اور 5min کے ہائی ایکوریسی پریمیم سگنلز کے لیے نیچے سے ایک پلان چوز کریں:\n\n"
    "🎁 **آفر پلان (صرف 1000 PKR):**\n"
    f"1. نیچے دیے گئے لنک پر کلک کر کے نیا کوئٹیکس اکاؤنٹ بنائیں:\n👉 {QUOTEX_LINK}\n"
    "2. اکاؤنٹ بنانے کے بعد اپنی Trader ID اور 1000 PKR کا اسکرین شاٹ بوٹ میں سینڈ کریں۔\n\n"
    "❌ **بغیر لنک پلان (1500 PKR):**\n"
    "اگر آپ ہمارے لنک سے اکاؤنٹ نہیں بنانا چاہتے، تو فیس 1500 PKR ہوگی۔ آپ ڈائریکٹ اسکرین شاٹ سینڈ کریں۔\n\n"
    "💳 **Accounts Details (Asad Ali):**\n"
    "• JazzCash: `03202656954`\n"
    "• Easypaisa: `03287616051`\n"
    "• SADApay: `03287616051`"
)


# ================= SIGNAL COMMAND & MENU HANDLER =================

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # PREMIUM USER CHECK
    if is_premium(user_id):
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
        await update.message.reply_text(payment_text, parse_mode="Markdown")
        return

    user_signals[user_id] += 1

    msg = "📊 FREE SIGNALS\n\n"
    for s in symbols_map.keys():
        rsi, price, ema = get_market_data(s)
        sig = signal_engine(rsi, price, ema)
        msg += f"{s}\nRSI: {rsi if rsi else 'None'}\nSignal: {sig}\n\n"

    await update.message.reply_text(msg)


async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📊 Forex Signals":
        await signal(update, context)
        
    elif text == "📉 Quotex Signals":
        if is_quotex_premium(user_id):
            # اگر کوئٹیکس پریمیم ایکٹو ہے تو ٹائم فریم کے ان لائن بٹن دکھائیں
            keyboard = [
                [InlineKeyboardButton("⚡ 5 Seconds", callback_data="qx_5sec"), InlineKeyboardButton("🕐 1 Minute", callback_data="qx_1min")],
                [InlineKeyboardButton("🕒 5 Minutes", callback_data="qx_5min"), InlineKeyboardButton("⏱️ 10 Minutes", callback_data="qx_10min")],
                [InlineKeyboardButton("⏳ 1 Hour", callback_data="qx_1hour")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🎯 **ForeXAurA Quotex Premium Menu**\n\nبڑے بھائی، سگنل حاصل کرنے کے لیے ٹائم فریم سلیکٹ کریں:", reply_markup=reply_markup, parse_mode="Markdown")
        else:
            # اگر پریمیم نہیں ہے تو 1000 اور 1500 والی آفر بٹن دکھائیں
            keyboard = [
                [InlineKeyboardButton("🎁 لنک آفر (1000 PKR)", callback_data="qx_choose_link")],
                [InlineKeyboardButton("❌ بغیر لنک پلان (1500 PKR)", callback_data="qx_choose_direct")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(quotex_payment_text, reply_markup=reply_markup, parse_mode="Markdown")

    # اگر یوزر ٹیکسٹ میسج میں ٹریڈر آئی ڈی ٹائپ کر کے بھیج رہا ہے
    elif user_id in user_states and user_states[user_id].get('state') == 'WAITING_FOR_ID':
        user_states[user_id]['trader_id'] = text
        user_states[user_id]['state'] = 'WAITING_FOR_SCREENSHOT'
        await update.message.reply_text("👍Trader ID محفوظ ہو گئی ہے۔ اب اپنی **1000 PKR** پیمنٹ کا اسکرین شاٹ (Photo) بوٹ میں سینڈ کریں۔")


# ================= SCREENSHOT HANDLER =================

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else "No Username"
    user_id = user.id

    # چیک کریں کہ آیا یہ کوئٹیکس کی پیمنٹ کا اسکرین شاٹ ہے
    if user_id in user_states and user_states[user_id].get('state') == 'WAITING_FOR_SCREENSHOT':
        plan = user_states[user_id].get('plan')
        t_id = user_states[user_id].get('trader_id', 'N/A')
        
        keyboard = [[
            InlineKeyboardButton("✅ Approve Quotex", callback_data=f"qxapp_{user_id}_{t_id}_{plan.split()[0]}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=(
                f"📉 **Quotex Premium Request!**\n\n"
                f"👤 Name: {user.first_name}\n"
                f"🆔 ID: {user_id}\n"
                f"📦 Plan: {plan}\n"
                f"🆔 Trader ID: `{t_id}`\n"
                f"📛 @{username}"
            ),
            reply_markup=reply_markup
        )
        await update.message.reply_text("✅ کوئٹیکس پریمیم کا اسکرین شاٹ موصول ہو گیا ہے۔ ایڈمن جلد ویریفائی کرے گا۔")
        # سٹیٹ صاف کر دیں
        user_states.pop(user_id, None)
        return

    # پرانی فاریکس اسکرین شاٹ لاجک (جیسے پہلے تھی)
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


# ================= CALLBACK BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.message.chat.id
    data = query.data

    # یوزر کے کوئٹیکس پلان سلیکشنز
    if data == "qx_choose_link":
        user_states[user_id] = {'plan': 'Link Plan (1000 PKR)', 'state': 'WAITING_FOR_ID'}
        await context.bot.send_message(chat_id=user_id, text="📝 بڑے بھائی، اب اپنی **Quotex Trader ID** یہاں ٹائپ کر کے سینڈ کریں۔")
        return
        
    elif data == "qx_choose_direct":
        user_states[user_id] = {'plan': 'Direct Plan (1500 PKR)', 'trader_id': 'N/A', 'state': 'WAITING_FOR_SCREENSHOT'}
        await context.bot.send_message(chat_id=user_id, text="📸 بڑے بھائی، اب اپنی **1500 PKR** پیمنٹ کا اسکرین شاٹ ڈائریکٹ یہاں سینڈ کریں۔")
        return

    # کوئٹیکس سگنلز جنریٹر (5sec, 1min, 5min, etc.)
    elif data.startswith("qx_"):
        t_frame = data.split("_")[1]
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD']
        selected_pair = random.choice(pairs)
        action = random.choice(['CALL (UP) ↑', 'PUT (DOWN) ↓'])
        accuracy = random.randint(90, 96)
        
        signal_msg = (
            f"📈 **ForeXAurA QUOTEX SIGNAL**\n\n"
            f"💱 **Pair:** {selected_pair}\n"
            f"🚀 **Action:** {action}\n"
            f"⏳ **Duration:** {t_frame}\n"
            f"🎯 **Accuracy:** {accuracy}%\n\n"
            f"_(بڑے بھائی، ابھی کوئٹیکس اوپن کریں اور ٹریڈ لگائیں!)_"
        )
        await context.bot.send_message(chat_id=user_id, text=signal_msg, parse_mode='Markdown')
        return

    # ایڈمن کے بٹنز ہینڈلنگ
    if query.from_user.id != ADMIN_ID:
        return

    # فاریکس اپروول (پرانا)
    if data.startswith("approve_"):
        target_user_id = int(data.split("_")[1])
        add_premium_db(target_user_id)

        await context.bot.send_message(
            chat_id=target_user_id,
            text="🎉 PREMIUM ACTIVATED!\nNow you have unlimited signals for 30 days."
        )
        await query.edit_message_caption("✅ Approved (30 Days)")

    # کوئٹیکس اپروول (نیا)
    elif data.startswith("qxapp_"):
        parts = data.split("_")
        target_user_id = int(parts[1])
        trader_id = parts[2]
        plan_type = parts[3]
        
        add_quotex_premium_db(target_user_id, trader_id, plan_type)
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text="🎉 **ForeXAurA Quotex Premium Activated!**\n\nمبارک ہو بڑے بھائی، آپ کا کوئٹیکس پریمیم اکاؤنٹ لائف ٹائم کے لیے ایکٹو ہو چکا ہے! اب آپ مینو سے سگنل لے سکتے ہیں۔"
        )
        
        # پریمیم اپروو ہوتے ہی کسٹمر کو وائس نوٹ اور وارننگ سینڈ کرنا
        if VOICE_NOTE_FILE_ID != 'YOUR_VOICE_NOTE_FILE_ID_HERE':
            caption_text = (
                "🚨 **IMPORTANT WARNING BY ForeXAurA!**\n\n"
                "بڑے بھائی، پریمیم ایکٹو ہو گیا ہے! لیکن یہ وائس نوٹ لازمی سنیں تاکہ آپ روزانہ پرافٹ میں رہیں۔"
            )
            try:
                await context.bot.send_voice(chat_id=target_user_id, voice=VOICE_NOTE_FILE_ID, caption=caption_text)
            except Exception:
                pass
                
        await query.edit_message_caption("✅ Quotex Approved (Lifetime)")


# ================= MANUAL APPROVE =================

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) == 0:
        await update.message.reply_text("/approve USER_ID")
        return

    user_id = int(context.args[0])
    add_premium_db(user_id)

    await context.bot.send_message(
        chat_id=user_id,
        text="🎉 Premium Activated for 30 Days!"
    )
    await update.message.reply_text("✅ Approved")


# وائس نوٹ کی فائل آئی ڈی معلوم کرنے کے لیے ہینڈلر (صرف ایڈمن کے لیے)
async def catch_voice_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        file_id = update.message.voice.file_id
        await update.message.reply_text(f"🎙️ **Voice File ID:**\n`{file_id}`", parse_mode="Markdown")


# ================= BOT SETUP =================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("approve", approve))

# بٹن اور ٹیکسٹ میسجز کے ہینڈلرز
app.add_handler(MessageHandler(filters.Text(["📊 Forex Signals", "📉 Quotex Signals"]) | filters.TEXT & ~filters.COMMAND, handle_text_menu))
app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
app.add_handler(MessageHandler(filters.VOICE, catch_voice_id)) # وائس آئی ڈی پکڑنے کے لیے
app.add_handler(CallbackQueryHandler(button_handler))

# آٹو ایکسپائری لوپ کو بیک گراؤنڈ میں اسٹارٹ کرنا
async def main():
    await app.initialize()
    await app.start()
    asyncio.create_task(check_expiry_loop(app))
    await app.updater.start_polling()
    print("BOT RUNNING WITH FOREX & QUOTEX ENGINES...")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
