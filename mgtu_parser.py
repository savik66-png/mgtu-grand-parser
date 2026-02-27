#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПАРСЕР ГРАНТОВ ДЛЯ МГТУ ИМ. БАУМАНА — BotHost версия"""
import requests, re, json, hashlib, time, csv, os
from datetime import datetime
from typing import List, Dict, Any

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8097523464:AAHoovPAanUbRwJR0wNXUdjcwPBoRvvnTKQ")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002752798613")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(SCRIPT_DIR, 'sent_grants.json')
CSV_BACKUP_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ.csv')
HTML_REPORT_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ_отчет.html')
MIN_ANNUAL_AMOUNT = 5_000_000

MGTU_DIRECTIONS = [
    "Электромеханические беспилотные автомобили большой грузоподъемности",
    "Сверхпроизводительные вычисления и аналитика больших данных",
    "Персонализированная медицина и здоровьесбережение",
    "Биомедицинские исследования",
    "Химические технологии и лабораторные исследования",
    "Материалы и нанотехнологии",
    "Машиностроительные технологии и перспективные материалы",
    "Космическая техника и системы",
    "Оборонные технологии и системы",
    "Цифровые платформы и ИИ-сервисы",
    "Интеллектуальные производственные и транспортные системы",
    "Технологии энергомашиностроения",
    "Новые технологии транспорта и связи",
    "Венчурное финансирование НИОКР"
]

