from telegram import ReplyKeyboardMarkup

def main_menu():

    keyboard = [
        ["📊 Forex Signals", "📉 Quotex Signals"],
        ["💎 Premium", "👤 My Account"],
        ["📞 Support", "ℹ️ Help"]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def forex_menu():

    keyboard = [
        ["🥇 XAU/USD", "💶 EUR/USD"],
        ["💷 GBP/USD", "💴 USD/JPY"],
        ["🇦🇺 AUD/USD", "🇺🇸 USD/CAD"],
        ["🇳🇿 NZD/USD", "💶 EUR/JPY"],
        ["💷 GBP/JPY", "₿ BTC/USD"],
        ["🔙 Back"]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
