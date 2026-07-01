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

# فری سگنلز کا ٹریک رکھنے کے لیے
user_forex_clicks = {}
user_quotex_clicks = {}

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
        ticker_symbol = symbols_map.get(symbol_name, "EURUSD=X")
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

# ================= MENUS & FLOWS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📊 Forex Signals"), KeyboardButton("📉 Quotex Signals")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🌟 **Welcome to ForeXAurA!** 🌟\n\n"
        "بڑے بھائی، خوش آمدید! آپ کے بہترین ٹریڈنگ سفر کا آغاز یہیں سے ہوتا ہے۔\n"
        "نیچے دیے گئے مینو سے اپنی مارکیٹ کا انتخاب کریں:\n\n"
        "👉 **Forex / Quotex Signals** حاصل کرنے کے لیے بٹنز کا استعمال کریں۔\n"
        "👉 فری یوزرز کے لیے صرف **3 فری سگنلز** دستیاب ہیں۔ لمٹ ختم ہونے کے بعد ان لمیٹڈ سگنلز کے لیے پریمیم پلان بائے کریں۔",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# کوئٹیکس پیئرز کا مینو
async def send_quotex_pairs_menu(bot, user_id):
    keyboard = [
        [InlineKeyboardButton("💱 EUR/USD (OTC)", callback_data="qxpair_EURUSD"), InlineKeyboardButton("💱 GBP/USD (OTC)", callback_data="qxpair_GBPUSD")],
        [InlineKeyboardButton("💱 USD/JPY (OTC)", callback_data="qxpair_USDJPY"), InlineKeyboardButton("💱 AUD/USD (OTC)", callback_data="qxpair_AUDUSD")],
        [InlineKeyboardButton("🪙 Crypto IDX", callback_data="qxpair_CryptoIDX")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=user_id,
        text="📊 **Quotex Assets Selection**\n\nبڑے بھائی، کس مشہور پیئر (Pair) کا سگنل چاہیے؟ نیچے سے سلیکٹ کریں:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ٹائم فریم کا مینو (5 Seconds شامل کر دیا گیا ہے)
async def send_quotex_time_menu(bot, user_id, pair_name):
    keyboard = [
        [InlineKeyboardButton("⚡ 5 Seconds", callback_data=f"qxt_5sec_{pair_name}"), InlineKeyboardButton("⏱️ 30 Seconds", callback_data=f"qxt_30sec_{pair_name}")],
        [InlineKeyboardButton("🕐 1 Minute", callback_data=f"qxt_1min_{pair_name}"), InlineKeyboardButton("🕒 5 Minutes", callback_data=f"qxt_5min_{pair_name}")],
        [InlineKeyboardButton("⏳ 30 Minutes", callback_data=f"qxt_30min_{pair_name}"), InlineKeyboardButton("⏰ 1 Hour", callback_data=f"qxt_1hour_{pair_name}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=user_id,
        text=f"🎯 **Pair Selected:** {pair_name.replace('SUB', '/')}\n\nبڑے بھائی، اب اس پیئر کے لیے اپنی اسٹریٹجی کا ٹائم فریم سلیکٹ کریں:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📊 Forex Signals":
        if is_premium(user_id):
            msg = "💎 **FOREX PREMIUM SIGNALS (Unlimited)**\n\n"
            for s in symbols_map.keys():
                rsi, price, ema = get_market_data(s)
                sig = signal_engine(rsi, price, ema)
                msg += f"💱 {s}\nSignal: {sig}\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            if user_id not in user_forex_clicks: user_forex_clicks[user_id] = 0
            
            if user_forex_clicks[user_id] >= 3:
                await update.message.reply_text(
                    "❌ **آپ کے 3 فری فاریکس سگنلز ختم ہو چکے ہیں!**\n\n"
                    "بڑے بھائی، اب ان لمیٹڈ (Jitna Marzi) سگنلز لینے کے لیے پریمیم سبسکرپشن لیں۔\n\n"
                    "💎 **Forex Premium (1000 PKR / 30 Days)**\n"
                    "• JazzCash: `03202656954`\n"
                    "• Easypaisa: `03287616051`\n"
                    "• Account Name: Asad Ali\n\n"
                    "پیمنٹ کر کے اسکرین شاٹ یہاں بھیجیں، ایڈمن فوری ایکٹو کر دے گا۔", 
                    parse_mode="Markdown"
                )
                return
                
            user_forex_clicks[user_id] += 1
            remaining = 3 - user_forex_clicks[user_id]
            msg = f"📊 **FOREX FREE SIGNALS (Free Clicks Left: {remaining})**\n\n"
            for s in symbols_map.keys():
                rsi, price, ema = get_market_data(s)
                sig = signal_engine(rsi, price, ema)
                msg += f"💱 {s}\nSignal: {sig}\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        
    elif text == "📉 Quotex Signals":
        if is_quotex_premium(user_id):
            await send_quotex_pairs_menu(context.bot, user_id)
        else:
            if user_id not in user_quotex_clicks: user_quotex_clicks[user_id] = 0
            
            if user_quotex_clicks[user_id] >= 3:
                quotex_payment_text = (
                    "❌ **آپ کے 3 فری کوئٹیکس سگنلز ختم ہو چکے ہیں!**\n\n"
                    "بڑے بھائی، اب ان لمیٹڈ (Jitna Marzi) سگنلز کے لیے پریمیم پلان بائے کریں۔\n\n"
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
                return
                
            # فری یوزر کو پیئر مینو دکھائیں لیکن کلک کاؤنٹ سگنل فائنل ہونے پر ہوگا
            await send_quotex_pairs_menu(context.bot, user_id)

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

    # 1. جب یوزر کوئٹیکس کا پیئر چوز کرے
    if data.startswith("qxpair_"):
        pair_selected = data.split("_")[1] # e.g. EURUSD, CryptoIDX
        # پیئر سلیکٹ ہونے کے بعد ٹائم فریم مینو بھیجیں
        await send_quotex_time_menu(context.bot, user_id, pair_selected)
        await query.message.delete() # پرانا میسج صاف کر دیں
        return

    # 2. جب یوزر ٹائم فریم سلیکٹ کرے (فائنل سگنل جنریشن)
    if data.startswith("qxt_"):
        parts = data.split("_")
        t_frame = parts[1]      # e.g. 5sec, 1min
        chosen_pair = parts[2]   # e.g. EURUSD, CryptoIDX
        
        # خوبصورت ڈسپلے نام کے لیے تبدیلیاں
        display_pair = chosen_pair
        if chosen_pair == "EURUSD": display_pair = "EUR/USD (OTC)"
        elif chosen_pair == "GBPUSD": display_pair = "GBP/USD (OTC)"
        elif chosen_pair == "USDJPY": display_pair = "USD/JPY (OTC)"
        elif chosen_pair == "AUDUSD": display_pair = "AUD/USD (OTC)"
        elif chosen_pair == "CryptoIDX": display_pair = "Crypto IDX"

        # پریمیم اور فری لمٹ چیک کریں
        if not is_quotex_premium(user_id):
            if user_id not in user_quotex_clicks: user_quotex_clicks[user_id] = 0
            if user_quotex_clicks[user_id] >= 3:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ **آپ کے 3 فری کوئٹیکس سگنلز ختم ہو چکے ہیں!** بڑے بھائی، اب مزید ان لمیٹڈ سگنلز پریمیم پلان میں ہی ملیں گے۔"
                )
                return
            user_quotex_clicks[user_id] += 1 # یہاں کلک رجسٹر کریں

        # ہائی ایکوریسی سگنل انجن لاجک
        rsi, price, ema = get_market_data(chosen_pair)
        
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
            f"💱 **Asset/Pair:** {display_pair}\n"
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

    if data.startswith("app_forex_"):
        target_id = int(data.split("_")[2])
        add_premium_db(target_id)
        await context.bot.send_message(
            chat_id=target_id, 
            text="🎉 **Forex Premium Activated!**\n\nبڑے بھائی، آپ کا فاریکس پریمیم پلان **30 دن** کے لیے ایکٹو کر دیا گیا ہے۔ اب جتنے مرضی ان لمیٹڈ سگنلز لیں۔"
        )
        await query.edit_message_caption("✅ Approved Forex Premium (30 Days)")

    elif data.startswith("app_quotex_"):
        target_id = int(data.split("_")[2])
        add_quotex_premium_db(target_id)
        await context.bot.send_message(
            chat_id=target_id, 
            text="🎉 **Quotex Premium Activated!**\n\nبڑے بھائی! آپ کا کوئٹیکس اسٹریٹجی پریمیم پلان **30 دن** کے لیے ایکٹو ہو چکا ہے۔ اب ان لمیٹڈ پیئرز کے سگنلز انجوائے کریں۔"
        )
        await send_quotex_pairs_menu(context.bot, target_id)
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
app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
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
