#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mgtu_parser.py — фильтрация грантов по критериям МГТУ.
Определяет направления, извлекает суммы, считает рейтинг.
"""
import re
import logging
from typing import List, Dict, Optional

from config import MGTU_DIRECTIONS, DEFAULT_MIN_AMOUNT, DEFAULT_MIN_DAYS

logger = logging.getLogger(__name__)


# ─── Извлечение суммы из текста ───────────────────────────────────────────────

def extract_amount(text: str) -> Optional[int]:
    """Ищет сумму финансирования в тексте."""
    t = text.lower()

    # Миллиарды
    for m in re.findall(r"(\d[\d\s]*[,.]?\d*)\s*млрд", t):
        try:
            return int(float(m.replace(",", ".").replace(" ", "")) * 1_000_000_000)
        except ValueError:
            continue

    # Диапазон: "10-30 млн"
    for m in re.findall(r"(\d+)\s*[-–]\s*\d+\s*млн", t):
        try:
            return int(m) * 1_000_000
        except ValueError:
            continue

    # Миллионы
    for m in re.findall(r"(\d[\d\s]*[,.]?\d*)\s*млн", t):
        try:
            return int(float(m.replace(",", ".").replace(" ", "")) * 1_000_000)
        except ValueError:
            continue

    # Просто большое число (от 1 млн)
    for m in re.findall(r"(\d{7,})", t.replace(" ", "")):
        try:
            val = int(m)
            if val >= 1_000_000:
                return val
        except ValueError:
            continue

    return None


# ─── Определение направлений МГТУ ─────────────────────────────────────────────

def detect_directions(text: str) -> List[str]:
    """Определяет какие направления МГТУ затрагивает грант."""
    t = text.lower()
    found = []
    for direction, keywords in MGTU_DIRECTIONS.items():
        if any(kw in t for kw in keywords):
            found.append(direction)
    return found if found else ["Общие научные исследования"]


# ─── Расчёт рейтинга ──────────────────────────────────────────────────────────

def calculate_rating(amount: Optional[int], directions: List[str]) -> int:
    """Рейтинг от 1 до 5 звёзд."""
    rating = 2  # базовый

    # По сумме
    if amount:
        if amount >= 30_000_000:
            rating += 2
        elif amount >= 15_000_000:
            rating += 1.5
        elif amount >= 5_000_000:
            rating += 1

    # По релевантности направлениям
    if directions and directions != ["Общие научные исследования"]:
        rating += 0.5

    return min(5, int(rating))


# ─── Форматирование суммы для отображения ─────────────────────────────────────

def format_amount(amount: Optional[int]) -> str:
    if not amount:
        return "Уточняется"
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.1f} млрд руб."
    if amount >= 1_000_000:
        return f"{amount // 1_000_000} млн руб."
    return f"{amount:,} руб."


# ─── Фильтрация и обогащение грантов ─────────────────────────────────────────

def process_grants(raw_grants: List[Dict], settings: dict) -> List[Dict]:
    """
    Обрабатывает сырые данные из источников:
    - Извлекает суммы
    - Определяет направления МГТУ
    - Считает рейтинг
    - Фильтрует по минимальной сумме
    """
    min_amount = settings.get("min_amount", DEFAULT_MIN_AMOUNT)
    processed = []

    for raw in raw_grants:
        full_text = raw.get("full_text", f"{raw.get('title','')} {raw.get('desc','')}")

        # Извлекаем сумму
        amount = extract_amount(full_text)

        # Если сумма найдена и ниже порога — пропускаем
        if amount is not None and amount < min_amount:
            continue

        # Определяем направления
        directions = detect_directions(full_text)

        # Рейтинг
        rating = calculate_rating(amount, directions)

        processed.append({
            "title":       raw.get("title", "Без названия"),
            "source":      raw.get("source", ""),
            "organizer":   raw.get("source", ""),
            "link":        raw.get("link", ""),
            "details_url": raw.get("link", ""),
            "desc":        raw.get("desc", ""),
            "description": raw.get("desc", ""),
            "pub_date":    raw.get("pub_date", ""),
            "deadline_info": raw.get("pub_date", ""),
            "amount":      format_amount(amount),
            "annual_amount_min": amount or 0,
            "directions":  directions,
            "direction":   ", ".join(directions),
            "rating":      rating,
            "project_duration": "Уточняется",
        })

    # Сортировка: сначала по рейтингу, потом по сумме
    processed.sort(
        key=lambda x: (x["rating"], x["annual_amount_min"]),
        reverse=True
    )

    logger.info(f"После фильтрации: {len(processed)} из {len(raw_grants)}")
    return processed
