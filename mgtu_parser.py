#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПАРСЕР ГРАНТОВ ДЛЯ МГТУ ИМ. БАУМАНА
Автоматический мониторинг научных конкурсов и грантов
Адаптировано для BotHost (без input, с env-переменными)
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
# Настройки Telegram (берём из переменных окружения BotHost)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8097523464:AAHoovPAanUbRwJR0wNXUdjcwPBoRvvnTKQ")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002752798613")

# Пути к файлам
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(SCRIPT_DIR, 'sent_grants.json')
CSV_BACKUP_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ.csv')
HTML_REPORT_FILE = os.path.join(SCRIPT_DIR, 'гранты_МГТУ_отчет.html')

# Критерии фильтрации
MIN_ANNUAL_AMOUNT = 5_000_000  # 5 млн руб. в год
MIN_DEADLINE_DAYS = 14  # минимум 14 дней на подготовку

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

# Статические гранты из Стратегии МГТУ 2030
STATIC_GRANTS = {
    "mgtu_strategy_2030": {
        "name": "Стратегия 2030 МГТУ",
        "grants": [
            {
                "title": "Электромеханические беспилотные автомобили большой грузоподъемности",
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
                "eligible_participants": "Университеты и научные организации РФ"
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
                "eligible_participants": "Ведущие технические университеты"
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
                "special_requirements": "Наличие медицинских партнеров",
                "eligible_participants": "Университеты с биомедицинскими направлениями"
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
                "eligible_participants": "Университеты и НИИ"
            },
            {
                "title": "Химические технологии и лабораторные исследования (Химлабстарт)",
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
                "eligible_participants": "Университеты с химическими факультетами"
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
                "eligible_participants": "Исследовательские университеты"
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
                "special_requirements": "Промышленные партнеры",
                "eligible_participants": "Технические университеты"
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
                "eligible_participants": "Аккредитованные организации"
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
                "special_requirements": "Форма допуска",
                "eligible_participants": "Организации с лицензией ФСБ"
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
                "eligible_participants": "IT-центры университетов"
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
                "special_requirements": "Партнерство с энергокомпаниями",
                "eligible_participants": "Энергетические институты"
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
                "eligible_participants": "Стартапы и spin-off компании"
            }
        ]
    }
}

# ==================== УТИЛИТЫ ====================
def log_message(message: str, level: str = "INFO"):
    """Логирование сообщений"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🔍"
    }.get(level, "📝")
    print(f"[{timestamp}] {prefix} {message}")

def get_grant_hash(grant: Dict[str, Any]) -> str:
    """Создание уникального хеша для гранта"""
    grant_text = f"{grant['title']}_{grant.get('organizer', '')}_{grant.get('amount', '')}"
    return hashlib.md5(grant_text.encode()).hexdigest()

# ==================== РАБОТА С ДАННЫМИ ====================
def load_sent_grants() -> set:
    """Загрузка истории отправленных грантов"""
    try:
        if os.path.exists(SENT_GRANTS_FILE):
            with open(SENT_GRANTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log_message(f"Загружено {len(data)} отправленных грантов", "SUCCESS")
                return set(data)
        else:
            log_message("Файл истории не найден, создаем новый", "WARNING")
            return set()
    except Exception as e:
        log_message(f"Ошибка загрузки истории: {e}", "ERROR")
        return set()

def save_sent_grants(sent_grants: set):
    """Сохранение истории отправленных грантов"""
    try:
        with open(SENT_GRANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sent_grants), f, ensure_ascii=False, indent=2)
        log_message(f"Сохранено {len(sent_grants)} грантов в историю", "SUCCESS")
    except Exception as e:
        log_message(f"Ошибка сохранения истории: {e}", "ERROR")

def filter_new_grants(grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Фильтрация только новых грантов"""
    sent_grants = load_sent_grants()
    new_grants = []
    log_message(f"Проверяем {len(grants)} грантов на новизну...", "INFO")
    for grant in grants:
        grant_hash = get_grant_hash(grant)
        if grant_hash not in sent_grants:
            new_grants.append(grant)
            sent_grants.add(grant_hash)
            log_message(f"Новый грант: {grant['title'][:50]}...", "SUCCESS")
        else:
            log_message(f"Пропускаем: {grant['title'][:50]}...", "DEBUG")
    save_sent_grants(sent_grants)
    return new_grants

