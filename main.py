# main.py - ПРОСТАЯ ВЕРСИЯ НА ОСНОВЕ ТВОЕГО РАБОЧЕГО КОДА
import os
import sys
import logging
import requests
import json
import hashlib
import csv
from datetime import datetime
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002752798613")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Пути к файлам (на хостинге)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(BASE_DIR, 'sent_grants.json')
CSV_BACKUP_FILE = os.path.join(BASE_DIR, 'гранты_МГТУ.csv')
HTML_REPORT_FILE = os.path.join(BASE_DIR, 'гранты_МГТУ_отчет.html')

# Критерии
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

# Статические гранты (твои данные)
STATIC_GRANTS = [
    {"title": "Электромеханические беспилотные автомобили большой грузоподъемности", "organizer": "Минобрнауки России", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка отечественных научных приборов для добывающих отраслей промышленности РФ", "direction": "Транспортные системы", "details_url": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Наличие научного задела", "eligible_participants": "Университеты и научные организации РФ"},
    {"title": "Сверхпроизводительные вычисления и аналитика больших данных", "organizer": "Минобрнауки России, РФТР", "amount": "20-50 млн руб./год", "annual_amount_min": 20_000_000, "description": "Создание отечественной продуктовой линейки гибридных сопроцессоров нового поколения", "direction": "Суперкомпьютерные технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30-45 дней", "project_duration": "3 года", "special_requirements": "Соответствие приоритетным направлениям НТР", "eligible_participants": "Ведущие технические университеты"},
    {"title": "Персонализированная медицина и здоровьесбережение", "organizer": "Минздрав, Минобрнауки", "amount": "10-30 млн руб./год", "annual_amount_min": 10_000_000, "description": "Разработка индивидуальных подходов к диагностике и лечению заболеваний", "direction": "Биомедицинские технологии", "details_url": "https://minzdrav.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Наличие медицинских партнеров", "eligible_participants": "Университеты с биомедицинскими направлениями"},
    {"title": "Биомедицинские исследования (Биомедстарт)", "organizer": "Минздрав, Минобрнауки", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования в области биомедицины и биотехнологий", "direction": "Биомедицинские технологии", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Научная новизна, практическая значимость", "eligible_participants": "Университеты и НИИ"},
    {"title": "Химические технологии и лабораторные исследования (Химлабстарт)", "organizer": "Минобрнауки, Минпромторг", "amount": "10-25 млн руб./год", "annual_amount_min": 10_000_000, "description": "Разработка новых химических технологий и материалов", "direction": "Химические технологии", "details_url": "https://minpromtorg.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Лабораторная база", "eligible_participants": "Университеты с химическими факультетами"},
    {"title": "Материалы и нанотехнологии (МНОКстарт)", "organizer": "Минобрнауки, РФФИ", "amount": "15-30 млн руб./год", "annual_amount_min": 15_000_000, "description": "Исследования и разработка новых материалов и нанотехнологий", "direction": "Новые материалы", "details_url": "https://minobrnauki.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Оборудование для нанотехнологий", "eligible_participants": "Исследовательские университеты"},
    {"title": "Машиностроительные технологии и перспективные материалы", "organizer": "Минпромторг, Минобрнауки", "amount": "15-35 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка новых материалов и технологий для машиностроения", "direction": "Машиностроение", "details_url": "https://minpromtorg.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Промышленные партнеры", "eligible_participants": "Технические университеты"},
    {"title": "Космическая техника и системы", "organizer": "Роскосмос, Минобрнауки", "amount": "25-60 млн руб./год", "annual_amount_min": 25_000_000, "description": "Разработка компонентов и систем для космической отрасли", "direction": "Космические технологии", "details_url": "https://www.roscosmos.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3-5 лет", "special_requirements": "Допуск к космическим технологиям", "eligible_participants": "Аккредитованные организации"},
    {"title": "Оборонные технологии и системы", "organizer": "Минобороны, Ростех", "amount": "30-100 млн руб./год", "annual_amount_min": 30_000_000, "description": "Разработка технологий для оборонно-промышленного комплекса", "direction": "Оборонные технологии", "details_url": "https://minoborony.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3-5 лет", "special_requirements": "Форма допуска", "eligible_participants": "Организации с лицензией ФСБ"},
    {"title": "Цифровые платформы и ИИ-сервисы", "organizer": "Минцифры, Минобрнауки", "amount": "15-40 млн руб./год", "annual_amount_min": 15_000_000, "description": "Разработка цифровых платформ и сервисов на основе искусственного интеллекта", "direction": "Цифровые технологии", "details_url": "https://digital.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "2-3 года", "special_requirements": "Команда разработчиков", "eligible_participants": "IT-центры университетов"},
    {"title": "Технологии энергомашиностроения", "organizer": "Минэнерго, Минобрнауки", "amount": "20-45 млн руб./год", "annual_amount_min": 20_000_000, "description": "Разработка оборудования и технологий для энергетического машиностроения", "direction": "Энергетическое машиностроение", "details_url": "https://minenergo.gov.ru/", "rating": 4, "deadline_info": "30+ дней", "project_duration": "3 года", "special_requirements": "Партнерство с энергокомпаниями", "eligible_participants": "Энергетические институты"},
    {"title": "Венчурное финансирование НИОКР", "organizer": "Уполномоченные банки, эндаумент-фонды", "amount": "от 15 млн руб./год", "annual_amount_min": 15_000_000, "description": "Механизм проектного финансирования инженерных разработок", "direction": "Инновационное предпринимательство", "details_url": "https://www.rvc.ru/", "rating": 4, "deadline_info": "Индивидуально", "project_duration": "2-5 лет", "special_requirements": "Бизнес-модель, коммерческий потенциал", "eligible_participants": "Стартапы и spin-off компании"}
]

# ==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

def log_message(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "📝")
    print(f"[{timestamp}] {prefix} {message}")

# ==================== РАБОТА С ИСТОРИЕЙ (SQLite не нужен, используем JSON как раньше) ====================
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

def get_grant_hash(grant: Dict[str, Any]) -> str:
    text = f"{grant['title']}_{grant.get('organizer', '')}_{grant.get('amount', '')}"
    return hashlib.md5(text.encode()).hexdigest()

# ==================== ОТПРАВКА В TELEGRAM (ТВОЙ РАБОЧИЙ КОД С requests) ====================
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
                logger.error(f"Telegram error: {resp.text}")
                return False
        return True
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

# ==================== ФОРМАТИРОВАНИЕ СООБЩЕНИЯ ====================
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

# ==================== ОСНОВНАЯ ЛОГИКА ПАРСЕРА (ИЗ ТВОЕГО КОДА) ====================
def run_parser() -> bool:
    """Запускает парсинг и отправку — как в твоём рабочем скрипте"""
    log_message("🚀 Запуск парсера...", "INFO")
    
    # Собираем гранты
    all_grants = []
    for g in STATIC_GRANTS:
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
        send_telegram_message("🔄 Новых грантов не найдено")
        return True
    
    # Отправляем
    msg = format_telegram_message(new_grants)
    success = send_telegram_message(msg)
    
    # Сохраняем CSV (упрощённо)
    try:
        with open(CSV_BACKUP_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Название', 'Организатор', 'Сумма', 'Ссылка'])
            for g in new_grants:
                writer.writerow([g['title'], g['organizer'], g['amount'], g['details_url']])
    except:
        pass
    
    log_message(f"✅ Отправлено {len(new_grants)} грантов", "SUCCESS")
    return success

# ==================== ОБРАБОТЧИКИ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"/start от user_id={user_id}, ADMIN_ID={ADMIN_ID}")
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text("⏳ Запуск парсера...")
    
    try:
        success = run_parser()
        if success:
            await update.message.reply_text("✅ Готово! Проверь чат.")
        else:
            await update.message.reply_text("⚠️ Ошибка при отправке")
    except Exception as e:
        logger.error(f"Parser error: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

# ==================== ЗАПУСК ====================
def main():
    logger.info("=== ЗАПУСК БОТА (ПРОСТАЯ ВЕРСИЯ) ===")
    logger.info(f"Token: {TELEGRAM_BOT_TOKEN[:10] if TELEGRAM_BOT_TOKEN else 'NONE'}...")
    logger.info(f"ADMIN_ID: {ADMIN_ID}")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    logger.info("🚀 Start polling...")
    # Простой polling — без сложных обёрток
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
