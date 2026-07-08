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
