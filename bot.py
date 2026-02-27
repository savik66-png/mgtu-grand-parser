#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""БОТ ДЛЯ ЗАПУСКА ПАРСЕРА — ДИАГНОСТИКА"""
import os, sys, logging, time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Пробуем импортировать парсер
try:
    from mgtu_parser import main as run_parser
    PARSER_LOADED = True
    logging.info("✅ Парсер импортирован успешно")
except Exception as e:
    PARSER_LOADED = False
    logging.error(f"❌ Ошибка импорта парсера: {e}")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ЛОГИРУЕТ ВСЕ СООБЩЕНИЯ"""
    try:
        uid = update.effective_user.id if update.effective_user else "Unknown"
        cid = update.effective_chat.id if update.effective_chat else "Unknown"
        txt = update.message.text if update.message and update.message.text else "[нет текста]"
        logger.info(f"🔍 MESSAGE: uid={uid}, cid={cid}, text='{txt}', ADMIN_ID={ADMIN_ID}")
        if uid == ADMIN_ID:
            await update.message.reply_text(f"✅ Бот жив!\nТвой ID: {uid}\nТекст: {txt}")
        else:
            await update.message.reply_text(f"❌ Доступ запрещён\nТвой ID: {uid}\nНужен: {ADMIN_ID}")
    except Exception as e:
        logger.error(f"❌ Ошибка echo_all: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    try:
        uid = update.effective_user.id
        logger.info(f"🚀 /start от uid={uid}, ADMIN_ID={ADMIN_ID}, PARSER_LOADED={PARSER_LOADED}")
        if uid != ADMIN_ID:
            await update.message.reply_text(f"❌ Доступ запрещён\nТвой ID: {uid}")
            return
        await update.message.reply_text("⏳ <b>Запуск...</b>", parse_mode='HTML')
        if PARSER_LOADED:
            run_parser()
            await update.message.reply_text("✅ <b>Готово!</b>", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Парсер не загружен. Проверь логи.")
    except Exception as e:
        logger.error(f"❌ Ошибка start: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:150]}", parse_mode='HTML')

def main():
    logger.info(f"🚀 Бот запущен. Token: {TOKEN[:10] if TOKEN else 'NONE'}..., ADMIN_ID={ADMIN_ID}")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_all))
    logger.info("✅ Handlers ready. Starting polling...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
