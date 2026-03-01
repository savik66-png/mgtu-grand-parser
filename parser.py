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
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", os.getenv("ADMIN_ID", ""))

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
        "биомедицин", "биотехнологи", "геномик", "протеомик",
        "фармацевтическ",
    ],
    "Химические технологии": [
        "химическ технологи", "нанотехнологи", "наноматериал",
        "химическ синтез",
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
        "транспортн систем", "умный город", "телекоммуникац", "связ",
    ],
    "Экология и природопользование": [
        "экологи", "природопользован", "климат", "зеленые технологи",
    ],
    "Инновации и венчур": [
        "инновацион", "стартап", "технологическ трансфер", "венчурн",
    ],
}

# ─── RSS-источники ─────────────────────────────────────────────────────────────
RSS_SOURCES = [
    {
        "name": "Минобрнауки",
        "url": "https://minobrnauki.gov.ru/ru/press-center/news/feed/",
        "timeout": 15,
    },
    {
        "name": "РНФ",
        "url": "https://rscf.ru/ru/news/feed/",
        "timeout": 15,
    },
    {
        "name": "Фонд Бортника (FASIE)",
        "url": "https://fasie.ru/rss/",
        "timeout": 15,
    },
    {
        "name": "Научная Россия",
        "url": "https://scientificrussia.ru/news/rss",
        "timeout": 15,
    },
    {
        "name": "Гранты.ру",
        "url": "https://www.grants.ru/rss/",
        "timeout": 15,
    },
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
    """Извлекает минимальную сумму гранта в рублях из текста."""
    text = text.lower()
    # Ищем паттерны типа "15 млн", "5 000 000", "до 30 млн", "от 10 млн"
    patterns = [
        r"(\d[\d\s]*)\s*млрд",   # миллиарды
        r"(\d[\d\s]*)\s*млн",    # миллионы
        r"(\d[\d\s]{4,})\s*руб", # большие числа в рублях
    ]
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                num = int(re.sub(r"\s", "", m))
                if i == 0:
                    return num * 1_000_000_000
                elif i == 1:
                    return num * 1_000_000
                else:
                    return num
            except ValueError:
                continue
    return None


def detect_directions(text: str) -> List[str]:
    """Определяет тематические направления гранта."""
    text_lower = text.lower()
    found = []
    for direction, keywords in DIRECTIONS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(direction)
                break
    return found if found else ["Общие научные исследования"]


def is_grant_related(text: str) -> bool:
    """Проверяет, относится ли новость к грантам/конкурсам."""
    keywords = [
        "грант", "конкурс", "финансирован", "субсидия", "заявк",
        "отбор", "программа поддержк", "научный проект",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def fetch_rss(source: dict) -> List[Dict[str, Any]]:
    """Получает и парсит RSS-ленту."""
    items = []
    try:
        resp = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=source.get("timeout", 15),
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"

        root = ET.fromstring(resp.content)

        # Поддержка обычного RSS и Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        channel = root.find("channel")
        if channel is not None:
            entries = channel.findall("item")
        else:
            entries = root.findall("atom:entry", ns)

        for entry in entries:
            def get(tag, ns_tag=None):
                el = entry.find(tag)
                if el is None and ns_tag:
                    el = entry.find(ns_tag, ns)
                return el.text.strip() if el is not None and el.text else ""

            title   = get("title", "atom:title")
            link_el = entry.find("link")
            if link_el is not None:
                link = link_el.text or link_el.get("href", "")
            else:
                link = ""
            link = link.strip()

            desc    = get("description") or get("atom:summary", "atom:summary")
            pub_date = get("pubDate") or get("atom:published", "atom:published")

            full_text = f"{title} {desc}"
            items.append({
                "title":     title,
                "link":      link,
                "desc":      desc[:500] if desc else "",
                "pub_date":  pub_date,
                "source":    source["name"],
                "full_text": full_text,
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
    """Фильтрует записи по критериям."""
    min_amount = settings.get("min_amount", 5_000_000)
    result = []

    for item in items:
        if not is_grant_related(item["full_text"]):
            continue

        amount = extract_amount(item["full_text"])
        passes_amount = (amount is None) or (amount >= min_amount)
        # Если сумма не найдена, включаем — пусть лучше лишнее, чем пропустить
        if not passes_amount:
            continue

        directions = detect_directions(item["full_text"])
        item["directions"] = directions
        item["amount_detected"] = amount
        result.append(item)

    return result


def send_telegram(text: str) -> bool:
    """Отправляет сообщение в Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
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
                    "chat_id":    TELEGRAM_CHAT_ID,
                    "text":       part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"Telegram API ошибка: {resp.text[:200]}")
                return False
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False
    return True


def format_grant(i: int, item: Dict) -> str:
    """Форматирует одну запись гранта для Telegram."""
    directions_str = ", ".join(item.get("directions", []))
    amount_str = ""
    if item.get("amount_detected"):
        amount_str = f"\n💰 <b>Сумма (в тексте):</b> от {item['amount_detected']:,} руб"

    pub = item.get("pub_date", "")
    if pub:
        pub = f"\n📅 <b>Дата публикации:</b> {pub[:25]}"

    desc = item.get("desc", "")
    if desc and len(desc) > 200:
        desc = desc[:200] + "..."
    desc_str = f"\n📝 {desc}" if desc else ""

    link = item.get("link", "")
    link_str = f"\n🔗 <a href=\"{link}\">Подробнее</a>" if link else ""

    return (
        f"<b>#{i}. {item['title']}</b>\n"
        f"🏛 <b>Источник:</b> {item['source']}"
        f"{amount_str}"
        f"\n🔬 <b>Направления:</b> {directions_str}"
        f"{pub}"
        f"{desc_str}"
        f"{link_str}\n"
        f"{'━' * 22}\n\n"
    )


def run_parser(settings: dict = None) -> int:
    """
    Основная функция парсера.
    Возвращает количество отправленных новых грантов.
    """
    if settings is None:
        settings = {"min_amount": 5_000_000, "min_days": 14}

    logger.info("─── Запуск парсера ───────────────────────────────")
    logger.info(f"Минимальная сумма: {settings['min_amount']:,} руб/год")

    # Сбор данных из всех источников
    all_items = []
    for source in RSS_SOURCES:
        logger.info(f"Парсинг: {source['name']} ...")
        items = fetch_rss(source)
        all_items.extend(items)

    logger.info(f"Всего записей получено: {len(all_items)}")

    # Фильтрация
    relevant = filter_grants(all_items, settings)
    logger.info(f"После фильтрации по критериям: {len(relevant)}")

    # Убираем уже отправленные
    sent = load_sent_grants()
    new_grants = []
    for item in relevant:
        h = grant_hash(item["title"], item["source"])
        if h not in sent:
            new_grants.append(item)
            sent.add(h)

    logger.info(f"Новых грантов для отправки: {len(new_grants)}")

    if not new_grants:
        logger.info("Новых грантов нет.")
        return 0

    # Формирование и отправка сообщения
    header = (
        "🎓 <b>МОНИТОРИНГ ГРАНТОВ — МГТУ им. Баумана</b>\n"
        f"📅 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"🔍 <i>Новых записей: {len(new_grants)}</i>\n"
        f"💰 <i>Порог: от {settings['min_amount']:,} руб/год</i>\n\n"
    )

    body = ""
    for i, item in enumerate(new_grants, 1):
        body += format_grant(i, item)

    footer = "🤖 <i>Автоматический мониторинг грантов МГТУ</i>"
    full_message = header + body + footer

    success = send_telegram(full_message)
    if success:
        save_sent_grants(sent)
        logger.info(f"✅ Отправлено {len(new_grants)} грантов")
    else:
        logger.error("❌ Ошибка отправки в Telegram")

    return len(new_grants) if success else 0


# ─── Прямой запуск ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    settings = {"min_amount": 5_000_000, "min_days": 14}
    count = run_parser(settings)
    print(f"Готово. Отправлено: {count}")
