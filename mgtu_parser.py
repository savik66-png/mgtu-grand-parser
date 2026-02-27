#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПАРСЕР ГРАНТОВ ДЛЯ МГТУ ИМ. БАУМАНА
Адаптированная версия для BotHost (без input, с env-переменными)
"""
import requests
import re
import json
import hashlib
import time
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ==================== КОНФИГУРАЦИЯ ====================
# 🔑 ТОКЕНЫ ЧИТАЕМ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (настраиваются в панели BotHost)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8097523464:AAHoovPAanUbRwJR0wNXUdjcwPBoRvvnTKQ")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002752798613")

# Пути к файлам (на хостинге)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(SCRIPT_DIR, 'sent_grants.json')
CSV_BACKUP_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ.csv')
HTML_REPORT_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ_отчет.html')

# Критерии фильтрации
MIN_ANNUAL_AMOUNT = 5_000_000
MIN_DEADLINE_DAYS = 14

# Тематические направления МГТУ (Стратегия 2030)
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

# Источники данных (оставляем как есть, парсинг сайтов можно добавить позже)
GRANT_SOURCES = {
    "minobrnauki": {"name": "Минобрнауки России", "base_url": "https://minobrnauki.gov.ru", "api_endpoints": ["https://minobrnauki.gov.ru/ru/activity/grant/competitions/"], "priority": 1},
    "rscf": {"name": "Российский научный фонд", "base_url": "https://rscf.ru", "api_endpoints": ["https://rscf.ru/contests/"], "priority": 1},
    "fasie": {"name": "Фонд содействия инновациям", "base_url": "https://fasie.ru", "api_endpoints": ["https://fasie.ru/programs/"], "priority": 2},
    "rfbr": {"name": "РФТР", "base_url": "https://rftr.ru", "api_endpoints": [], "priority": 2},
    "grants_ru": {"name": "База грантов России", "base_url": "https://grants.ru", "api_endpoints": ["https://grants.ru/grants/"], "priority": 3}
}

# Статические гранты (твои данные — без изменений)
STATIC_GRANTS = {
    "mgtu_strategy_2030": {
        "name": "Стратегия 2030 МГТУ",
        "grants": [
            {"title": "Электромеханические беспилотные автомобили большой грузоподъемности", "organizer": "Минобрнауки России", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка отечественных научных приборов для добывающих отраслей промышленности РФ", "direction": "Транспортные системы", "details_url": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Наличие научного задела", "eligible_participants": "Университеты и научные организации РФ"},
            {"title": "Сверхпроизводительные вычисления и аналитика больших данных", "organizer": "Минобрнауки России, РФТР", "amount": "20-50 млн руб./год", "annual_amount_min": 20_000_000, "description": "Создание отечественной продуктовой линейки гибридных сопроцессоров нового поколения", "direction": "Суперкомпьютерные технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30-45 дней", "project_duration": "3 года", "special_requirements": "Соответствие приоритетным направлениям НТР", "eligible_participants": "Ведущие технические университеты"},
            {"title": "Персонализированная медицина и здоровьесбережение", "organizer": "Минздрав, Минобрнауки", "amount": "10-30 млн руб./год", "annual_amount_min": 10_000_000, "description": "Разработка индивидуальных подходов к диагностике и лечению заболеваний", "direction": "Биомедицинские технологии", "details_url": "https://minzdrav.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Наличие медицинских партнеров", "eligible_participants": "Университеты с биомедицинскими направлениями"},
            {"title": "Биомедицинские исследования (Биомедстарт)", "organizer": "Минздрав, Минобрнауки", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования в области биомедицины и биотехнологий", "direction": "Биомедицинские технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Научная новизна", "eligible_participants": "Университеты и НИИ"},
            {"title": "Химические технологии и лабораторные исследования (Химлабстарт)", "organizer": "Минобрнауки, Минпромторг", "amount": "10-25 млн руб./год", "annual_amount_min": 10_000_000, "description": "Разработка новых химических технологий", "direction": "Химические технологии", "details_url": "https://minpromtorg.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Лабораторная база", "eligible_participants": "Университеты с химическими факультетами"},
            {"title": "Материалы и нанотехнологии (МНОКстарт)", "organizer": "Минобрнауки, РФФИ", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования новых материалов", "direction": "Новые материалы", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Оборудование для нанотехнологий", "eligible_participants": "Исследовательские университеты"},
            {"title": "Машиностроительные технологии", "organizer": "Минпромторг", "amount": "15-35 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка технологий для машиностроения", "direction": "Машиностроение", "details_url": "https://minpromtorg.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Промышленные партнеры", "eligible_participants": "Технические университеты"},
            {"title": "Космическая техника и системы", "organizer": "Роскосмос", "amount": "25-60 млн руб./год", "annual_amount_min": 25_000_000, "description": "Компоненты для космической отрасли", "direction": "Космические технологии", "details_url": "https://www.roscosmos.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3-5 лет", "special_requirements": "Допуск", "eligible_participants": "Аккредитованные организации"},
            {"title": "Оборонные технологии", "organizer": "Минобороны", "amount": "30-100 млн руб./год", "annual_amount_min": 30_000_000, "description": "Технологии для ОПК", "direction": "Оборонные технологии", "details_url": "https://minoborony.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3-5 лет", "special_requirements": "Форма допуска", "eligible_participants": "Организации с лицензией"},
            {"title": "Цифровые платформы и ИИ", "organizer": "Минцифры", "amount": "15-40 млн руб./год", "annual_amount_min": 15_000_000, "description": "Цифровые платформы на основе ИИ", "direction": "Цифровые технологии", "details_url": "https://digital.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Команда разработчиков", "eligible_participants": "IT-центры"},
            {"title": "Технологии энергомашиностроения", "organizer": "Минэнерго", "amount": "20-45 млн руб./год", "annual_amount_min": 20_000_000, "description": "Оборудование для энергетики", "direction": "Энергетическое машиностроение", "details_url": "https://minenergo.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Партнерство", "eligible_participants": "Энергетические институты"},
            {"title": "Венчурное финансирование НИОКР", "organizer": "Фонды", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Проектное финансирование", "direction": "Инновационное предпринимательство", "details_url": "https://www.rvc.ru/", "rating": 4, "deadline_info": "Индивидуально", "project_duration": "2-5 лет", "special_requirements": "Бизнес-модель", "eligible_participants": "Стартапы"}
        ]
    }
}

# ==================== УТИЛИТЫ ====================
def log_message(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "📝")
    print(f"[{timestamp}] {prefix} {message}")

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

# ==================== TELEGRAM (ТВОЙ РАБОЧИЙ КОД) ====================
def send_telegram_message(text: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        max_length = 4000
        parts = []
        if len(text) > max_length:
            while text:
                if len(text) <= max_length:
                    parts.append(text)
                    break
                part = text[:max_length]
                last_nl = part.rfind('\n')
                if last_nl == -1:
                    parts.append(text[:max_length])
                    text = text[max_length:]
                else:
                    parts.append(text[:last_nl+1])
                    text = text[last_nl+1:]
        else:
            parts = [text]
        for part in parts:
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": part, "parse_mode": "HTML"}
            resp = requests.post(url, data=data, timeout=30)
            if resp.status_code != 200:
                log_message(f"Telegram error: {resp.text}", "ERROR")
                return False
            time.sleep(0.5)
        return True
    except Exception as e:
        log_message(f"Send error: {e}", "ERROR")
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

# ==================== ОТЧЕТЫ ====================
def save_csv_report(grants: List[Dict[str, Any]]):
    try:
        with open(CSV_BACKUP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Название', 'Организатор', 'Сумма', 'Ссылка'])
            for g in grants:
                writer.writerow([g['title'], g['organizer'], g['amount'], g['details_url']])
    except:
        pass

def save_html_report(grants: List[Dict[str, Any]]):
    try:
        html = f"<html><body><h1>Гранты МГТУ</h1><p>Дата: {datetime.now()}</p>"
        for g in grants:
            html += f"<div><b>{g['title']}</b><br>Орг: {g['organizer']}<br>Сумма: {g['amount']}<br><a href='{g['details_url']}'>Ссылка</a></div><hr>"
        html += "</body></html>"
        with open(HTML_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
    except:
        pass

# ==================== ОСНОВНАЯ ЛОГИКА ====================
def run_parser():
    """Запускает парсинг — как в твоём рабочем скрипте"""
    log_message("🚀 Запуск парсера...", "INFO")
    
    # Собираем гранты
    all_grants = []
    for source_data in STATIC_GRANTS.values():
        for g in source_data["grants"]:
            if g.get('annual_amount_min', 0) >= MIN_ANNUAL_AMOUNT:
                all_grants.append(g)
    
    # Фильтруем новые
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
    
    # Отправляем
    msg = format_telegram_message(new_grants)
    success = send_telegram_message(msg)
    
    # Сохраняем отчеты
    save_csv_report(new_grants)
    save_html_report(new_grants)
    
    log_message(f"✅ Отправлено {len(new_grants)} грантов", "SUCCESS")
    return success

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    # Запуск только функции main(), без input()
    log_message("=== ЗАПУСК ПАРСЕРА ===", "INFO")
    main()
    log_message("=== ГОТОВО ===", "SUCCESS")
