from telegram import Update
from telegram.ext import ContextTypes

from database import add_user
from utils.keyboard import main_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user.id,
        user.username,
        user.first_name
    )

    aawait update.message.reply_text(
    f"السلام علیکم {user.first_name} 👋\n\n"
    "Aura Forex Bot میں خوش آمدید.",
    reply_markup=main_menu()
)
