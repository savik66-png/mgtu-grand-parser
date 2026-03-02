#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — Telegram бот для управления парсером грантов МГТУ.
Команды в личке, гранты идут в канал.
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
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, ADMIN_ID
from storage import load_settings, save_settings, reset_sent_grants
from parser_core import run_parser

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
KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔍 Запустить парсер"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("💰 Изменить минимум"), KeyboardButton("🔄 Сбросить историю")],
        [KeyboardButton("ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)


def is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ADMIN_ID


async def send_welcome(update: Update):
    settings = load_settings()
    channel = f"<code>{TELEGRAM_CHANNEL_ID}</code>" if TELEGRAM_CHANNEL_ID else "⚠️ не задан"
    text = (
        "👋 <b>Бот мониторинга грантов МГТУ им. Баумана</b>\n\n"
        "Слежу за грантами в российских источниках и отправляю подходящие в канал.\n\n"
        "<b>Источники:</b> Минобрнауки, РНФ, Фонд Бортника, Приоритет-2030,\n"
        "Telegram-каналы ведомств, региональные фонды\n\n"
        f"💰 Порог: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"📢 Канал: {channel}\n"
        "⏰ Автозапуск: каждый день в 12:00 МСК\n\n"
        "Используй кнопки ниже 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=KEYBOARD)


# ─── Команды ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Старт от user_id={update.effective_user.id}")
    if not is_admin(update):
        await update.message.reply_text(
            f"❌ Доступ запрещён.\nВаш ID: <code>{update.effective_user.id}</code>",
            parse_mode="HTML"
        )
        return
    await send_welcome(update)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not TELEGRAM_CHANNEL_ID:
        await update.message.reply_text("❌ Не задана переменная TELEGRAM_CHANNEL_ID!")
        return

    await update.message.reply_text("⏳ Запускаю парсер...", reply_markup=KEYBOARD)
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None, lambda: run_parser(settings, TELEGRAM_CHANNEL_ID)
        )
        if count > 0:
            await update.message.reply_text(
                f"✅ Готово! Отправлено в канал: <b>{count} грантов</b>",
                parse_mode="HTML", reply_markup=KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "✅ Готово! Новых грантов не найдено.",
                reply_markup=KEYBOARD,
            )
    except Exception as e:
        logger.exception("Ошибка парсера")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:300]}", reply_markup=KEYBOARD)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    settings = load_settings()
    text = (
        "⚙️ <b>Текущие настройки</b>\n\n"
        f"💰 Минимальная сумма: <b>{settings['min_amount']:,} руб/год</b>\n"
        f"📅 Мин. срок подачи: <b>{settings['min_days']} дней</b>\n"
        f"📢 Канал: <code>{TELEGRAM_CHANNEL_ID or 'не задан'}</code>\n\n"
        "<b>Источники:</b>\n"
        "• Минобрнауки, РНФ, Фонд Бортника\n"
        "• Приоритет-2030\n"
        "• Telegram-каналы ведомств\n"
        "• Сколково, РВК\n"
        "• Гранты.ру, Научная Россия"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=KEYBOARD)


async def cmd_setamount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        settings = load_settings()
        await update.message.reply_text(
            f"Текущий порог: <b>{settings['min_amount']:,} руб</b>\n\n"
            "Введите новую сумму:\n<code>/setamount 10000000</code>",
            parse_mode="HTML", reply_markup=KEYBOARD,
        )
        return
    try:
        amount = int(context.args[0].replace(",", "").replace(" ", ""))
        if amount < 1_000_000:
            await update.message.reply_text("⚠️ Минимально: 1 000 000 руб.")
            return
        settings = load_settings()
        settings["min_amount"] = amount
        save_settings(settings)
        await update.message.reply_text(
            f"✅ Новый порог: <b>{amount:,} руб/год</b>",
            parse_mode="HTML", reply_markup=KEYBOARD,
        )
    except ValueError:
        await update.message.reply_text("❌ Пример: /setamount 10000000")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    ok = reset_sent_grants()
    if ok:
        await update.message.reply_text(
            "✅ История очищена!\nТеперь нажми 🔍 Запустить парсер — придут все гранты заново.",
            reply_markup=KEYBOARD,
        )
    else:
        await update.message.reply_text("ℹ️ История уже пуста.", reply_markup=KEYBOARD)


# ─── Обработчик кнопок ────────────────────────────────────────────────────────

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"Текущий порог: <b>{settings['min_amount']:,} руб/год</b>\n\n"
            "Отправьте команду с новой суммой:\n"
            "<code>/setamount 10000000</code>",
            parse_mode="HTML", reply_markup=KEYBOARD,
        )
    elif text == "🔄 Сбросить историю":
        await cmd_reset(update, context)
    elif text == "ℹ️ Помощь":
        await update.message.reply_text(
            "📖 <b>Как пользоваться ботом</b>\n\n"
            "🔍 <b>Запустить парсер</b> — найти новые гранты прямо сейчас\n"
            "⚙️ <b>Настройки</b> — текущие параметры и источники\n"
            "💰 <b>Изменить минимум</b> — изменить мин. сумму гранта\n"
            "🔄 <b>Сбросить историю</b> — получить все гранты заново\n\n"
            "<b>Команды:</b>\n"
            "/start — главное меню\n"
            "/check — запустить парсер\n"
            "/setamount 10000000 — изменить порог суммы\n"
            "/reset — сбросить историю\n\n"
            "⏰ Автозапуск каждый день в 12:00 МСК",
            parse_mode="HTML", reply_markup=KEYBOARD,
        )
    else:
        await send_welcome(update)


# ─── Автозапуск по расписанию ─────────────────────────────────────────────────

async def job_daily(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHANNEL_ID:
        logger.warning("TELEGRAM_CHANNEL_ID не задан — автозапуск пропущен")
        return
    logger.info("⏰ Автозапуск парсера по расписанию")
    try:
        settings = load_settings()
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None, lambda: run_parser(settings, TELEGRAM_CHANNEL_ID)
        )
        logger.info(f"✅ Автозапуск завершён. Грантов: {count}")
    except Exception as e:
        logger.exception("Ошибка автозапуска")


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if ADMIN_ID == 0:
        logger.error("❌ ADMIN_ID не задан!")
        sys.exit(1)

    logger.info("🚀 Бот запускается...")
    logger.info(f"   ADMIN_ID   = [{ADMIN_ID}]")
    logger.info(f"   CHANNEL_ID = [{TELEGRAM_CHANNEL_ID or 'не задан'}]")

    # Удаляем webhook
    import requests as req
    try:
        r = req.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
            "?drop_pending_updates=true",
            timeout=10
        )
        logger.info(f"   deleteWebhook: {r.json().get('description','ok')}")
    except Exception as e:
        logger.warning(f"   deleteWebhook: {e}")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("setamount", cmd_setamount))
    app.add_handler(CommandHandler("reset",     cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    # Каждый день в 09:00 UTC = 12:00 МСК
    app.job_queue.run_daily(job_daily, time=dtime(hour=9, minute=0))

    logger.info("✅ Polling запущен...")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
