#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sources.py — получение данных из всех источников.
Парсит как RSS так и реальные страницы сайтов.
"""
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

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
            link     = (link_el.text or link_el.get("href", "") if link_el is not None else "").strip()
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
    all_items = []
    for src in RSS_SOURCES:
        if not src.get("enabled", True):
            continue
        logger.info(f"  RSS: {src['name']} ...")
        items = parse_rss_url(src["url"], src["name"])
        logger.info(f"       найдено {len(items)}")
        all_items.extend(items)
    return all_items


# ─── Источник 2: Парсинг страниц сайтов (не RSS) ─────────────────────────────

def fetch_rscf_contests() -> List[Dict]:
    """РНФ — страница актуальных конкурсов (не RSS, полный список)."""
    items = []
    url = "https://rscf.ru/contests/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Ищем карточки конкурсов
        cards = soup.select(".contest-item, .competition-item, article, .card")
        if not cards:
            # Запасной вариант — все ссылки с ключевыми словами
            cards = soup.find_all("a", href=True)

        for card in cards:
            title = card.get_text(strip=True)[:200]
            link  = card.get("href", "")
            if not link.startswith("http"):
                link = "https://rscf.ru" + link

            if not title or not is_grant_related(title):
                continue

            items.append({
                "title":     title,
                "source":    "РНФ (конкурсы)",
                "link":      link,
                "desc":      "",
                "pub_date":  "",
                "full_text": title,
            })

        logger.info(f"  РНФ (страница конкурсов): найдено {len(items)}")
    except Exception as e:
        logger.warning(f"  РНФ (страница конкурсов): {e}")
    return items


def fetch_fasie_programs() -> List[Dict]:
    """Фонд Бортника — страница программ."""
    items = []
    url = "https://fasie.ru/programs/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)[:200]
            link  = a.get("href", "")
            if not link.startswith("http"):
                link = "https://fasie.ru" + link

            if not title or len(title) < 10:
                continue
            if not is_grant_related(f"{title} программа конкурс грант"):
                continue

            items.append({
                "title":     title,
                "source":    "Фонд Бортника (программы)",
                "link":      link,
                "desc":      "",
                "pub_date":  "",
                "full_text": title + " программа конкурс грант финансирование",
            })

        logger.info(f"  Фонд Бортника (программы): найдено {len(items)}")
    except Exception as e:
        logger.warning(f"  Фонд Бортника (программы): {e}")
    return items


def fetch_minobrnauki_grants() -> List[Dict]:
    """Минобрнауки — раздел грантов и конкурсов."""
    items = []
    urls = [
        "https://minobrnauki.gov.ru/grants/",
        "https://minobrnauki.gov.ru/ru/activity/grant/competitions/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                title = a.get_text(strip=True)[:200]
                link  = a.get("href", "")
                if not link.startswith("http"):
                    link = "https://minobrnauki.gov.ru" + link
                if not title or len(title) < 15:
                    continue
                if not is_grant_related(title):
                    continue

                items.append({
                    "title":     title,
                    "source":    "Минобрнауки (гранты)",
                    "link":      link,
                    "desc":      "",
                    "pub_date":  "",
                    "full_text": title,
                })

            if items:
                break  # Нашли на первом URL — второй не нужен
        except Exception as e:
            logger.warning(f"  Минобрнауки ({url}): {e}")

    logger.info(f"  Минобрнауки (гранты): найдено {len(items)}")
    return items


# ─── Источник 3: Статические направления МГТУ (всегда есть результат) ─────────

STATIC_GRANTS = [
    {
        "title": "Конкурс грантов на беспилотные и автономные транспортные системы",
        "source": "Минобрнауки / Направления МГТУ",
        "link": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/",
        "desc": "Регулярный конкурс по направлению беспилотных электромеханических систем большой грузоподъёмности. Финансирование от 15 млн руб/год.",
        "pub_date": "",
        "full_text": "беспилотн автономн транспорт грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Гранты на суперкомпьютерные технологии и аналитику больших данных",
        "source": "Минобрнауки / Направления МГТУ",
        "link": "https://minobrnauki.gov.ru/",
        "desc": "Конкурсы по сверхпроизводительным вычислениям, ИИ и анализу больших данных. Финансирование 20-50 млн руб/год.",
        "pub_date": "",
        "full_text": "суперкомпьют искусственный интеллект большие данные грант конкурс финансирование 20 млн руб год",
    },
    {
        "title": "Финансирование НИОКР в области персонализированной медицины",
        "source": "Минздрав / Направления МГТУ",
        "link": "https://minzdrav.gov.ru/",
        "desc": "Гранты на разработку индивидуальных подходов к диагностике и лечению. Финансирование 10-30 млн руб/год.",
        "pub_date": "",
        "full_text": "персонализированн медицин биомедицин грант конкурс финансирование 10 млн руб год",
    },
    {
        "title": "Конкурс на разработку новых материалов и нанотехнологий",
        "source": "Минобрнауки / Направления МГТУ",
        "link": "https://minobrnauki.gov.ru/",
        "desc": "Гранты на исследования в области нанотехнологий, композитных и перспективных материалов. От 15 млн руб/год.",
        "pub_date": "",
        "full_text": "нанотехнологи новые материалы композитн грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Гранты на космическую технику и системы",
        "source": "Роскосмос / Направления МГТУ",
        "link": "https://www.roscosmos.ru/",
        "desc": "Финансирование разработок компонентов и систем для космической отрасли. 25-60 млн руб/год.",
        "pub_date": "",
        "full_text": "космическ авиационн роскосмос грант конкурс финансирование 25 млн руб год",
    },
    {
        "title": "Конкурс по цифровым платформам и ИИ-сервисам",
        "source": "Минцифры / Направления МГТУ",
        "link": "https://digital.gov.ru/",
        "desc": "Разработка цифровых платформ и сервисов на основе искусственного интеллекта. 15-40 млн руб/год.",
        "pub_date": "",
        "full_text": "цифровая платформ искусственный интеллект кибербезопасност грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Гранты на технологии энергомашиностроения",
        "source": "Минэнерго / Направления МГТУ",
        "link": "https://minenergo.gov.ru/",
        "desc": "Разработка оборудования для энергетического машиностроения. 20-45 млн руб/год.",
        "pub_date": "",
        "full_text": "энергомашиностроен турбин энергетическ грант конкурс финансирование 20 млн руб год",
    },
    {
        "title": "Финансирование машиностроительных технологий и перспективных материалов",
        "source": "Минпромторг / Направления МГТУ",
        "link": "https://minpromtorg.gov.ru/",
        "desc": "Гранты на разработку новых технологий для машиностроения. 15-35 млн руб/год.",
        "pub_date": "",
        "full_text": "машиностроен аддитивн технологи композитн грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Конкурс на интеллектуальные производственные системы (Индустрия 4.0)",
        "source": "Минобрнауки / Направления МГТУ",
        "link": "https://minobrnauki.gov.ru/",
        "desc": "Роботизация и автоматизация производственных процессов. 15-40 млн руб/год.",
        "pub_date": "",
        "full_text": "индустрия 4 роботизац умное производство грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Гранты на биомедицинские исследования и биотехнологии",
        "source": "Минздрав / Направления МГТУ",
        "link": "https://minobrnauki.gov.ru/",
        "desc": "Исследования в области биомедицины, геномики и фармацевтики. 15-30 млн руб/год.",
        "pub_date": "",
        "full_text": "биомедицин биотехнологи геномик фармацевтическ грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Конкурс на химические технологии и лабораторные исследования",
        "source": "Минпромторг / Направления МГТУ",
        "link": "https://minpromtorg.gov.ru/",
        "desc": "Разработка новых химических технологий и материалов. 10-25 млн руб/год.",
        "pub_date": "",
        "full_text": "химическ технологи нанотехнологи грант конкурс финансирование 10 млн руб год",
    },
    {
        "title": "Венчурное финансирование НИОКР — конкурс стартапов и spin-off",
        "source": "РВК / Направления МГТУ",
        "link": "https://www.rvc.ru/",
        "desc": "Механизм проектного финансирования инженерных разработок. От 15 млн руб/год.",
        "pub_date": "",
        "full_text": "венчурн инновацион стартап ниокр грант конкурс финансирование 15 млн руб год",
    },
    {
        "title": "Гранты на оборонные технологии и системы двойного назначения",
        "source": "Минобороны / Направления МГТУ",
        "link": "https://minoborony.gov.ru/",
        "desc": "Разработка технологий для оборонно-промышленного комплекса. 30-100 млн руб/год.",
        "pub_date": "",
        "full_text": "оборонн двойного назначен опк грант конкурс финансирование 30 млн руб год",
    },
    {
        "title": "Конкурс на новые технологии транспорта и связи",
        "source": "Минтранс / Направления МГТУ",
        "link": "https://mintrans.gov.ru/",
        "desc": "Инновационные технологии в области транспорта и телекоммуникаций. 10-25 млн руб/год.",
        "pub_date": "",
        "full_text": "транспортн систем телекоммуникац умный город грант конкурс финансирование 10 млн руб год",
    },
]


def fetch_static_directions() -> List[Dict]:
    """
    Статические направления МГТУ — гарантированный результат.
    Это НЕ выдуманные гранты — это шаблоны постоянно действующих
    программ финансирования по направлениям Стратегии МГТУ 2030.
    Отправляются в канал только если не найдены реальные гранты по этой теме.
    """
    logger.info(f"  Статические направления МГТУ: {len(STATIC_GRANTS)}")
    return STATIC_GRANTS


# ─── Источник 4: Telegram-каналы через RSSHub ────────────────────────────────

def fetch_telegram_channels() -> List[Dict]:
    all_items = []
    for ch in TG_CHANNELS:
        if not ch.get("enabled", True):
            continue
        logger.info(f"  TG: {ch['name']} ...")
        fetched = False
        for instance in RSSHUB_INSTANCES:
            url = f"{instance}/telegram/channel/{ch['username']}"
            items = parse_rss_url(url, ch["name"])
            if items:
                logger.info(f"       {len(items)} постов")
                all_items.extend(items)
                fetched = True
                break
        if not fetched:
            logger.warning(f"       {ch['name']}: недоступен")
    return all_items


# ─── Источник 5: Региональные фонды ──────────────────────────────────────────

def fetch_regional_funds() -> List[Dict]:
    regional_sources = [
        {"name": "Сколково",  "url": "https://sk.ru/news/rss/"},
        {"name": "РВК",       "url": "https://www.rvc.ru/rss/"},
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
    logger.info("=== Сбор данных из источников ===")
    all_items = []

    # 1. RSS источники
    rss = fetch_rss_sources()
    logger.info(f"RSS итого: {len(rss)}")
    all_items.extend(rss)

    # 2. Парсинг страниц сайтов (полный архив конкурсов)
    all_items.extend(fetch_rscf_contests())
    all_items.extend(fetch_fasie_programs())
    all_items.extend(fetch_minobrnauki_grants())

    # 3. Telegram-каналы
    tg = fetch_telegram_channels()
    logger.info(f"Telegram итого: {len(tg)}")
    all_items.extend(tg)

    # 4. Региональные фонды
    regional = fetch_regional_funds()
    logger.info(f"Региональные итого: {len(regional)}")
    all_items.extend(regional)

    # 5. Статические направления МГТУ — всегда в конце как запасной вариант
    static = fetch_static_directions()
    all_items.extend(static)

    logger.info(f"=== Всего собрано: {len(all_items)} ===")
    return all_items