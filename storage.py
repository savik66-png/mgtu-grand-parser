#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
storage.py — хранение истории, настроек, HTML отчётов.
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Set

from config import DEFAULT_MIN_AMOUNT, DEFAULT_MIN_DAYS

logger = logging.getLogger(__name__)

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
SENT_GRANTS_FILE = os.path.join(SCRIPT_DIR, "sent_grants.json")
SETTINGS_FILE    = os.path.join(SCRIPT_DIR, "settings.json")
HTML_REPORT_FILE = os.path.join(SCRIPT_DIR, "grants_report.html")


# ─── Настройки ────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    defaults = {"min_amount": DEFAULT_MIN_AMOUNT, "min_days": DEFAULT_MIN_DAYS}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
    return defaults


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")


# ─── История отправленных грантов ─────────────────────────────────────────────

def load_sent_grants() -> Set[str]:
    try:
        if os.path.exists(SENT_GRANTS_FILE):
            with open(SENT_GRANTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"История: {len(data)} записей")
                return set(data)
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
    return set()


def save_sent_grants(sent: Set[str]):
    try:
        with open(SENT_GRANTS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(sent), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения истории: {e}")


def reset_sent_grants():
    """Очистка истории — все гранты будут отправлены заново."""
    try:
        if os.path.exists(SENT_GRANTS_FILE):
            os.remove(SENT_GRANTS_FILE)
            logger.info("История очищена")
            return True
    except Exception as e:
        logger.error(f"Ошибка очистки истории: {e}")
    return False


def grant_hash(title: str, source: str = "") -> str:
    return hashlib.md5(f"{title.strip().lower()}|{source}".encode()).hexdigest()


def filter_new_grants(grants: List[Dict]) -> List[Dict]:
    """Оставляет только гранты которых ещё не было в канале."""
    sent = load_sent_grants()
    new = []
    for g in grants:
        h = grant_hash(g["title"], g.get("source", ""))
        if h not in sent:
            new.append(g)
            sent.add(h)
    save_sent_grants(sent)
    return new


# ─── HTML отчёт ───────────────────────────────────────────────────────────────

def save_html_report(grants: List[Dict], settings: dict):
    try:
        rows = ""
        for i, g in enumerate(grants, 1):
            stars = "⭐" * g.get("rating", 3)
            directions = ", ".join(g.get("directions", [g.get("direction", "")]))
            desc = g.get("description", "")[:200]
            link = g.get("details_url", g.get("link", "#"))
            rows += f"""
            <tr>
                <td>{i}</td>
                <td><b>{g['title']}</b><br><small style="color:#666">{desc}</small></td>
                <td>{g.get('organizer', g.get('source', ''))}</td>
                <td style="color:green;font-weight:bold">{g.get('amount','Уточняется')}</td>
                <td>{directions}</td>
                <td>{g.get('deadline_info','')}</td>
                <td>{stars}</td>
                <td><a href="{link}" target="_blank">→ Открыть</a></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Гранты МГТУ — {datetime.now().strftime('%d.%m.%Y')}</title>
<style>
  body{{font-family:Arial,sans-serif;padding:20px;background:#f0f2f5;margin:0}}
  h1{{background:linear-gradient(135deg,#667eea,#764ba2);color:white;
      padding:25px 30px;border-radius:10px;margin-bottom:10px}}
  .meta{{color:#666;margin-bottom:25px;font-size:0.95em}}
  table{{width:100%;border-collapse:collapse;background:white;
         border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)}}
  th{{background:#667eea;color:white;padding:13px 10px;text-align:left;font-size:0.9em}}
  td{{padding:11px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top;font-size:0.9em}}
  tr:hover{{background:#f9f9ff}}
  a{{color:#667eea;text-decoration:none}}
  a:hover{{text-decoration:underline}}
  .footer{{text-align:center;margin-top:30px;color:#999;font-size:0.85em}}
</style>
</head>
<body>
<h1>🎯 Гранты для МГТУ им. Баумана</h1>
<div class="meta">
  📅 Отчёт: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b> &nbsp;|&nbsp;
  🔍 Найдено: <b>{len(grants)}</b> &nbsp;|&nbsp;
  💰 Порог: <b>от {settings['min_amount']:,} руб/год</b>
</div>
<table>
<tr><th>#</th><th>Название / Описание</th><th>Источник</th>
    <th>Финансирование</th><th>Направления МГТУ</th>
    <th>Срок подачи</th><th>Рейтинг</th><th>Ссылка</th></tr>
{rows}
</table>
<div class="footer">🤖 Автоматический мониторинг грантов МГТУ им. Баумана</div>
</body></html>"""

        with open(HTML_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML отчёт сохранён: {HTML_REPORT_FILE}")
    except Exception as e:
        logger.error(f"Ошибка HTML отчёта: {e}")
