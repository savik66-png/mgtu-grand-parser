#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""БОТ ДЛЯ ЗАПУСКА ПАРСЕРА ИЗ TELEGRAM"""
import os, sys, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgtu_parser import main as run_parser

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    logger.info(f"/start от {uid}, ADMIN_ID={ADMIN_ID}")
    if uid != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    await update.message.reply_text("⏳ <b>Запуск парсера...</b>", parse_mode='HTML')
    try:
        run_parser()
        await update.message.reply_text("✅ <b>Готово! Проверь чат.</b>", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:150]}", parse_mode='HTML')

def main():
    logger.info(f"🚀 Бот запущен. Token: {TOKEN[:10] if TOKEN else 'NONE'}...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", start))
    logger.info("✅ Запуск polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
