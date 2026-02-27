# main.py - ДИАГНОСТИЧЕСКАЯ ВЕРСИЯ
import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "0")

print(f"✅ CONFIG: ADMIN_ID={ADMIN_ID}")

async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на ЛЮБОЕ сообщение"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text if update.message.text else "[без текста]"
    
    # Логируем ВСЁ
    print(f"🔍 MESSAGE RECEIVED: user_id={user_id}, name={user_name}, text='{text}', ADMIN_ID={ADMIN_ID}")
    
    # Отвечаем всем (для теста)
    await update.message.reply_text(
        f"🤖 БОТ ЖИВ!\n\n"
        f"Твой ID: {user_id}\n"
        f"Ожидаемый ADMIN_ID: {ADMIN_ID}\n"
        f"Текст: {text}\n\n"
        f"Если ID совпадают — бот работает! ✅"
    )

def main():
    print("🚀 STARTING DIAGNOSTIC BOT...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обрабатываем ВСЕ текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_all))
    # Также обрабатываем /start
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", echo_all))
    
    print("✅ Handlers registered. Starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
