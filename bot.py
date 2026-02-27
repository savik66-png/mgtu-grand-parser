#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
БОТ ДЛЯ ЗАПУСКА ПАРСЕРА ГРАНТОВ ИЗ TELEGRAM
ДИАГНОСТИЧЕСКАЯ ВЕРСИЯ — логирует ВСЕ сообщения
"""
import os
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Добавляем текущую папку в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию запуска из парсера
from mgtu_parser import main as run_parser

# Настройки из переменных окружения (BotHost)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002752798613")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

# ==================== ОБРАБОТЧИКИ ====================

async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ЛОГИРУЕТ ВСЕ СООБЩЕНИЯ — для диагностики"""
    try:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
        chat_type = update.effective_chat.type if update.effective_chat else "Unknown"
        text = update.message.text if update.message and update.message.text else "[нет текста]"
        
        logger.info(f"🔍 ПОЛУЧЕНО: user_id={user_id}, chat_id={chat_id}, type={chat_type}, text='{text}'")
        logger.info(f"🔍 ОЖИДАЕМ: ADMIN_ID={ADMIN_ID}, TELEGRAM_CHAT_ID={TELEGRAM_CHAT_ID}")
        
        # Проверяем, тот ли это пользователь
        if user_id != ADMIN_ID:
            logger.warning(f"⚠️ Доступ запрещён: user_id={user_id} != ADMIN_ID={ADMIN_ID}")
            await update.message.reply_text(f"❌ Доступ запрещён\nТвой ID: {user_id}\nНужен: {ADMIN_ID}")
            return
        
        # Отвечаем, что бот жив
        await update.message.reply_text(f"✅ Бот жив!\nChat: {chat_id} ({chat_type})\nТвой ID: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в echo_all: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        logger.info(f"🚀 /start от user_id={user_id}, chat_id={chat_id}, ADMIN_ID={ADMIN_ID}")
        
        if user_id != ADMIN_ID:
            await update.message.reply_text(f"❌ Доступ запрещён\nТвой ID: {user_id}")
            return
        
        await update.message.reply_text("⏳ <b>Запуск парсера грантов...</b>", parse_mode='HTML')
        
        try:
            run_parser()
            await update.message.reply_text("✅ <b>Готово!</b> Проверь чат.", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка парсера: {e}")
            await update.message.reply_text(f"❌ <b>Ошибка:</b> {str(e)[:200]}", parse_mode='HTML')
    except Exception as e:
        logger.error(f"❌ Ошибка в start: {e}")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /check (алиас)"""
    await start(update, context)

# ==================== ЗАПУСК ====================
def main():
    logger.info("🚀 Запуск ДИАГНОСТИЧЕСКОГО бота...")
    logger.info(f"Token: {TELEGRAM_BOT_TOKEN[:10] if TELEGRAM_BOT_TOKEN else 'NONE'}...")
    logger.info(f"ADMIN_ID: {ADMIN_ID}")
    logger.info(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем ВСЕ обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    # Обработчик для ВСЕХ текстовых сообщений (диагностика)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_all))
    
    logger.info("✅ Обработчики готовы. Запуск polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
