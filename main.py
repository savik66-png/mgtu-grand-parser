# main.py
"""
TELEGRAM БОТ ДЛЯ ПАРСЕРА ГРАНТОВ МГТУ
Запуск через вебхук на BotHost
"""
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
import storage
import parser_core

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard():
    """Основное меню бота"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить гранты", callback_data="check_grants")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton("📥 Скачать отчет CSV", callback_data="download_csv"),
         InlineKeyboardButton("📥 Скачать отчет HTML", callback_data="download_html")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user_id = update.effective_user.id
    
    # Проверка прав доступа
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text(
            "❌ <b>Доступ запрещен</b>\n\n"
            "У вас нет прав на использование этого бота.",
            parse_mode='HTML'
        )
        return
    
    welcome_text = (
        f"👋 <b>Привет, {update.effective_user.first_name}!</b>\n\n"
        "🤖 <b>Бот парсер грантов МГТУ им. Баумана</b>\n\n"
        "Я помогаю мониторить научные гранты и конкурсы.\n\n"
        "<b>Что я умею:</b>\n"
        "✅ Проверять новые гранты по кнопке\n"
        "✅ Фильтровать по сумме (от 5 млн руб./год)\n"
        "✅ Сохранять отчеты в CSV и HTML\n\n"
        "Выберите действие в меню ниже 👇"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = (
        "📚 <b>СПРАВКА ПО БОТУ</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/stats - Показать статистику\n"
        "/help - Эта справка\n\n"
        "<b>Критерии отбора:</b>\n"
        "💰 Мин. сумма: 5 млн руб./год\n"
        "⏰ Мин. срок: 14 дней на подготовку"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    action = query.data
    
    # 🔍 ПРОВЕРКА ГРАНТОВ
    if action == "check_grants":
        await query.edit_message_text(
            "⏳ <b>Запуск парсера...</b>\n\nПожалуйста, подождите.",
            parse_mode='HTML'
        )
        
        try:
            new_grants = parser_core.process_new_grants()
            
            if new_grants:
                message = parser_core.format_telegram_message(new_grants)
                # Исправленный вызов функции отправки
                await send_long_message(context.bot, query.message.chat_id, message)
                
                # Генерируем отчеты
                parser_core.save_csv_report(new_grants)
                parser_core.save_html_report(new_grants)
                
                await query.message.reply_text(
                    f"✅ <b>Готово!</b>\nНайдено: {len(new_grants)} грантов",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            else:
                await query.message.reply_text(
                    "ℹ️ <b>Новых грантов не найдено</b>",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await query.message.reply_text(
                f"❌ <b>Ошибка:</b> {str(e)[:100]}",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
    
    # 📊 СТАТИСТИКА
    elif action == "show_stats":
        stats_message = parser_core.format_stats_message()
        await query.edit_message_text(
            stats_message,
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    
    # 📥 СКАЧАТЬ ОТЧЕТЫ
    elif action == "download_csv":
        file_path = config.CSV_REPORT_FILE
        if os.path.exists(file_path):
            await query.message.reply_document(
                document=open(file_path, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.csv",
                caption="📄 CSV отчет"
            )
        else:
            await query.message.reply_text("❌ Отчет не найден. Сначала запустите проверку.")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    elif action == "download_html":
        file_path = config.HTML_REPORT_FILE
        if os.path.exists(file_path):
            await query.message.reply_document(
                document=open(file_path, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.html",
                caption="🌐 HTML отчет"
            )
        else:
            await query.message.reply_text("❌ Отчет не найден. Сначала запустите проверку.")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    # ℹ️ ПОМОЩЬ
    elif action == "help_info":
        await query.edit_message_text(
            "📚 <b>СПРАВКА</b>\n\nБот помогает мониторить гранты для МГТУ.\nКритерии: от 5 млн руб., от 14 дней.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    # ⬅️ НАЗАД
    elif action == "back_menu":
        await query.edit_message_text(
            "📋 <b>ГЛАВНОЕ МЕНЮ</b>",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_long_message(bot, chat_id: int, text: str):
    """Отправка длинного сообщения (разбивка на части)"""
    max_length = 4000
    parts = []
    
    if len(text) <= max_length:
        parts = [text]
    else:
        current_part = ""
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                parts.append(current_part)
                current_part = line
            else:
                current_part += '\n' + line if current_part else line
        if current_part:
            parts.append(current_part)
    
    for part in parts:
        # Исправленный синтаксис вызова
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode='HTML'
        )

# ==================== ЗАПУСК БОТА ====================

def main():
    """Точка входа для запуска бота на BotHost"""
    
    # Инициализация базы данных
    storage.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Создание приложения
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запуск бота (для BotHost через вебхук)
    logger.info("🚀 Запуск бота...")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=config.TELEGRAM_BOT_TOKEN,
        webhook_url=None
    )

if __name__ == "__main__":
    main()
