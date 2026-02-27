# bot.py - ПРОСТОЙ БОТ ДЛЯ ЗАПУСКА ПАРСЕРА
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Импортируем функцию запуска из твоего парсера
from mgtu_parser import main as run_parser

# Настройки из переменных окружения (BotHost)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    logger.info(f"/start от user_id={user_id}, ADMIN_ID={ADMIN_ID}")
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text("⏳ <b>Запуск парсера грантов...</b>", parse_mode='HTML')
    
    try:
        # Запускаем твой парсер
        run_parser()
        await update.message.reply_text("✅ <b>Готово!</b> Проверь чат.", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ <b>Ошибка:</b> {str(e)[:200]}", parse_mode='HTML')

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /check (алиас для /start)"""
    await start(update, context)

# ==================== ЗАПУСК ====================
def main():
    logger.info("🚀 Запуск бота-обёртки...")
    logger.info(f"Token: {TELEGRAM_BOT_TOKEN[:10] if TELEGRAM_BOT_TOKEN else 'NONE'}...")
    logger.info(f"ADMIN_ID: {ADMIN_ID}")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    
    logger.info("✅ Обработчики готовы. Запуск polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()