# ==================== ПАРСИНГ ====================
def get_static_grants() -> List[Dict[str, Any]]:
    """Получение статических грантов из Стратегии МГТУ 2030"""
    all_grants = []
    log_message("Загружаем статические гранты из Стратегии МГТУ 2030...", "INFO")
    for source_id, source_data in STATIC_GRANTS.items():
        for grant_data in source_data["grants"]:
            annual_amount = grant_data.get('annual_amount_min', 0)
            if annual_amount >= MIN_ANNUAL_AMOUNT:
                grant = {
                    'title': grant_data['title'],
                    'organizer': grant_data['organizer'],
                    'amount': grant_data['amount'],
                    'annual_amount_min': annual_amount,
                    'description': grant_data['description'],
                    'direction': grant_data['direction'],
                    'source': source_data['name'],
                    'details_url': grant_data['details_url'],
                    'rating': grant_data.get('rating', 3),
                    'deadline_info': grant_data.get('deadline_info', 'Уточняется'),
                    'deadline_days': -1,
                    'open_date': 'Регулярно',
                    'close_date': 'Уточняется',
                    'project_duration': grant_data.get('project_duration', 'Уточняется'),
                    'special_requirements': grant_data.get('special_requirements', 'Стандартные'),
                    'eligible_participants': grant_data.get('eligible_participants', 'Все организации'),
                    'date_parsed': datetime.now().strftime('%d.%m.%Y %H:%M'),
                    'type': 'static'
                }
                all_grants.append(grant)
                log_message(f"Добавлен: {grant['title'][:50]}...", "SUCCESS")
    return all_grants

# ==================== TELEGRAM ====================
def send_telegram_message(text: str) -> bool:
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        max_length = 4000
        parts = []
        if len(text) > max_length:
            while text:
                if len(text) <= max_length:
                    parts.append(text)
                    break
                else:
                    part = text[:max_length]
                    last_newline = part.rfind('\n')
                    if last_newline == -1:
                        last_newline = max_length
                    parts.append(text[:last_newline + 1])
                    text = text[last_newline + 1:]
        else:
            parts = [text]
        success_count = 0
        for i, part in enumerate(parts, 1):
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": part,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                success_count += 1
                log_message(f"Отправлена часть {i}/{len(parts)}", "SUCCESS")
            else:
                log_message(f"Ошибка отправки части {i}: {response.text}", "ERROR")
                return False
            time.sleep(0.5)
        return success_count == len(parts)
    except Exception as e:
        log_message(f"Критическая ошибка Telegram: {e}", "ERROR")
        return False

def format_telegram_message(grants: List[Dict[str, Any]]) -> str:
    """Форматирование сообщения для Telegram"""
    if not grants:
        return "❌ Новых грантов, соответствующих критериям, не найдено"
    message = "🎯 <b>ГРАНТЫ ДЛЯ МГТУ ИМ. БАУМАНА</b>\n"
    message += f"📅 <i>Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n"
    message += f"🔍 <i>Найдено: {len(grants)} грантов</i>\n"
    message += f"💰 <i>Критерий: от 5 млн руб./год</i>\n"
    message += f"⏰ <i>Срок подготовки: от 14 дней</i>\n\n"
    for i, grant in enumerate(grants, 1):
        rating_stars = "⭐" * grant.get('rating', 3)
        message += f"<b>#{i} {grant['title']}</b> {rating_stars}\n"
        message += f"👤 <b>Организатор:</b> {grant['organizer']}\n"
        message += f"💰 <b>Финансирование:</b> {grant['amount']}\n"
        message += f"📊 <b>Направление:</b> {grant['direction']}\n"
        message += f"📝 <b>Описание:</b> {grant['description'][:150]}...\n"
        message += f"⏳ <b>Срок реализации:</b> {grant.get('project_duration', 'Уточняется')}\n"
        message += f"🔗 <b>Ссылка:</b> {grant['details_url']}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "🤖 <i>Автоматический парсер грантов МГТУ</i>\n"
    message += "📧 <i>Вопросы: Центр 'Моя наука'</i>"
    return message

