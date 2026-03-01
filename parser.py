#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер грантов для МГТУ им. Баумана
- Статические гранты из Стратегии МГТУ 2030
- Реальный парсинг RSS источников
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
HTML_REPORT_FILE = os.path.join(SCRIPT_DIR, "grants_report.html")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── Настройки ────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    defaults = {"min_amount": 5_000_000, "min_days": 14}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
    except Exception:
        pass
    return defaults

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")

# ─── Статические гранты из Стратегии МГТУ 2030 ───────────────────────────────

STATIC_GRANTS = [
    {
        "title": "Электромеханические беспилотные автомобили большой грузоподъёмности",
        "organizer": "Минобрнауки России",
        "amount": "от 15 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Разработка отечественных научных приборов для добывающих отраслей промышленности РФ",
        "direction": "Транспортные системы",
        "details_url": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "2-3 года",
        "special_requirements": "Наличие научного задела, соответствие нацпроекту 'Наука'",
        "eligible_participants": "Университеты и научные организации РФ",
    },
    {
        "title": "Сверхпроизводительные вычисления и аналитика больших данных",
        "organizer": "Минобрнауки России, РФТР",
        "amount": "20-50 млн руб./год",
        "annual_amount_min": 20_000_000,
        "description": "Создание отечественной продуктовой линейки гибридных сопроцессоров нового поколения",
        "direction": "Суперкомпьютерные технологии",
        "details_url": "https://minobrnauki.gov.ru/",
        "rating": 4,
        "deadline_info": "30-45 дней",
        "project_duration": "3 года",
        "special_requirements": "Соответствие приоритетным направлениям НТР",
        "eligible_participants": "Ведущие технические университеты",
    },
    {
        "title": "Персонализированная медицина и здоровьесбережение",
        "organizer": "Минздрав, Минобрнауки",
        "amount": "10-30 млн руб./год",
        "annual_amount_min": 10_000_000,
        "description": "Разработка индивидуальных подходов к диагностике и лечению заболеваний",
        "direction": "Биомедицинские технологии",
        "details_url": "https://minzdrav.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3 года",
        "special_requirements": "Наличие медицинских партнёров",
        "eligible_participants": "Университеты с биомедицинскими направлениями",
    },
    {
        "title": "Биомедицинские исследования (Биомедстарт)",
        "organizer": "Минздрав, Минобрнауки",
        "amount": "15-30 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Исследования в области биомедицины и биотехнологий",
        "direction": "Биомедицинские технологии",
        "details_url": "https://minobrnauki.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3 года",
        "special_requirements": "Научная новизна, практическая значимость",
        "eligible_participants": "Университеты и НИИ",
    },
    {
        "title": "Химические технологии и лабораторные исследования",
        "organizer": "Минобрнауки, Минпромторг",
        "amount": "10-25 млн руб./год",
        "annual_amount_min": 10_000_000,
        "description": "Разработка новых химических технологий и материалов",
        "direction": "Химические технологии",
        "details_url": "https://minpromtorg.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "2-3 года",
        "special_requirements": "Лабораторная база",
        "eligible_participants": "Университеты с химическими факультетами",
    },
    {
        "title": "Материалы и нанотехнологии (МНОКстарт)",
        "organizer": "Минобрнауки, РФФИ",
        "amount": "15-30 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Исследования и разработка новых материалов и нанотехнологий",
        "direction": "Новые материалы",
        "details_url": "https://minobrnauki.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3 года",
        "special_requirements": "Оборудование для нанотехнологий",
        "eligible_participants": "Исследовательские университеты",
    },
    {
        "title": "Машиностроительные технологии и перспективные материалы",
        "organizer": "Минпромторг, Минобрнауки",
        "amount": "15-35 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Разработка новых материалов и технологий для машиностроения",
        "direction": "Машиностроение",
        "details_url": "https://minpromtorg.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3 года",
        "special_requirements": "Промышленные партнёры",
        "eligible_participants": "Технические университеты",
    },
    {
        "title": "Космическая техника и системы",
        "organizer": "Роскосмос, Минобрнауки",
        "amount": "25-60 млн руб./год",
        "annual_amount_min": 25_000_000,
        "description": "Разработка компонентов и систем для космической отрасли",
        "direction": "Космические технологии",
        "details_url": "https://www.roscosmos.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3-5 лет",
        "special_requirements": "Допуск к космическим технологиям",
        "eligible_participants": "Аккредитованные организации",
    },
    {
        "title": "Оборонные технологии и системы",
        "organizer": "Минобороны, Ростех",
        "amount": "30-100 млн руб./год",
        "annual_amount_min": 30_000_000,
        "description": "Разработка технологий для оборонно-промышленного комплекса",
        "direction": "Оборонные технологии",
        "details_url": "https://minoborony.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3-5 лет",
        "special_requirements": "Форма допуска, лицензия ФСБ",
        "eligible_participants": "Организации с лицензией ФСБ",
    },
    {
        "title": "Цифровые платформы и ИИ-сервисы",
        "organizer": "Минцифры, Минобрнауки",
        "amount": "15-40 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Разработка цифровых платформ и сервисов на основе искусственного интеллекта",
        "direction": "Цифровые технологии",
        "details_url": "https://digital.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "2-3 года",
        "special_requirements": "Команда разработчиков",
        "eligible_participants": "IT-центры университетов",
    },
    {
        "title": "Технологии энергомашиностроения",
        "organizer": "Минэнерго, Минобрнауки",
        "amount": "20-45 млн руб./год",
        "annual_amount_min": 20_000_000,
        "description": "Разработка оборудования и технологий для энергетического машиностроения",
        "direction": "Энергетическое машиностроение",
        "details_url": "https://minenergo.gov.ru/",
        "rating": 4,
        "deadline_info": "30+ дней",
        "project_duration": "3 года",
        "special_requirements": "Партнёрство с энергокомпаниями",
        "eligible_participants": "Энергетические институты",
    },
    {
        "title": "Интеллектуальные производственные и транспортные системы",
        "organizer": "Минобрнауки, Фонд развития промышленности",
        "amount": "15-40 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Разработка систем автоматизации и роботизации производственных процессов",
        "direction": "Индустрия 4.0",
        "details_url": "https://minobrnauki.gov.ru/",
        "rating": 4,
        "deadline_info": "21-30 дней",
        "project_duration": "3 года",
        "special_requirements": "Промышленный партнёр",
        "eligible_participants": "Технические университеты",
    },
    {
        "title": "Новые технологии транспорта и связи",
        "organizer": "Минтранс, Минцифры",
        "amount": "10-25 млн руб./год",
        "annual_amount_min": 10_000_000,
        "description": "Разработка инновационных технологий в области транспорта и связи",
        "direction": "Транспорт и связь",
        "details_url": "https://mintrans.gov.ru/",
        "rating": 3,
        "deadline_info": "30+ дней",
        "project_duration": "2-3 года",
        "special_requirements": "Отраслевые партнёры",
        "eligible_participants": "Университеты транспортного профиля",
    },
    {
        "title": "Венчурное финансирование НИОКР",
        "organizer": "Уполномоченные банки, эндаумент-фонды",
        "amount": "от 15 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Механизм проектного финансирования инженерных разработок",
        "direction": "Инновационное предпринимательство",
        "details_url": "https://www.rvc.ru/",
        "rating": 4,
        "deadline_info": "Индивидуально",
        "project_duration": "2-5 лет",
        "special_requirements": "Бизнес-модель, коммерческий потенциал",
        "eligible_participants": "Стартапы и spin-off компании",
    },
]

