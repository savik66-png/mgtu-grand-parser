# sources.py
"""
Модуль с источниками грантов
Здесь хранятся статические гранты и ссылки для парсинга
"""

# ==================== СТАТИЧЕСКИЕ ГРАНТЫ (Стратегия 2030) ====================
STATIC_GRANTS = [
    {
        "title": "Электромеханические беспилотные автомобили большой грузоподъемности",
        "organizer": "Минобрнауки России",
        "amount": "от 15 млн руб./год",
        "annual_amount_min": 15_000_000,
        "description": "Разработка отечественных научных приборов для добывающих отраслей промышленности РФ",
        "direction": "Транспортные системы",
        "details_url": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/",
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
        "deadline_info": "Индивидуально",
        "project_duration": "2-5 лет",
        "special_requirements": "Бизнес-модель, коммерческий потенциал",
        "eligible_participants": "Стартапы и spin-off компании"
    }
]

# ==================== URL ИСТОЧНИКИ ДЛЯ ПАРСИНГА ====================
# В будущем здесь можно добавить функции для парсинга этих сайтов
URL_SOURCES = {
    "minobrnauki": {
        "name": "Минобрнауки России",
        "url": "https://minobrnauki.gov.ru/ru/activity/grant/competitions/",
        "priority": 1,
        "enabled": True
    },
    "rscf": {
        "name": "Российский научный фонд",
        "url": "https://rscf.ru/contests/",
        "priority": 1,
        "enabled": True
    },
    "fasie": {
        "name": "Фонд содействия инновациям",
        "url": "https://fasie.ru/programs/",
        "priority": 2,
        "enabled": True
    },
    "rftr": {
        "name": "Российский фонд технологического развития",
        "url": "https://rftr.ru/",
        "priority": 2,
        "enabled": True
    },
    "grants_ru": {
        "name": "База грантов России",
        "url": "https://grants.ru/grants/",
        "priority": 3,
        "enabled": False  # Пока отключено
    }
}

# ==================== ФУНКЦИИ ДОСТУПА ====================

def get_static_grants_list():
    """Получить список статических грантов"""
    return STATIC_GRANTS

def get_enabled_url_sources():
    """Получить список активных URL источников"""
    return {key: value for key, value in URL_SOURCES.items() if value.get('enabled', False)}

def add_new_grant(grant_data):
    """
    Пример функции для добавления нового гранта в список
    Можно использовать для динамического добавления
    """
    STATIC_GRANTS.append(grant_data)