STATIC_GRANTS = {
    "mgtu_strategy_2030": {
        "name": "Стратегия 2030 МГТУ",
        "grants": [
            {"title": "Электромеханические беспилотные автомобили большой грузоподъемности", "organizer": "Минобрнауки России", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка отечественных научных приборов", "direction": "Транспортные системы", "details_url": "https://minobrnauki.gov.ru/", "rating": 4},
            {"title": "Сверхпроизводительные вычисления и аналитика больших данных", "organizer": "Минобрнауки России, РФТР", "amount": "20-50 млн руб./год", "annual_amount_min": 20_000_000, "description": "Создание гибридных сопроцессоров", "direction": "Суперкомпьютерные технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4},
            {"title": "Персонализированная медицина и здоровьесбережение", "organizer": "Минздрав, Минобрнауки", "amount": "10-30 млн руб./год", "annual_amount_min": 10_000_000, "description": "Индивидуальные подходы к диагностике", "direction": "Биомедицинские технологии", "details_url": "https://minzdrav.gov.ru/", "rating": 4},
            {"title": "Биомедицинские исследования (Биомедстарт)", "organizer": "Минздрав, Минобрнауки", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования в области биомедицины", "direction": "Биомедицинские технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4},
            {"title": "Химические технологии и лабораторные исследования", "organizer": "Минобрнауки, Минпромторг", "amount": "10-25 млн руб./год", "annual_amount_min": 10_000_000, "description": "Разработка новых химических технологий", "direction": "Химические технологии", "details_url": "https://minpromtorg.gov.ru/", "rating": 4},
            {"title": "Материалы и нанотехнологии", "organizer": "Минобрнауки, РФФИ", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования новых материалов", "direction": "Новые материалы", "details_url": "https://minobrnauki.gov.ru/", "rating": 4},
            {"title": "Машиностроительные технологии", "organizer": "Минпромторг, Минобрнауки", "amount": "15-35 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка технологий для машиностроения", "direction": "Машиностроение", "details_url": "https://minpromtorg.gov.ru/", "rating": 4},
            {"title": "Космическая техника и системы", "organizer": "Роскосмос, Минобрнауки", "amount": "25-60 млн руб./год", "annual_amount_min": 25_000_000, "description": "Компоненты для космической отрасли", "direction": "Космические технологии", "details_url": "https://www.roscosmos.ru/", "rating": 4},
            {"title": "Оборонные технологии и системы", "organizer": "Минобороны, Ростех", "amount": "30-100 млн руб./год", "annual_amount_min": 30_000_000, "description": "Технологии для ОПК", "direction": "Оборонные технологии", "details_url": "https://minoborony.gov.ru/", "rating": 4},
            {"title": "Цифровые платформы и ИИ-сервисы", "organizer": "Минцифры, Минобрнауки", "amount": "15-40 млн руб./год", "annual_amount_min": 15_000_000, "description": "Цифровые платформы на основе ИИ", "direction": "Цифровые технологии", "details_url": "https://digital.gov.ru/", "rating": 4},
            {"title": "Технологии энергомашиностроения", "organizer": "Минэнерго, Минобрнауки", "amount": "20-45 млн руб./год", "annual_amount_min": 20_000_000, "description": "Оборудование для энергетики", "direction": "Энергетическое машиностроение", "details_url": "https://minenergo.gov.ru/", "rating": 4},
            {"title": "Венчурное финансирование НИОКР", "organizer": "Фонды", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Проектное финансирование", "direction": "Инновационное предпринимательство", "details_url": "https://www.rvc.ru/", "rating": 4}
        ]
    }
}

def log_message(message: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "📝")
    print(f"[{ts}] {prefix} {message}")

def get_grant_hash(grant: Dict[str, Any]) -> str:
    text = f"{grant['title']}_{grant.get('organizer', '')}_{grant.get('amount', '')}"
    return hashlib.md5(text.encode()).hexdigest()

def load_sent_grants() -> set:
    try:
        if os.path.exists(SENT_GRANTS_FILE):
            with open(SENT_GRANTS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_sent_grants(sent_grants: set):
    try:
        with open(SENT_GRANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sent_grants), f, ensure_ascii=False, indent=2)
    except:
        pass

def send_telegram_message(text: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        max_len = 4000
        parts = []
        if len(text) > max_len:
            while text:
                if len(text) <= max_len:
                    parts.append(text)
                    break
                part = text[:max_len]
                last_nl = part.rfind('\n')
                if last_nl == -1:
                    parts.append(text[:max_len])
                    text = text[max_len:]
                else:
                    parts.append(text[:last_nl+1])
                    text = text[last_nl+1:]
        else:
            parts = [text]
        for part in parts:
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": part, "parse_mode": "HTML"}
            resp = requests.post(url, data=data, timeout=30)
            if resp.status_code != 200:
                return False
            time.sleep(0.5)
        return True
    except:
        return False

def format_telegram_message(grants: List[Dict[str, Any]]) -> str:
    if not grants:
        return "❌ Новых грантов не найдено"
    msg = "🎯 <b>ГРАНТЫ ДЛЯ МГТУ ИМ. БАУМАНА</b>\n"
    msg += f"📅 <i>Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
    msg += f"🔍 <i>Найдено: {len(grants)} грантов</i>\n\n"
    for i, g in enumerate(grants, 1):
        stars = "⭐" * g.get('rating', 3)
        msg += f"<b>#{i} {g['title']}</b> {stars}\n"
        msg += f"👤 <b>Организатор:</b> {g['organizer']}\n"
        msg += f"💰 <b>Финансирование:</b> {g['amount']}\n"
        msg += f"📊 <b>Направление:</b> {g['direction']}\n"
        msg += f"📝 <b>Описание:</b> {g['description'][:150]}...\n"
        msg += f"🔗 <b>Ссылка:</b> {g['details_url']}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "🤖 <i>Автоматический парсер грантов МГТУ</i>"
    return msg

def save_csv_report(grants: List[Dict[str, Any]]):
    try:
        with open(CSV_BACKUP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Название', 'Организатор', 'Сумма', 'Ссылка'])
            for g in grants:
                writer.writerow([g['title'], g['organizer'], g['amount'], g['details_url']])
    except:
        pass

def main():
    """Основная функция — запускает парсинг"""
    log_message("🚀 Запуск парсера...", "INFO")
    all_grants = []
    for src in STATIC_GRANTS.values():
        for g in src["grants"]:
            if g.get('annual_amount_min', 0) >= MIN_ANNUAL_AMOUNT:
                all_grants.append(g)
    sent = load_sent_grants()
    new_grants = []
    for g in all_grants:
        h = get_grant_hash(g)
        if h not in sent:
            new_grants.append(g)
            sent.add(h)
    save_sent_grants(sent)
    if not new_grants:
        log_message("ℹ️ Новых грантов не найдено", "INFO")
        return True
    msg = format_telegram_message(new_grants)
    success = send_telegram_message(msg)
    save_csv_report(new_grants)
    log_message(f"✅ Отправлено {len(new_grants)} грантов", "SUCCESS")
    return success

# 🔥 ЗАПУСК — БЕЗ input(), БЕЗ МЕНЮ
if __name__ == "__main__":
    log_message("=== ЗАПУСК ПАРСЕРА (BotHost) ===", "INFO")
    main()
    log_message("=== ГОТОВО ===", "SUCCESS")
