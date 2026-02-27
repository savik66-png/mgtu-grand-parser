# main.py - МИНИМАЛЬНАЯ ВЕРСИЯ
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

print(f"✅ CONFIG: BOT_TOKEN starts with {BOT_TOKEN[:10] if BOT_TOKEN else 'NONE'}..., ADMIN_ID={ADMIN_ID}")

# Простая клавиатура
def get_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Проверить гранты", callback_data="check")]])

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔍 COMMAND /start received from user_id={user_id}, expected ADMIN_ID={ADMIN_ID}")
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text(
        "👋 Бот работает!\nНажми кнопку ниже для проверки грантов.",
        reply_markup=get_keyboard()
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    if query.data == "check":
        await query.edit_message_text("✅ Кнопка нажата! Парсер готов к запуску.\n(Логика парсера подключается отдельно)")

# Запуск
def main():
    print("🚀 STARTING BOT WITH POLLING...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Handlers registered. Starting polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    print("🛑 Polling stopped")

if __name__ == "__main__":
    main()
