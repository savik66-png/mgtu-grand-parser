#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот для мониторинга грантов МГТУ им. Баумана
"""
import os
import sys
import logging
import asyncio
import json
from datetime import time as dtime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, JobQueue
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import run_parser, SETTINGS_FILE

# ─── Настройки из переменных окружения ────────────────────────────────────────
TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", str(ADMIN_ID))

# ─── Логирование ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    force=True,
)
logger = logging.getLogger(__name__)


def load_settings() -> dict:
    defaults = {"min_amount": 5_000_000, "min_days": 14}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


# ─── Команды ──────────────────────────────────────────────────────────────────

async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"📨 Обновление от {update.effective_user.id if update.effective_user else 'неизвестно'}: {update.message.text if update.message else update}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start от {update.effective_user.id}, ADMIN_ID={ADMIN_ID}")
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    settings = load_settings()
    text = (
        "👋 <b>Бот мониторинга грантов МГТУ</b>\n\n"
        "Доступные команды:\n"
        "/check — запустить парсер прямо сейчас\n"
        "/status — текущие настройки\n"
        "/setamount <сумма> — минимальная сумма гранта в рублях/год\n"
        "  Пример: /setamount 10000000\n\n"
        f"⚙️ <i>Текущий минимум: {settings['min_amount']:,} руб/год</i>\n"
        f"⏰ <i>Автозапуск: каждый день в 09:00</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    settings = load_settings()
    text = (
        "⚙️ <b>Текущие настройки</b>\n\n"
        f"💰 Минимальная сумма: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"📅 Минимальный срок подачи: <b>{settings['min_days']} дней</b>\n\n"
        "Источники мониторинга:\n"
        "• minobrnauki.gov.ru\n"
        "• rscf.ru (РНФ)\n"
        "• fasie.ru (Фонд Бортника)\n"
        "• grant.gov.ru\n"
        "• scientificrussia.ru"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_setamount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    if not context.args:
        await update.message.reply_text(
            "⚠️ Укажите сумму. Пример: /setamount 10000000"
        )
        return
    try:
        amount = int(context.args[0].replace(" ", "").replace(",", ""))
        if amount < 1_000_000:
            await update.message.reply_text("⚠️ Минимально допустимое значение — 1 000 000 руб.")
            return
        settings = load_settings()
        settings["min_amount"] = amount
        save_settings(settings)
        await update.message.reply_text(
            f"✅ Минимальная сумма обновлена: <b>{amount:,} руб/год</b>",
            parse_mode="HTML",
        )
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Укажите число, например: /setamount 10000000")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    await update.message.reply_text("⏳ <b>Запускаю парсер...</b>", parse_mode="HTML")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(None, lambda: run_parser(settings))
        if count > 0:
            await update.message.reply_text(
                f"✅ <b>Готово!</b> Отправлено новых грантов: {count}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "✅ <b>Готово!</b> Новых грантов не найдено.",
                parse_mode="HTML",
            )
    except Exception as e:
        logger.exception("Ошибка при запуске парсера")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)[:200]}",
            parse_mode="HTML",
        )


async def job_daily(context: ContextTypes.DEFAULT_TYPE):
    """Автоматический ежедневный запуск в 09:00."""
    logger.info("⏰ Автозапуск парсера по расписанию")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(None, lambda: run_parser(settings))
        logger.info(f"✅ Автозапуск завершён. Новых грантов: {count}")
    except Exception as e:
        logger.exception("Ошибка автозапуска")


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if ADMIN_ID == 0:
        logger.error("ADMIN_ID не задан!")
        sys.exit(1)

    logger.info("🚀 Бот запускается...")

    app = Application.builder().token(TOKEN).build()

    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=1)
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("setamount", cmd_setamount))

    # Ежедневный запуск в 09:00 UTC (12:00 МСК)
    app.job_queue.run_daily(job_daily, time=dtime(hour=6, minute=0))

    logger.info("✅ Бот запущен, ожидаю команды...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
