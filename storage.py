# storage.py
import sqlite3
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import config

def get_db_path() -> str:
    """Получить путь к файлу базы данных"""
    return os.path.join(config.BASE_DIR, "grants.db")

def init_db():
    """Инициализация базы данных (создание таблиц)"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Таблица отправленных грантов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_grants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grant_hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            organizer TEXT,
            amount TEXT,
            date_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT
        )
    """)
    
    # Таблица логов запусков
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            grants_found INTEGER,
            status TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ База данных инициализирована: {db_path}")

def get_grant_hash(grant: Dict[str, Any]) -> str:
    """Создание уникального хеша для гранта"""
    grant_text = f"{grant['title']}_{grant.get('organizer', '')}_{grant.get('amount', '')}"
    return hashlib.md5(grant_text.encode('utf-8')).hexdigest()

def is_grant_sent(grant: Dict[str, Any]) -> bool:
    """Проверка: отправлялся ли уже этот грант"""
    grant_hash = get_grant_hash(grant)
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sent_grants WHERE grant_hash = ?", (grant_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Ошибка проверки гранта: {e}")
        return False

def save_grant(grant: Dict[str, Any]):
    """Сохранение гранта в историю отправленных"""
    grant_hash = get_grant_hash(grant)
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO sent_grants (grant_hash, title, organizer, amount, source)
            VALUES (?, ?, ?, ?, ?)
        """, (
            grant_hash,
            grant.get('title', ''),
            grant.get('organizer', ''),
            grant.get('amount', ''),
            grant.get('source', '')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка сохранения гранта: {e}")

def save_run_log(grants_found: int, status: str = "SUCCESS"):
    """Сохранение лога запуска парсера"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO run_logs (grants_found, status)
            VALUES (?, ?)
        """, (grants_found, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка сохранения лога: {e}")

def get_stats() -> Dict[str, Any]:
    """Получение статистики по базе"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Всего отправленных грантов
        cursor.execute("SELECT COUNT(*) FROM sent_grants")
        total_grants = cursor.fetchone()[0]
        
        # Последний запуск
        cursor.execute("SELECT run_date, grants_found, status FROM run_logs ORDER BY id DESC LIMIT 1")
        last_run = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_grants": total_grants,
            "last_run_date": last_run[0] if last_run else "Никогда",
            "last_run_found": last_run[1] if last_run else 0,
            "last_run_status": last_run[2] if last_run else "N/A"
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {"total_grants": 0, "last_run_date": "Ошибка", "last_run_found": 0, "last_run_status": "Ошибка"}

def clear_history():
    """Очистка истории (для тестов)"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sent_grants")
        cursor.execute("DELETE FROM run_logs")
        conn.commit()
        conn.close()
        print("✅ История очищена")
    except Exception as e:
        print(f"❌ Ошибка очистки истории: {e}")

# Автоинициализация при импорте
if __name__ != "__main__":
    init_db()