#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sources.py — получение данных из всех источников.
Чтобы добавить новый источник — добавь функцию и вызови её в get_all_grants().
"""
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict

import requests

from config import RSS_SOURCES, TG_CHANNELS, RSSHUB_INSTANCES, GRANT_KEYWORDS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}


# ─── Утилиты ──────────────────────────────────────────────────────────────────

def is_grant_related(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in GRANT_KEYWORDS)


def parse_rss_url(url: str, source_name: str) -> List[Dict]:
    """Универсальный парсер RSS/Atom лент."""
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        channel = root.find("channel")
        entries = (
            channel.findall("item") if channel is not None
            else root.findall("atom:entry", ns)
        )

        for entry in entries:
            def get(tag, ns_tag=None):
                el = entry.find(tag)
                if el is None and ns_tag:
                    el = entry.find(ns_tag, ns)
                return el.text.strip() if el is not None and el.text else ""

            title    = get("title", "atom:title")
            link_el  = entry.find("link")
            link     = (
                link_el.text or link_el.get("href", "")
                if link_el is not None else ""
            ).strip()
            desc     = get("description") or get("atom:summary", "atom:summary")
            pub_date = get("pubDate") or get("atom:published", "atom:published")

            if not title:
                continue

            full_text = f"{title} {desc}"
            if not is_grant_related(full_text):
                continue

            items.append({
                "title":     title,
                "source":    source_name,
                "link":      link,
                "desc":      desc[:500] if desc else "",
                "pub_date":  pub_date[:25] if pub_date else "",
                "full_text": full_text,
            })

    except requests.exceptions.Timeout:
        logger.warning(f"  {source_name}: таймаут")
    except requests.exceptions.ConnectionError:
        logger.warning(f"  {source_name}: нет соединения")
    except ET.ParseError as e:
        logger.warning(f"  {source_name}: ошибка XML — {e}")
    except Exception as e:
        logger.warning(f"  {source_name}: {e}")

    return items


# ─── Источник 1: RSS ──────────────────────────────────────────────────────────

def fetch_rss_sources() -> List[Dict]:
    """Парсинг всех RSS источников из config.RSS_SOURCES."""
    all_items = []
    for src in RSS_SOURCES:
        if not src.get("enabled", True):
            continue
        logger.info(f"  RSS: {src['name']} ...")
        items = parse_rss_url(src["url"], src["name"])
        logger.info(f"       найдено {len(items)} грантов")
        all_items.extend(items)
    return all_items


# ─── Источник 2: Telegram-каналы через RSSHub ────────────────────────────────

def fetch_telegram_channels() -> List[Dict]:
    """
    Мониторинг Telegram-каналов через RSSHub без API ключей.
    RSSHub конвертирует публичные каналы в RSS.
    """
    all_items = []
    for ch in TG_CHANNELS:
        if not ch.get("enabled", True):
            continue
        logger.info(f"  TG канал: {ch['name']} ...")

        # Пробуем разные инстансы RSSHub
        fetched = False
        for instance in RSSHUB_INSTANCES:
            url = f"{instance}/telegram/channel/{ch['username']}"
            items = parse_rss_url(url, ch["name"])
            if items:
                logger.info(f"       найдено {len(items)} через {instance}")
                all_items.extend(items)
                fetched = True
                break

        if not fetched:
            logger.warning(f"       {ch['name']}: все инстансы недоступны")

    return all_items


# ─── Источник 3: Приоритет-2030 (веб-скрейпинг) ──────────────────────────────

def fetch_priority2030() -> List[Dict]:
    """
    Парсинг priority2030.ru — программа развития университетов.
    Пробуем RSS, если нет — базовый веб-скрейпинг.
    """
    items = []
    urls_to_try = [
        ("RSS",  "https://priority2030.ru/rss"),
        ("News", "https://priority2030.ru/news"),
    ]

    for label, url in urls_to_try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            # Пробуем как RSS
            try:
                root = ET.fromstring(resp.content)
                parsed = parse_rss_url(url, "Приоритет-2030")
                if parsed:
                    logger.info(f"  Приоритет-2030 ({label}): {len(parsed)} грантов")
                    return parsed
            except ET.ParseError:
                pass

            # Если RSS не вышло — ищем ключевые слова в HTML
            text = resp.text.lower()
            if any(kw in text for kw in GRANT_KEYWORDS):
                items.append({
                    "title":     "Приоритет-2030: новые материалы на сайте",
                    "source":    "Приоритет-2030",
                    "link":      url,
                    "desc":      "Проверьте сайт на наличие новых конкурсов",
                    "pub_date":  "",
                    "full_text": text[:1000],
                })
                logger.info(f"  Приоритет-2030: найдены ключевые слова на странице")
                return items

        except Exception as e:
            logger.warning(f"  Приоритет-2030 ({label}): {e}")

    return items


# ─── Источник 4: Региональные фонды ──────────────────────────────────────────

def fetch_regional_funds() -> List[Dict]:
    """
    Региональные фонды поддержки инноваций.
    Сейчас: базовый мониторинг доступности.
    Расширяй этот список по мере необходимости.
    """
    regional_sources = [
        {
            "name": "Фонд Сколково",
            "url":  "https://sk.ru/news/rss/",
        },
        {
            "name": "РВК (Росвенчур)",
            "url":  "https://www.rvc.ru/rss/",
        },
        # Добавляй региональные фонды сюда:
        # {"name": "Фонд Москвы", "url": "https://..."},
    ]

    all_items = []
    for src in regional_sources:
        logger.info(f"  Регион: {src['name']} ...")
        items = parse_rss_url(src["url"], src["name"])
        logger.info(f"       найдено {len(items)}")
        all_items.extend(items)
    return all_items


# ─── Главная функция ──────────────────────────────────────────────────────────

def get_all_grants() -> List[Dict]:
    """
    Собирает гранты из всех источников.
    Чтобы добавить новый источник — вызови его функцию здесь.
    """
    logger.info("=== Сбор данных из источников ===")
    all_items = []

    # 1. RSS источники
    rss = fetch_rss_sources()
    logger.info(f"RSS итого: {len(rss)}")
    all_items.extend(rss)

    # 2. Telegram-каналы
    tg = fetch_telegram_channels()
    logger.info(f"Telegram итого: {len(tg)}")
    all_items.extend(tg)

    # 3. Приоритет-2030
    p2030 = fetch_priority2030()
    logger.info(f"Приоритет-2030 итого: {len(p2030)}")
    all_items.extend(p2030)

    # 4. Региональные фонды
    regional = fetch_regional_funds()
    logger.info(f"Региональные итого: {len(regional)}")
    all_items.extend(regional)

    logger.info(f"=== Всего собрано: {len(all_items)} ===")
    return all_items
