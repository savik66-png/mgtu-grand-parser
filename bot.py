#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот для мониторинга грантов МГТУ им. Баумана
"""
import os
import sys
import logging
import asyncio
from datetime import time as dtime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import run_parser, load_settings, save_settings

# ─── Переменные окружения ──────────────────────────────────────────────────────
TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = (os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())
except ValueError:
    ADMIN_ID = 0

# ─── Логирование ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
    force=True,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ─── Клавиатура ───────────────────────────────────────────────────────────────
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔍 Запустить парсер"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("💰 Изменить минимум"),  KeyboardButton("ℹ️ Помощь")],
    ],
    resize_keyboard=True,
    persistent=True,
)


def is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ADMIN_ID


async def send_welcome(update: Update, settings: dict):
    channel_info = f"📢 <code>{CHANNEL_ID}</code>" if CHANNEL_ID else "⚠️ канал не задан"
    text = (
        "👋 <b>Бот мониторинга грантов МГТУ им. Баумана</b>\n\n"
        "Я слежу за грантами и конкурсами в российских источниках "
        "и отправляю подходящие в канал.\n\n"
        "<b>Источники:</b> Минобрнауки, РНФ, Фонд Бортника, Гранты.ру\n\n"
        f"💰 Минимум: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"📢 Канал: {channel_info}\n"
        f"⏰ Автозапуск: каждый день в 12:00 МСК\n\n"
        "Используй кнопки ниже 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)


# ─── Команды и кнопки ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Старт от user_id={update.effective_user.id}")
    if not is_admin(update):
        await update.message.reply_text(
            f"❌ Доступ запрещён.\nВаш ID: <code>{update.effective_user.id}</code>",
            parse_mode="HTML"
        )
        return
    settings = load_settings()
    await send_welcome(update, settings)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not CHANNEL_ID:
        await update.message.reply_text("❌ Не задана переменная TELEGRAM_CHANNEL_ID в BotHost!")
        return
    await update.message.reply_text("⏳ Запускаю парсер...", reply_markup=MAIN_KEYBOARD)
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
                reply_markup=MAIN_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "✅ Готово! Новых грантов не найдено.",
                reply_markup=MAIN_KEYBOARD,
            )
    except Exception as e:
        logger.exception("Ошибка парсера")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}", reply_markup=MAIN_KEYBOARD)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    settings = load_settings()
    text = (
        "⚙️ <b>Текущие настройки</b>\n\n"
        f"💰 Минимальная сумма: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"📅 Мин. срок подачи: <b>{settings['min_days']} дней</b>\n"
        f"📢 Канал: <code>{CHANNEL_ID or 'не задан'}</code>\n\n"
        "<b>Источники:</b>\n"
        "• Минобрнауки\n• РНФ\n• Фонд Бортника\n• Научная Россия\n• Гранты.ру"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)


async def cmd_setamount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        settings = load_settings()
        await update.message.reply_text(
            f"Текущий минимум: <b>{settings['min_amount']:,} руб</b>\n\n"
            "Введите новую сумму командой:\n<code>/setamount 10000000</code>",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    try:
        amount = int(context.args[0].replace(",", "").replace(" ", ""))
        if amount < 1_000_000:
            await update.message.reply_text("⚠️ Минимум 1 000 000 руб.")
            return
        settings = load_settings()
        settings["min_amount"] = amount
        save_settings(settings)
        await update.message.reply_text(
            f"✅ Новый минимум: <b>{amount:,} руб/год</b>",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD,
        )
    except ValueError:
        await update.message.reply_text("❌ Пример: /setamount 10000000", reply_markup=MAIN_KEYBOARD)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок клавиатуры."""
    if not is_admin(update):
        await update.message.reply_text(
            f"❌ Доступ запрещён. Ваш ID: <code>{update.effective_user.id}</code>",
            parse_mode="HTML"
        )
        return

    text = update.message.text

    if text == "🔍 Запустить парсер":
        await cmd_check(update, context)

    elif text == "⚙️ Настройки":
        await cmd_status(update, context)

    elif text == "💰 Изменить минимум":
        settings = load_settings()
        await update.message.reply_text(
            f"Текущий минимум: <b>{settings['min_amount']:,} руб/год</b>\n\n"
            "Отправьте команду с новой суммой:\n"
            "<code>/setamount 10000000</code>",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD,
        )

    elif text == "ℹ️ Помощь":
        await update.message.reply_text(
            "📖 <b>Как пользоваться ботом</b>\n\n"
            "🔍 <b>Запустить парсер</b> — найти новые гранты прямо сейчас\n"
            "⚙️ <b>Настройки</b> — показать текущие параметры\n"
            "💰 <b>Изменить минимум</b> — изменить мин. сумму гранта\n\n"
            "<b>Команды:</b>\n"
            "/start — главное меню\n"
            "/check — запустить парсер\n"
            "/setamount 10000000 — изменить минимум\n\n"
            "⏰ Парсер запускается автоматически каждый день в 12:00 МСК",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD,
        )

    else:
        # Любой другой текст — показываем меню
        settings = load_settings()
        await send_welcome(update, settings)


async def job_daily(context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_ID:
        logger.warning("TELEGRAM_CHANNEL_ID не задан — автозапуск пропущен")
        return
    logger.info("⏰ Автозапуск парсера")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None, lambda: run_parser(settings, CHANNEL_ID)
        )
        logger.info(f"✅ Автозапуск завершён. Грантов: {count}")
    except Exception as e:
        logger.exception("Ошибка автозапуска")


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if ADMIN_ID == 0:
        logger.error("❌ ADMIN_ID не задан!")
        sys.exit(1)

    logger.info("🚀 Бот запускается...")
    logger.info(f"   ADMIN_ID   = [{ADMIN_ID}]")
    logger.info(f"   CHANNEL_ID = [{CHANNEL_ID}]")

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
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("setamount", cmd_setamount))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    app.job_queue.run_daily(job_daily, time=dtime(hour=9, minute=0))

    logger.info("✅ Polling запущен...")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