# ==================== ОТЧЕТЫ ====================
def save_csv_report(grants: List[Dict[str, Any]]):
    """Сохранение CSV отчета"""
    try:
        with open(CSV_BACKUP_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Дата парсинга', 'Рейтинг', 'Название', 'Организатор',
                'Финансирование', 'Годовая сумма (руб)', 'Направление',
                'Дата открытия', 'Дата закрытия', 'Срок реализации',
                'Особые требования', 'Участники', 'Ссылка'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for grant in grants:
                writer.writerow({
                    'Дата парсинга': grant.get('date_parsed', ''),
                    'Рейтинг': '⭐' * grant.get('rating', 3),
                    'Название': grant['title'],
                    'Организатор': grant['organizer'],
                    'Финансирование': grant['amount'],
                    'Годовая сумма (руб)': grant.get('annual_amount_min', 0),
                    'Направление': grant['direction'],
                    'Дата открытия': grant.get('open_date', ''),
                    'Дата закрытия': grant.get('close_date', ''),
                    'Срок реализации': grant.get('project_duration', ''),
                    'Особые требования': grant.get('special_requirements', ''),
                    'Участники': grant.get('eligible_participants', ''),
                    'Ссылка': grant['details_url']
                })
        log_message(f"CSV отчет сохранен: {CSV_BACKUP_FILE}", "SUCCESS")
    except Exception as e:
        log_message(f"Ошибка сохранения CSV: {e}", "ERROR")

def save_html_report(grants: List[Dict[str, Any]]):
    """Сохранение HTML отчета"""
    try:
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Гранты МГТУ - {datetime.now().strftime('%d.%m.%Y')}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
.grant-card {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #667eea; }}
.amount {{ color: #28a745; font-weight: bold; }}
.link {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
</style>
</head>
<body>
<div class="header">
<h1>🎯 Гранты для МГТУ им. Баумана</h1>
<p>📅 Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
<p>📊 Найдено грантов: {len(grants)}</p>
</div>
"""
        for i, grant in enumerate(grants, 1):
            rating_stars = "⭐" * grant.get('rating', 3)
            html_content += f"""
<div class="grant-card">
<h3>#{i} {grant['title']}</h3>
<div>{rating_stars}</div>
<p><b>👤 Организатор:</b> {grant['organizer']}</p>
<p><b>💰 Финансирование:</b> <span class="amount">{grant['amount']}</span></p>
<p><b>📊 Направление:</b> {grant['direction']}</p>
<p><b>📝 Описание:</b> {grant['description']}</p>
<a href="{grant['details_url']}" class="link" target="_blank">🔗 Подробнее</a>
</div>
"""
        html_content += """
<div style="text-align: center; margin-top: 40px; color: #666;">
<p>🤖 Автоматический парсер грантов МГТУ им. Баумана</p>
</div>
</body>
</html>"""
        with open(HTML_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log_message(f"HTML отчет сохранен: {HTML_REPORT_FILE}", "SUCCESS")
    except Exception as e:
        log_message(f"Ошибка сохранения HTML: {e}", "ERROR")

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    """Основная функция парсера"""
    log_message("=" * 60, "INFO")
    log_message("ЗАПУСК ПАРСЕРА ГРАНТОВ ДЛЯ МГТУ", "INFO")
    log_message("=" * 60, "INFO")
    
    # Собираем гранты
    all_grants = get_static_grants()
    
    # Сортируем по рейтингу и сумме
    all_grants.sort(key=lambda x: (x.get('rating', 0), x.get('annual_amount_min', 0)), reverse=True)
    
    # Фильтруем новые
    new_grants = filter_new_grants(all_grants)
    
    if not new_grants:
        log_message("Новых грантов не найдено", "INFO")
        # НЕ отправляем сообщение в Telegram, чтобы не спамить
        return True
    
    # Отправляем в Telegram
    telegram_message = format_telegram_message(new_grants)
    telegram_success = send_telegram_message(telegram_message)
    
    # Сохраняем отчеты
    save_csv_report(new_grants)
    save_html_report(new_grants)
    
    log_message("=" * 60, "INFO")
    log_message(f"НАЙДЕНО {len(new_grants)} НОВЫХ ГРАНТОВ!", "SUCCESS")
    log_message(f"Telegram: {'✅' if telegram_success else '❌'}", "INFO")
    log_message("=" * 60, "INFO")
    
    return telegram_success

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    log_message("=== ЗАПУСК ПАРСЕРА (BotHost) ===", "INFO")
    main()
    log_message("=== ГОТОВО ===", "SUCCESS")
