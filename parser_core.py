# parser_core.py
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import config
import storage
from sources import get_static_grants_list, get_enabled_url_sources

# ==================== УТИЛИТЫ ====================

def log_message(message: str, level: str = "INFO"):
    """Логирование сообщений в консоль"""
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
    """Создание уникального хеша для гранта (для проверки дублей)"""
    grant_text = f"{grant['title']}_{grant.get('organizer', '')}_{grant.get('amount', '')}"
    return hashlib.md5(grant_text.encode('utf-8')).hexdigest()

def calculate_rating(grant: Dict[str, Any]) -> int:
    """Расчет рейтинга гранта (1-5 звезд)"""
    rating = 0
    # Критерий 1: Сумма финансирования
    annual_amount = grant.get('annual_amount_min', 0)
    if annual_amount >= 30_000_000:
        rating += 2
    elif annual_amount >= 15_000_000:
        rating += 1.5
    elif annual_amount >= 5_000_000:
        rating += 1
    
    # Критерий 2: Срок подачи (если известен)
    deadline_days = grant.get('deadline_days', -1)
    if deadline_days >= 30:
        rating += 1.5
    elif deadline_days >= 14:
        rating += 1
    
    # Критерий 3: Соответствие направлениям МГТУ
    direction = grant.get('direction', '')
    if any(d.lower() in direction.lower() for d in config.MGTU_DIRECTIONS):
        rating += 1.5
    
    return min(5, int(rating))

def filter_grants(grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Фильтрация грантов по критериям (сумма, сроки)"""
    filtered = []
    for grant in grants:
        # Проверка минимальной суммы
        if grant.get('annual_amount_min', 0) < config.MIN_ANNUAL_AMOUNT:
            continue
        
        # Проверка срока (если указан)
        deadline_days = grant.get('deadline_days', -1)
        if deadline_days != -1 and deadline_days < config.MIN_DEADLINE_DAYS:
            continue
            
        filtered.append(grant)
    
    log_message(f"Отфильтровано {len(filtered)} грантов из {len(grants)}", "INFO")
    return filtered

# ==================== СБОР ГРАНТОВ ====================

def get_static_grants() -> List[Dict[str, Any]]:
    """Получение статических грантов из модуля sources"""
    all_grants = []
    log_message("Загружаем статические гранты из Стратегии МГТУ 2030...", "INFO")
    
    for grant_data in get_static_grants_list():
        grant = {
            'title': grant_data['title'],
            'organizer': grant_data['organizer'],
            'amount': grant_data['amount'],
            'annual_amount_min': grant_data['annual_amount_min'],
            'description': grant_data['description'],
            'direction': grant_data['direction'],
            'source': 'Стратегия 2030',
            'details_url': grant_data['details_url'],
            'deadline_info': grant_data.get('deadline_info', 'Уточняется'),
            'deadline_days': -1,  # Неизвестно для статических
            'open_date': 'Регулярно',
            'close_date': 'Уточняется',
            'project_duration': grant_data.get('project_duration', 'Уточняется'),
            'special_requirements': grant_data.get('special_requirements', 'Стандартные'),
            'eligible_participants': grant_data.get('eligible_participants', 'Все организации'),
            'date_parsed': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'type': 'static'
        }
        # Рассчитываем рейтинг
        grant['rating'] = calculate_rating(grant)
        all_grants.append(grant)
    
    log_message(f"Загружено {len(all_grants)} статических грантов", "SUCCESS")
    return all_grants

def get_all_grants() -> List[Dict[str, Any]]:
    """Сбор всех грантов (статические + парсинг сайтов)"""
    all_grants = []
    
    # 1. Добавляем статические гранты
    all_grants.extend(get_static_grants())
    
    # 2. Здесь в будущем будет парсинг сайтов (URL)
    # all_grants.extend(parse_url_grants())
    
    # Сортируем по рейтингу и сумме
    all_grants.sort(key=lambda x: (x.get('rating', 0), x.get('annual_amount_min', 0)), reverse=True)
    
    return all_grants

# ==================== ОБРАБОТКА НОВЫХ ГРАНТОВ ====================

def process_new_grants() -> List[Dict[str, Any]]:
    """
    Основная функция: собирает гранты, фильтрует дубли, сохраняет новые.
    Возвращает список новых грантов для отправки.
    """
    log_message("=" * 60, "INFO")
    log_message("ЗАПУСК ПАРСЕРА ГРАНТОВ ДЛЯ МГТУ", "INFO")
    log_message("=" * 60, "INFO")
    
    # 1. Собираем все гранты
    all_grants = get_all_grants()
    
    # 2. Фильтруем по критериям (сумма, сроки)
    filtered_grants = filter_grants(all_grants)
    
    # 3. Отбираем только новые (через базу данных)
    new_grants = []
    for grant in filtered_grants:
        if not storage.is_grant_sent(grant):
            new_grants.append(grant)
            storage.save_grant(grant)
            log_message(f"Новый грант: {grant['title'][:50]}...", "SUCCESS")
        else:
            log_message(f"Пропускаем (уже был): {grant['title'][:50]}...", "DEBUG")
    
    # 4. Сохраняем лог запуска
    storage.save_run_log(len(new_grants), "SUCCESS" if new_grants else "NO_NEW")
    
    log_message("=" * 60, "INFO")
    log_message(f"НАЙДЕНО {len(new_grants)} НОВЫХ ГРАНТОВ!", "SUCCESS")
    log_message("=" * 60, "INFO")
    
    return new_grants

# ==================== ФОРМАТИРОВАНИЕ ====================

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
        
        if grant.get('open_date') and grant['open_date'] != 'Регулярно':
            message += f"📅 <b>Открытие:</b> {grant['open_date']}\n"
        if grant.get('close_date') and grant['close_date'] != 'Уточняется':
            message += f"⏰ <b>Закрытие:</b> {grant['close_date']}\n"
            
        message += f"📝 <b>Описание:</b> {grant['description'][:150]}...\n"
        message += f"⏳ <b>Срок реализации:</b> {grant.get('project_duration', 'Уточняется')}\n"
        
        if grant.get('special_requirements'):
            message += f"⚡ <b>Требования:</b> {grant['special_requirements'][:100]}\n"
        if grant.get('eligible_participants'):
            message += f"👥 <b>Участники:</b> {grant['eligible_participants'][:100]}\n"
            
        message += f"🔗 <b>Ссылка:</b> {grant['details_url']}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "🤖 <i>Автоматический парсер грантов МГТУ</i>\n"
    message += "📧 <i>Вопросы: Центр 'Моя наука'</i>"
    
    return message

def format_stats_message() -> str:
    """Форматирование сообщения со статистикой"""
    stats = storage.get_stats()
    
    message = "📊 <b>СТАТИСТИКА ПАРСЕРА</b>\n\n"
    message += f"📁 <b>Всего грантов в базе:</b> {stats['total_grants']}\n"
    message += f"🕒 <b>Последний запуск:</b> {stats['last_run_date']}\n"
    message += f"🔍 <b>Найдено в последний раз:</b> {stats['last_run_found']}\n"
    message += f"✅ <b>Статус:</b> {stats['last_run_status']}\n\n"
    message += "🤖 <i>Бот готов к работе</i>"
    
    return message