# ─── RSS источники ─────────────────────────────────────────────────────────────

RSS_SOURCES = [
    {"name": "Минобрнауки",    "url": "https://minobrnauki.gov.ru/ru/press-center/news/feed/"},
    {"name": "РНФ",            "url": "https://rscf.ru/ru/news/feed/"},
    {"name": "Фонд Бортника",  "url": "https://fasie.ru/rss/"},
    {"name": "Научная Россия", "url": "https://scientificrussia.ru/news/rss"},
    {"name": "Гранты.ру",      "url": "https://www.grants.ru/rss/"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

GRANT_KEYWORDS = [
    "грант", "конкурс", "финансирован", "субсидия",
    "заявк", "отбор", "научный проект", "нир ", "ниокр",
]

# ─── Утилиты ──────────────────────────────────────────────────────────────────

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
        logger.error(f"Ошибка сохранения истории: {e}")

def grant_hash(title: str, source: str = "") -> str:
    return hashlib.md5(f"{title.strip().lower()}|{source}".encode()).hexdigest()

def is_grant_related(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in GRANT_KEYWORDS)

def extract_amount(text: str) -> Optional[int]:
    t = text.lower()
    for pattern, mult in [(r"(\d[\d\s]*)\s*млрд", 1_000_000_000), (r"(\d[\d\s]*)\s*млн", 1_000_000)]:
        for m in re.findall(pattern, t):
            try:
                return int(re.sub(r"\s", "", m)) * mult
            except ValueError:
                continue
    return None

# ─── Парсинг RSS ──────────────────────────────────────────────────────────────

def fetch_rss(source: dict) -> List[Dict]:
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
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

            full_text = f"{title} {desc}"
            if not is_grant_related(full_text):
                continue

            amount = extract_amount(full_text)
            items.append({
                "title":            title,
                "organizer":        source["name"],
                "amount":           f"{amount//1_000_000} млн руб." if amount else "Уточняется",
                "annual_amount_min": amount or 0,
                "description":      desc[:300] if desc else "",
                "direction":        "Актуальный конкурс",
                "details_url":      link,
                "rating":           3,
                "deadline_info":    pub_date[:25] if pub_date else "",
                "project_duration": "Уточняется",
                "special_requirements": "",
                "eligible_participants": "",
                "source":           source["name"],
                "type":             "rss",
            })

        logger.info(f"  {source['name']}: найдено {len(items)} грантов")
    except Exception as e:
        logger.warning(f"  {source['name']}: {e}")
    return items

# ─── Отправка в Telegram ──────────────────────────────────────────────────────

def send_telegram(text: str, chat_id: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_len = 4000
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text); break
        cut = text[:max_len].rfind("\n")
        if cut == -1: cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip()

    for part in parts:
        try:
            r = requests.post(url, data={
                "chat_id": chat_id, "text": part,
                "parse_mode": "HTML", "disable_web_page_preview": True,
            }, timeout=30)
            if r.status_code != 200:
                logger.error(f"Telegram: {r.text[:200]}")
                return False
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False
    return True

def format_message(grants: List[Dict], settings: dict) -> str:
    header = (
        "🎯 <b>ГРАНТЫ ДЛЯ МГТУ ИМ. БАУМАНА</b>\n"
        f"📅 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
        f"🔍 <i>Найдено: {len(grants)}</i>  "
        f"💰 <i>Порог: от {settings['min_amount']:,} руб/год</i>\n\n"
    )
    body = ""
    for i, g in enumerate(grants, 1):
        stars = "⭐" * g.get("rating", 3)
        body += f"<b>#{i} {g['title']}</b> {stars}\n"
        body += f"👤 <b>Организатор:</b> {g['organizer']}\n"
        body += f"💰 <b>Финансирование:</b> {g['amount']}\n"
        body += f"📊 <b>Направление:</b> {g['direction']}\n"
        if g.get("deadline_info"):
            body += f"⏳ <b>Срок подачи:</b> {g['deadline_info']}\n"
        if g.get("project_duration") and g["project_duration"] != "Уточняется":
            body += f"📆 <b>Реализация:</b> {g['project_duration']}\n"
        if g.get("special_requirements"):
            body += f"⚡ <b>Требования:</b> {g['special_requirements'][:100]}\n"
        if g.get("eligible_participants"):
            body += f"👥 <b>Участники:</b> {g['eligible_participants'][:100]}\n"
        if g.get("description"):
            body += f"📝 {g['description'][:200]}\n"
        if g.get("details_url"):
            body += f"🔗 <a href=\"{g['details_url']}\">Подробнее →</a>\n"
        body += "━" * 22 + "\n\n"
    return header + body + "🤖 <i>Автоматический мониторинг грантов МГТУ</i>"

# ─── HTML отчёт ───────────────────────────────────────────────────────────────

def save_html_report(grants: List[Dict]):
    try:
        rows = ""
        for i, g in enumerate(grants, 1):
            stars = "⭐" * g.get("rating", 3)
            rows += f"""
            <tr>
                <td>{i}</td>
                <td><b>{g['title']}</b><br><small>{g.get('description','')[:150]}</small></td>
                <td>{g['organizer']}</td>
                <td style="color:green;font-weight:bold">{g['amount']}</td>
                <td>{g['direction']}</td>
                <td>{g.get('deadline_info','')}</td>
                <td>{g.get('project_duration','')}</td>
                <td>{stars}</td>
                <td><a href="{g.get('details_url','#')}" target="_blank">Открыть</a></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Гранты МГТУ — {datetime.now().strftime('%d.%m.%Y')}</title>
<style>
  body{{font-family:Arial,sans-serif;padding:20px;background:#f5f5f5}}
  h1{{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:8px}}
  table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1)}}
  th{{background:#667eea;color:white;padding:12px;text-align:left}}
  td{{padding:10px;border-bottom:1px solid #eee;vertical-align:top}}
  tr:hover{{background:#f9f9ff}}
  a{{color:#667eea}}
</style>
</head>
<body>
<h1>🎯 Гранты для МГТУ им. Баумана</h1>
<p>📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} | Найдено грантов: <b>{len(grants)}</b></p>
<table>
<tr><th>#</th><th>Название</th><th>Организатор</th><th>Финансирование</th>
<th>Направление</th><th>Срок подачи</th><th>Реализация</th><th>Рейтинг</th><th>Ссылка</th></tr>
{rows}
</table>
<p><i>🤖 Автоматический мониторинг грантов МГТУ</i></p>
</body></html>"""

        with open(HTML_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML отчёт сохранён: {HTML_REPORT_FILE}")
    except Exception as e:
        logger.error(f"Ошибка HTML отчёта: {e}")

# ─── Главная функция ──────────────────────────────────────────────────────────

def run_parser(settings: dict = None, channel_id: str = None) -> int:
    if settings is None:
        settings = load_settings()

    target = channel_id or os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID", "")
    min_amount = settings.get("min_amount", 5_000_000)

    logger.info("─── Запуск парсера ───────────────────────────")
    logger.info(f"Порог суммы: {min_amount:,} руб/год")

    # 1. Статические гранты
    all_grants = [g for g in STATIC_GRANTS if g["annual_amount_min"] >= min_amount]
    logger.info(f"Статических грантов: {len(all_grants)}")

    # 2. RSS (если доступны)
    rss_count = 0
    for source in RSS_SOURCES:
        items = fetch_rss(source)
        for item in items:
            if item["annual_amount_min"] == 0 or item["annual_amount_min"] >= min_amount:
                all_grants.append(item)
                rss_count += 1
    logger.info(f"Из RSS: {rss_count}")

    # 3. Фильтр новых
    sent = load_sent_grants()
    new_grants = []
    for g in all_grants:
        h = grant_hash(g["title"], g.get("source", g.get("organizer", "")))
        if h not in sent:
            new_grants.append(g)
            sent.add(h)

    logger.info(f"Новых грантов: {len(new_grants)}")

    if not new_grants:
        return 0

    # 4. Сортировка по рейтингу
    new_grants.sort(key=lambda x: (x.get("rating", 0), x.get("annual_amount_min", 0)), reverse=True)

    # 5. Отправка в Telegram
    msg = format_message(new_grants, settings)
    success = send_telegram(msg, target)

    if success:
        save_sent_grants(sent)
        save_html_report(new_grants)
        logger.info(f"✅ Отправлено {len(new_grants)} грантов")
        return len(new_grants)
    else:
        logger.error("❌ Ошибка отправки")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = run_parser()
    print(f"Готово. Отправлено: {count}")
