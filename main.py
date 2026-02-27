# main.py - ТЕСТОВАЯ ВЕРСИЯ (без парсера)
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
import storage  # Только база данных, без парсера

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

logger.info(f"✅ CONFIG: ADMIN_IDS={config.ADMIN_IDS}")

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проверить гранты", callback_data="check")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🔍 /start от user_id={user_id}")
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text(
        "👋 <b>Бот работает!</b>\n\nНажми кнопку для теста.",
        parse_mode='HTML',
        reply_markup=get_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    if query.data == "check":
        # ВРЕМЕННО: просто тестовый ответ
        await query.edit_message_text("✅ Кнопка нажата!\n(Парсер подключим следующим шагом)")
    elif query.data == "stats":
        stats = storage.get_stats()
        await query.edit_message_text(
            f"📊 <b>Статистика</b>\n\nВ базе: {stats['total_grants']} грантов",
            parse_mode='HTML'
        )

def main():
    logger.info("🚀 Запуск бота (тест без парсера)...")
    
    storage.init_db()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("✅ Handlers registered")
    
    # Простой polling без обёрток
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
