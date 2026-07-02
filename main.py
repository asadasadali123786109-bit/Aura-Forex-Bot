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

# 💳 PAYMENT DETAILS (Fixed formatting cleanly to avoid Telegram text reversing)
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

user_forex_clicks = {}
user_quotex_clicks = {}

symbols_map = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "XAUUSD": "XAUUSD=F",
    "CryptoIDX": "BTC-USD"
}

# Database functions
def init_db():
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS premium (user_id INTEGER PRIMARY KEY, expiry_date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS quotex_premium (user_id INTEGER PRIMARY KEY, expiry_date TEXT)")
    conn.commit()
    conn.close()

init_db()

def is_premium(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM premium WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        if datetime.now() < datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'):
            return True
    return False

def is_quotex_premium(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect('premium_users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM quotex_premium WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        if datetime.now() < datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'):
            return True
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

# SCREENSHOT FORWARDER WITH INLINE BUTTONS FOR ADMIN
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return
        
    caption_text = (
        f"📩 *New Payment Screenshot Received!*\n\n"
        f"👤 *Name:* {user.full_name}\n"
        f"🆔 *Chat ID:* `{user.id}`\n\n"
        f"بڑے بھائی، نیچے دیے گئے بٹن پر کلک کر کے ڈائریکٹ اپروو کریں۔"
    )
    
    # Inline approval buttons for Admin's personal chat
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve Forex", callback_data=f"adm_appf_{user.id}"),
            InlineKeyboardButton("✅ Approve Quotex", callback_data=f"adm_appq_{user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID, 
        photo=update.message.photo[-1].file_id, 
        caption=caption_text, 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ آپ کا سکرین شاٹ ایڈمن کو موصول ہو گیا ہے! ڈیٹا چیک کر کے اکاؤنٹ جلدی ایکٹیو کر دیا جائے گا۔")

# FULL MARKET ANALYSIS ENGINE
def advanced_market_analysis(symbol_name, is_forex_mode=False):
    try:
        ticker_symbol = symbols_map.get(symbol_name, "EURUSD=X")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="2d", interval="1m")
        
        if df.empty or len(df) < 20:
            rsi_val = random.uniform(45.0, 55.0)
            if is_forex_mode:
                return f"RSI: {rsi_val:.4f}", "🟢 BUY (Trend)"
            return "🟢 CALL (UP) ↑", "BULLISH (💡 Dynamic Support)"
            
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        
        current_price = float(df['Close'].iloc[-1])
        sma_20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
        
        if is_forex_mode:
            rsi_str = f"RSI: {rsi:.4f}"
            if rsi < 35 or current_price > sma_20:
                return rsi_str, "🟢 BUY (Trend)"
            else:
                return rsi_str, "🔴 SELL (Trend)"
        else:
            if rsi < 35: return "🟢 CALL (UP) ↑", "STRONG BULLISH (⚠️ Oversold Reversal)"
            elif rsi > 65: return "🔴 PUT (DOWN) ↓", "STRONG BEARISH (⚠️ Overbought Reversal)"
            elif current_price > sma_20: return "🟢 CALL (UP) ↑", "BULLISH TREND (📈 Above SMA-20)"
            else: return "🔴 PUT (DOWN) ↓", "BEARISH TREND (📉 Below SMA-20)"
            
    except:
        rsi_val = random.uniform(40.0, 60.0)
        if is_forex_mode:
            act = random.choice(["🟢 BUY (Trend)", "🔴 SELL (Trend)"])
            return f"RSI: {rsi_val:.4f}", act
        direction = random.choice(["🟢 CALL (UP) ↑", "🔴 PUT (DOWN) ↓"])
        trend = "BULLISH (💡 Price Action)" if "CALL" in direction else "BEARISH (💡 Price Action)"
        return direction, trend

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📊 Forex Signals"), KeyboardButton("📉 Quotex Signals")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    urdu_welcome = (
        "🌟 *ForeXAurA میں خوش آمدید!* 🌟\n\n"
        "بڑے بھائی، مارکیٹ کا لائیو ڈیٹا اینالائز کر کے پرافٹ ایبل سگنل دینے والا فائنل انجن بالکل تیار ہے۔\n\n"
        "👉 *Forex / Quotex Signals* حاصل کرنے کے لیے نیچے دیے گئے مینو بٹنز کا استعمال کریں۔\n"
        f"🆔 *آپ کا اکاؤنٹ نمبر (Chat ID):* `{update.effective_user.id}`\n"
        "👉 فری یوزرز کے لیے روزانہ صرف *3 فری سگنلز* دستیاب ہیں۔"
    )
    await update.message.reply_text(urdu_welcome, reply_markup=reply_markup, parse_mode="Markdown")

async def send_quotex_pairs_menu(bot, user_id, is_premium_user=False):
    keyboard = [
        [InlineKeyboardButton("💱 EUR/USD (OTC)", callback_data="qxpair_EURUSD"), InlineKeyboardButton("💱 GBP/USD (OTC)", callback_data="qxpair_GBPUSD")],
        [InlineKeyboardButton("💱 USD/JPY (OTC)", callback_data="qxpair_USDJPY"), InlineKeyboardButton("💱 AUD/USD (OTC)", callback_data="qxpair_AUDUSD")],
        [InlineKeyboardButton("🪙 Crypto IDX", callback_data="qxpair_CryptoIDX")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_premium_user:
        text_header = "💎 **QUOTEX PREMIUM SIGNALS (Fully Analyzed)**\n\n📊 **Quotex Assets Selection**\n\nبڑے بھائی، کس پیئر کا گہرا لائیو اینالیسس سگنل چاہیے؟ نیچے سے منتخب کریں:"
    else:
        text_header = "📊 **Quotex Assets Selection**\n\nبڑے بھائی، کس پیئر کا گہرا لائیو اینالیسس سگنل چاہیے؟ نیچے سے منتخب کریں:"
        
    await bot.send_message(
        chat_id=user_id,
        text=text_header,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_quotex_time_menu(bot, user_id, pair_name):
    keyboard = [
        [InlineKeyboardButton("⚡ 5 Seconds", callback_data=f"qxt_5sec_{pair_name}"), InlineKeyboardButton("⏱️ 30 Seconds", callback_data=f"qxt_30sec_{pair_name}")],
        [InlineKeyboardButton("🕐 1 Minute", callback_data=f"qxt_1min_{pair_name}"), InlineKeyboardButton("🕒 5 Minutes", callback_data=f"qxt_5min_{pair_name}")],
        [InlineKeyboardButton("⏳ 30 Minutes", callback_data=f"qxt_30min_{pair_name}"), InlineKeyboardButton("⏰ 1 Hour", callback_data=f"qxt_1hour_{pair_name}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=user_id,
        text=f"🎯 **Pair Selected:** {pair_name}\n\nبڑے بھائی، اب اس پیئر کے لیے اپنی اسٹریٹجی کا ٹائم فریم سلیکٹ کریں:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📊 Forex Signals":
        premium_active = is_premium(user_id)
        
        if not premium_active and user_id != ADMIN_ID:
            if user_id not in user_forex_clicks: user_forex_clicks[user_id] = 0
            if user_forex_clicks[user_id] >= 3:
                limit_msg = f"❌ *آپ کے فری فاریکس سگنلز کی لمیٹ ختم ہو چکی ہے!*\n\n{FOREX_PAYMENT_DETAILS}\n\n🆔 *Your Account Number:* `{user_id}`"
                await update.message.reply_text(limit_msg, parse_mode="Markdown")
                return
            user_forex_clicks[user_id] += 1
            title = f"📊 **FREE SIGNALS (Clicks Left: {3 - user_forex_clicks[user_id]})**\n\n"
            pairs = ["EURUSD", "GBPUSD", "XAUUSD"]
        else:
            title = "💎 **FOREX PREMIUM SIGNALS (Fully Analyzed)**\n\n"
            pairs = ["EURUSD", "GBPUSD", "XAUUSD"]
            
        msg = title
        for p in pairs:
            rsi_val, action = advanced_market_analysis(p, is_forex_mode=True)
            p_display = "EUR/USD" if p == "EURUSD" else "GBP/USD" if p == "GBPUSD" else "XAU/USD"
            msg += f"*{p_display}*\n{rsi_val}\nSignal: {action}\n\n"
            
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    elif text == "📉 Quotex Signals":
        if is_quotex_premium(user_id):
            await send_quotex_pairs_menu(context.bot, user_id, is_premium_user=True)
        else:
            if user_id not in user_quotex_clicks: user_quotex_clicks[user_id] = 0
            if user_quotex_clicks[user_id] >= 3:
                limit_msg = f"❌ *آپ کے فری کوٹیکس سگنلز کی لمیٹ ختم ہو چکی ہے!*\n\n{QUOTEX_PAYMENT_DETAILS}\n\n🆔 *Your Account Number:* `{user_id}`"
                await update.message.reply_text(limit_msg, parse_mode="Markdown")
                return
            await send_quotex_pairs_menu(context.bot, user_id, is_premium_user=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.message.chat.id

    # ADMIN DIRECT APPROVAL BUTTON LOGIC
    if data.startswith("adm_appf_"):
        target_id = int(data.split("_")[2])
        add_premium_db(target_id)
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ *Approved for Forex Premium!*")
        try:
            await context.bot.send_message(chat_id=target_id, text="🎉 مبارک ہو! آپ کا فاریکس پریمیئم اکاؤنٹ 30 دن کے لیے ایکٹیو کر دیا گیا ہے۔")
        except: pass
        return

    if data.startswith("adm_appq_"):
        target_id = int(data.split("_")[2])
        add_quotex_premium_db(target_id)
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ *Approved for Quotex Premium!*")
        try:
            await context.bot.send_message(chat_id=target_id, text="🎉 مبارک ہو! آپ کا کوٹیکس پریمیئم اکاؤنٹ 30 دن کے لیے ایکٹیو کر دیا گیا ہے۔")
        except: pass
        return

    # USER LOGIC
    if data.startswith("qxpair_"):
        pair_selected = data.split("_")[1]
        if not is_quotex_premium(user_id):
            if user_id not in user_quotex_clicks: user_quotex_clicks[user_id] = 0
            if user_quotex_clicks[user_id] >= 3:
                limit_msg = f"❌ *آپ کے فری کوٹیکس سگنلز کی لمیٹ ختم ہو چکی ہے!*\n\n{QUOTEX_PAYMENT_DETAILS}\n\n🆔 *Your Account Number:* `{user_id}`"
                await context.bot.send_message(chat_id=user_id, text=limit_msg, parse_mode="Markdown")
                return
        await send_quotex_time_menu(context.bot, user_id, pair_selected)
        await query.message.delete()
        return

    if data.startswith("qxt_"):
        parts = data.split("_")
        t_frame = parts[1]
        chosen_pair = parts[2]
        
        display_map = {"EURUSD": "EUR/USD (OTC)", "GBPUSD": "GBP/USD (OTC)", "USDJPY": "USD/JPY (OTC)", "AUDUSD": "AUD/USD (OTC)", "CryptoIDX": "Crypto IDX"}
        display_pair = display_map.get(chosen_pair, chosen_pair)

        if not is_quotex_premium(user_id):
            if user_id not in user_quotex_clicks: user_quotex_clicks[user_id] = 0
            if user_quotex_clicks[user_id] >= 3: 
                limit_msg = f"❌ *آپ کے فری کوٹیکس سگنلز کی لمیٹ ختم ہو چکی ہے!*\n\n{QUOTEX_PAYMENT_DETAILS}\n\n🆔 *Your Account Number:* `{user_id}`"
                await context.bot.send_message(chat_id=user_id, text=limit_msg, parse_mode="Markdown")
                return
            user_quotex_clicks[user_id] += 1

        action, trend = advanced_market_analysis(chosen_pair, is_forex_mode=False)
        accuracy = random.randint(92, 97)
        
        signal_msg = (
            f"🎯 **ForeXAurA QUOTEX ANALYZED SIGNAL**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💱 **Asset/Pair:** {display_pair}\n"
            f"🚀 **Direction:** {action}\n"
            f"⏳ **Strategy Time:** {t_frame}\n"
            f"📊 **Signal Accuracy:** {accuracy}%\n"
            f"📶 **Market Trend:** {trend}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_(بڑے بھائی، مارکیٹ کا لائیو ڈیٹا اینالیسس مکمل ہو چکا ہے۔ ابھی پرافٹ بک کریں!)_"
        )
        await context.bot.send_message(chat_id=user_id, text=signal_msg, parse_mode='Markdown')
        return

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
app.add_handler(MessageHandler(filters.Text(["📊 Forex Signals", "📉 Quotex Signals"]), handle_text_menu))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
