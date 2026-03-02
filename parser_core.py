#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parser_core.py — ядро парсера. Оркестрирует все модули.
Вызывается из bot.py и может запускаться самостоятельно.
"""
import logging
from datetime import datetime
from typing import List, Dict

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
from sources import get_all_grants
from mgtu_parser import process_grants
from storage import load_settings, filter_new_grants, save_html_report

logger = logging.getLogger(__name__)


# ─── Форматирование сообщения для Telegram ────────────────────────────────────

def format_telegram_message(grants: List[Dict], settings: dict) -> str:
    header = (
        "🎯 <b>ГРАНТЫ ДЛЯ МГТУ ИМ. БАУМАНА</b>\n"
        f"📅 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"🔍 <i>Найдено новых: {len(grants)}</i>  "
        f"💰 <i>Порог: от {settings['min_amount']:,} руб/год</i>\n\n"
    )

    body = ""
    for i, g in enumerate(grants, 1):
        stars = "⭐" * g.get("rating", 3)
        directions_str = ", ".join(g.get("directions", []))
        desc = g.get("desc", "")
        if len(desc) > 250:
            desc = desc[:250] + "..."

        link = g.get("link", g.get("details_url", ""))

        body += f"<b>#{i} {g['title']}</b> {stars}\n"
        body += f"🏛 <b>Источник:</b> {g['source']}\n"

        if g.get("amount") and g["amount"] != "Уточняется":
            body += f"💰 <b>Финансирование:</b> {g['amount']}\n"

        body += f"🔬 <b>Направления МГТУ:</b> {directions_str}\n"

        if g.get("pub_date"):
            body += f"📅 <b>Опубликовано:</b> {g['pub_date']}\n"

        if desc:
            body += f"📝 {desc}\n"

        if link:
            body += f'🔗 <a href="{link}">Подробнее →</a>\n'

        body += "━" * 22 + "\n\n"

    footer = "🤖 <i>Автоматический мониторинг грантов МГТУ</i>"
    return header + body + footer


# ─── Отправка в Telegram ──────────────────────────────────────────────────────

def send_telegram(text: str, chat_id: str, token: str = None) -> bool:
    tok = token or TELEGRAM_BOT_TOKEN
    if not tok or not chat_id:
        logger.error("Не заданы токен или chat_id")
        return False

    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    max_len = 4000
    parts = []

    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text[:max_len].rfind("\n")
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip()

    import time
    for part in parts:
        try:
            r = requests.post(url, data={
                "chat_id":                  chat_id,
                "text":                     part,
                "parse_mode":               "HTML",
                "disable_web_page_preview": True,
            }, timeout=30)
            if r.status_code != 200:
                logger.error(f"Telegram API: {r.text[:300]}")
                return False
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False
    return True


# ─── Главная функция ──────────────────────────────────────────────────────────

def run_parser(settings: dict = None, channel_id: str = None) -> int:
    """
    Запускает полный цикл парсинга.
    Возвращает количество отправленных грантов.
    """
    if settings is None:
        settings = load_settings()

    target = channel_id or TELEGRAM_CHANNEL_ID
    if not target:
        logger.error("Не задан TELEGRAM_CHANNEL_ID")
        return 0

    logger.info("=" * 50)
    logger.info(f"Старт парсера | Порог: {settings['min_amount']:,} руб")
    logger.info(f"Канал: {target}")

    # 1. Сбор из источников
    raw = get_all_grants()

    # 2. Фильтрация и обогащение
    processed = process_grants(raw, settings)

    # 3. Только новые (не отправлявшиеся раньше)
    new_grants = filter_new_grants(processed)
    logger.info(f"Новых для отправки: {len(new_grants)}")

    if not new_grants:
        logger.info("Новых грантов нет")
        return 0

    # 4. Отправка в Telegram
    message = format_telegram_message(new_grants, settings)
    success = send_telegram(message, target)

    if success:
        # 5. Сохраняем HTML отчёт
        save_html_report(new_grants, settings)
        logger.info(f"✅ Отправлено {len(new_grants)} грантов в {target}")
        return len(new_grants)
    else:
        logger.error("❌ Ошибка отправки в Telegram")
        return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    )
    count = run_parser()
    print(f"\n✅ Готово. Отправлено грантов: {count}")
