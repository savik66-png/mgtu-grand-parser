#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер грантов для МГТУ им. Баумана
Источники: Минобрнауки, РНФ, Фонд Бортника, grant.gov.ru, Научная Россия
"""
import os
import re
import json
import time
import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(SCRIPT_DIR, "sent_grants.json")
SETTINGS_FILE    = os.path.join(SCRIPT_DIR, "settings.json")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── Настройки ────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    defaults = {"min_amount": 5_000_000, "min_days": 14}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
    except Exception:
        pass
    return defaults


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")


# ─── Тематические направления МГТУ ────────────────────────────────────────────
DIRECTIONS = {
    "Беспилотные системы": [
        "беспилотн", "автономн транспорт", "uav", "бла", "дрон",
    ],
    "Суперкомпьютеры и ИИ": [
        "суперкомпьют", "сверхпроизводительн", "нейросет", "искусственный интеллект",
        "машинное обучение", "big data", "больших данных",
    ],
    "Интеллектуальные производства": [
        "индустрия 4", "умное производство", "роботизац", "автоматизац производ",
        "цифровое производств",
    ],
    "Персонализированная медицина": [
        "персонализированн медицин", "точная медицин", "диагностик", "биосенсор",
        "медицинские технологии",
    ],
    "Машиностроение и материалы": [
        "машиностроен", "новые материалы", "композитн", "металлообработк",
        "аддитивн технологи",
    ],
    "Энергомашиностроение": [
        "энергомашиностроен", "турбин", "энергетическое оборудован",
        "возобновляемая энергетик",
    ],
    "Биомедицина и биотехнологии": [
        "биомедицин", "биотехнологи", "геномик", "протеомик", "фармацевтическ",
    ],
    "Химические технологии": [
        "химическ технологи", "нанотехнологи", "наноматериал", "химическ синтез",
    ],
    "Цифровые платформы": [
        "цифровая платформ", "информационная систем", "программное обеспечен",
        "кибербезопасност",
    ],
    "Космос и авиация": [
        "космическ", "авиационн", "роскосмос", "спутник",
    ],
    "Оборонные технологии": [
        "оборонн", "двойного назначен", "военн", "опк",
    ],
    "Транспорт и связь": [
        "транспортн систем", "умный город", "телекоммуникац",
    ],
    "Экология": [
        "экологи", "природопользован", "климат", "зеленые технологи",
    ],
    "Инновации и венчур": [
        "инновацион", "стартап", "технологическ трансфер", "венчурн",
    ],
}

RSS_SOURCES = [
    {"name": "Минобрнауки",        "url": "https://minobrnauki.gov.ru/ru/press-center/news/feed/"},
    {"name": "РНФ",                "url": "https://rscf.ru/ru/news/feed/"},
    {"name": "Фонд Бортника",      "url": "https://fasie.ru/rss/"},
    {"name": "Научная Россия",     "url": "https://scientificrussia.ru/news/rss"},
    {"name": "Гранты.ру",          "url": "https://www.grants.ru/rss/"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def load_sent_grants() -> set:
    try:
        if os.path.exists(SENT_GRANTS_FILE):
            with open(SENT_GRANTS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def save_sent_grants(sent: set):
    try:
        with open(SENT_GRANTS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(sent), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения sent_grants: {e}")


def grant_hash(title: str, source: str) -> str:
    text = f"{title.strip().lower()}|{source}"
    return hashlib.md5(text.encode()).hexdigest()


def extract_amount(text: str) -> Optional[int]:
    text = text.lower()
    patterns = [
        (r"(\d[\d\s]*)\s*млрд", 1_000_000_000),
        (r"(\d[\d\s]*)\s*млн",  1_000_000),
    ]
    for pattern, multiplier in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                num = int(re.sub(r"\s", "", m))
                return num * multiplier
            except ValueError:
                continue
    return None


def detect_directions(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for direction, keywords in DIRECTIONS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(direction)
                break
    return found if found else ["Общие научные исследования"]


def is_grant_related(text: str) -> bool:
    keywords = [
        "грант", "конкурс", "финансирован", "субсидия", "заявк",
        "отбор", "программа поддержк", "научный проект", "нир ", "ниокр",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def fetch_rss(source: dict) -> List[Dict[str, Any]]:
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"

        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        channel = root.find("channel")
        entries = channel.findall("item") if channel is not None else root.findall("atom:entry", ns)

        for entry in entries:
            def get(tag, ns_tag=None):
                el = entry.find(tag)
                if el is None and ns_tag:
                    el = entry.find(ns_tag, ns)
                return el.text.strip() if el is not None and el.text else ""

            title    = get("title", "atom:title")
            link_el  = entry.find("link")
            link     = (link_el.text or link_el.get("href", "") if link_el is not None else "").strip()
            desc     = get("description") or get("atom:summary", "atom:summary")
            pub_date = get("pubDate") or get("atom:published", "atom:published")

            items.append({
                "title":     title,
                "link":      link,
                "desc":      desc[:500] if desc else "",
                "pub_date":  pub_date,
                "source":    source["name"],
                "full_text": f"{title} {desc}",
            })

        logger.info(f"  {source['name']}: получено {len(items)} записей")
    except requests.exceptions.Timeout:
        logger.warning(f"  {source['name']}: таймаут")
    except requests.exceptions.ConnectionError:
        logger.warning(f"  {source['name']}: ошибка соединения")
    except ET.ParseError as e:
        logger.warning(f"  {source['name']}: ошибка XML — {e}")
    except Exception as e:
        logger.warning(f"  {source['name']}: ошибка — {e}")
    return items


def filter_grants(items: List[Dict], settings: dict) -> List[Dict]:
    min_amount = settings.get("min_amount", 5_000_000)
    result = []
    for item in items:
        if not is_grant_related(item["full_text"]):
            continue
        amount = extract_amount(item["full_text"])
        # Если сумма найдена и она меньше порога — пропускаем
        if amount is not None and amount < min_amount:
            continue
        item["directions"]       = detect_directions(item["full_text"])
        item["amount_detected"]  = amount
        result.append(item)
    return result


def send_telegram(text: str, chat_id: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.error("Не заданы TELEGRAM_BOT_TOKEN или chat_id")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

    for part in parts:
        try:
            resp = requests.post(
                url,
                data={
                    "chat_id":                  chat_id,
                    "text":                     part,
                    "parse_mode":               "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"Telegram API ошибка {resp.status_code}: {resp.text[:200]}")
                return False
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False
    return True


def format_grant(i: int, item: Dict) -> str:
    directions_str = ", ".join(item.get("directions", []))
    amount_str = ""
    if item.get("amount_detected"):
        amount_str = f"\n💰 <b>Сумма (в тексте):</b> от {item['amount_detected']:,} руб"

    pub = item.get("pub_date", "")[:25]
    pub_str = f"\n📅 <b>Опубликовано:</b> {pub}" if pub else ""

    desc = item.get("desc", "")
    if desc and len(desc) > 250:
        desc = desc[:250] + "..."
    desc_str = f"\n📝 {desc}" if desc else ""

    link = item.get("link", "")
    link_str = f'\n🔗 <a href="{link}">Подробнее →</a>' if link else ""

    return (
        f"<b>#{i}. {item['title']}</b>\n"
        f"🏛 <b>Источник:</b> {item['source']}"
        f"{amount_str}"
        f"\n🔬 <b>Направления:</b> {directions_str}"
        f"{pub_str}"
        f"{desc_str}"
        f"{link_str}\n"
        f"{'━' * 22}\n\n"
    )


def run_parser(settings: dict = None, channel_id: str = None) -> int:
    """
    Запускает парсер и отправляет новые гранты в указанный канал/чат.
    Возвращает количество отправленных грантов.
    """
    if settings is None:
        settings = load_settings()

    # chat_id для отправки: либо аргумент, либо переменная окружения
    target_chat = channel_id or os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID", "")

    logger.info("─── Запуск парсера ───────────────────────────────")
    logger.info(f"Минимальная сумма: {settings['min_amount']:,} руб/год")
    logger.info(f"Отправка в: {target_chat}")

    # Сбор данных
    all_items = []
    for source in RSS_SOURCES:
        logger.info(f"Парсинг: {source['name']} ...")
        all_items.extend(fetch_rss(source))

    logger.info(f"Всего записей: {len(all_items)}")

    # Фильтрация
    relevant = filter_grants(all_items, settings)
    logger.info(f"После фильтрации: {len(relevant)}")

    # Убираем уже отправленные
    sent = load_sent_grants()
    new_grants = []
    for item in relevant:
        h = grant_hash(item["title"], item["source"])
        if h not in sent:
            new_grants.append(item)
            sent.add(h)

    logger.info(f"Новых для отправки: {len(new_grants)}")

    if not new_grants:
        return 0

    header = (
        "🎓 <b>МОНИТОРИНГ ГРАНТОВ — МГТУ им. Баумана</b>\n"
        f"📅 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"🔍 <i>Новых записей: {len(new_grants)}</i>\n"
        f"💰 <i>Порог: от {settings['min_amount']:,} руб/год</i>\n\n"
    )
    body   = "".join(format_grant(i, item) for i, item in enumerate(new_grants, 1))
    footer = "🤖 <i>Автоматический мониторинг грантов МГТУ</i>"

    success = send_telegram(header + body + footer, target_chat)
    if success:
        save_sent_grants(sent)
        logger.info(f"✅ Отправлено {len(new_grants)} грантов")
    else:
        logger.error("❌ Ошибка отправки в Telegram")

    return len(new_grants) if success else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = run_parser()
    print(f"Готово. Отправлено: {count}")
