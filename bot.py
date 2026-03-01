#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот для мониторинга грантов МГТУ им. Баумана
- Гранты публикуются в канал
- Команды управления работают в личке
"""
import os
import sys
import logging
import asyncio
from datetime import time as dtime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import run_parser, load_settings, save_settings

# ─── Настройки из переменных окружения ────────────────────────────────────────
TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = (os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())
except ValueError:
    ADMIN_ID = 0

# ─── Логирование — скрываем URL с токеном ─────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
    force=True,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ADMIN_ID


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start от user_id={update.effective_user.id}")
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    settings = load_settings()
    channel_info = f"📢 Канал: <code>{CHANNEL_ID}</code>" if CHANNEL_ID else "⚠️ TELEGRAM_CHANNEL_ID не задан!"

    text = (
        "👋 <b>Бот мониторинга грантов МГТУ</b>\n\n"
        "Команды:\n"
        "/check — запустить парсер прямо сейчас\n"
        "/status — текущие настройки\n"
        "/setamount 10000000 — изменить минимальную сумму\n\n"
        f"💰 Минимум: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"{channel_info}\n"
        "⏰ Автозапуск: каждый день в 12:00 МСК"
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
        f"📅 Мин. срок подачи: <b>{settings['min_days']} дней</b>\n"
        f"📢 Канал для грантов: <code>{CHANNEL_ID or 'не задан'}</code>\n\n"
        "<b>Источники мониторинга:</b>\n"
        "• Минобрнауки (minobrnauki.gov.ru)\n"
        "• РНФ (rscf.ru)\n"
        "• Фонд Бортника (fasie.ru)\n"
        "• Научная Россия (scientificrussia.ru)\n"
        "• Гранты.ру (grants.ru)"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_setamount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    if not context.args:
        settings = load_settings()
        await update.message.reply_text(
            f"Текущий минимум: <b>{settings['min_amount']:,} руб</b>\n\n"
            "Чтобы изменить:\n/setamount 10000000",
            parse_mode="HTML",
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
            f"✅ Готово! Новый минимум: <b>{amount:,} руб/год</b>",
            parse_mode="HTML",
        )
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Пример: /setamount 10000000")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    if not CHANNEL_ID:
        await update.message.reply_text("❌ Не задана переменная TELEGRAM_CHANNEL_ID в BotHost!")
        return

    await update.message.reply_text("⏳ Запускаю парсер...")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None, lambda: run_parser(settings, CHANNEL_ID)
        )
        if count > 0:
            await update.message.reply_text(
                f"✅ Готово! Отправлено в канал новых грантов: <b>{count}</b>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text("✅ Готово! Новых грантов не найдено.")
    except Exception as e:
        logger.exception("Ошибка при запуске парсера")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")


async def job_daily(context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_ID:
        logger.warning("TELEGRAM_CHANNEL_ID не задан — автозапуск пропущен")
        return
    logger.info("⏰ Автозапуск парсера по расписанию")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None, lambda: run_parser(settings, CHANNEL_ID)
        )
        logger.info(f"✅ Автозапуск завершён. Новых грантов: {count}")
    except Exception as e:
        logger.exception("Ошибка автозапуска")


def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if ADMIN_ID == 0:
        logger.error("❌ ADMIN_ID не задан!")
        sys.exit(1)
    if not CHANNEL_ID:
        logger.warning("⚠️ TELEGRAM_CHANNEL_ID не задан!")

    logger.info("🚀 Бот запускается...")
    logger.info(f"   ADMIN_ID    = [{ADMIN_ID}] (тип: {type(ADMIN_ID).__name__})")
    logger.info(f"   CHANNEL_ID  = [{CHANNEL_ID}]")
    logger.info(f"   TOKEN OK    = {bool(TOKEN)}")

    # Удаляем webhook если был установлен (мешает polling)
    import requests as req
    try:
        r = req.get(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        logger.info(f"   deleteWebhook: {r.json().get('description', 'ok')}")
    except Exception as e:
        logger.warning(f"   deleteWebhook не удался: {e}")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("setamount", cmd_setamount))

    # Ловим ВСЕ сообщения для диагностики
    async def log_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else "??"
        txt = update.message.text if update.message else str(update)
        logger.info(f"📨 Сообщение от {uid}: {txt}")
        if update.effective_user and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(f"Твой ID: {uid}. ADMIN_ID={ADMIN_ID}")
    app.add_handler(MessageHandler(filters.ALL, log_all), group=1)

    # Каждый день в 09:00 UTC = 12:00 МСК
    app.job_queue.run_daily(job_daily, time=dtime(hour=9, minute=0))

    logger.info("✅ Polling запущен, жду команды...")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
