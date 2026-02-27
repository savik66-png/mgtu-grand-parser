# main.py
"""
TELEGRAM БОТ ДЛЯ ПАРСЕРА ГРАНТОВ МГТУ
Запуск через POLLING на BotHost (без вебхука)
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
    level=getattr(logging, config.LOG_LEVEL),
    force=True  # Перезаписываем логи для чистоты
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
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text(
            "❌ <b>Доступ запрещен</b>",
            parse_mode='HTML'
        )
        return
    
    welcome_text = (
        f"👋 <b>Привет, {update.effective_user.first_name}!</b>\n\n"
        "🤖 <b>Бот парсер грантов МГТУ им. Баумана</b>\n\n"
        "Нажми «🔍 Проверить гранты» для запуска."
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = (
        "📚 <b>СПРАВКА</b>\n\n"
        "/start - Главное меню\n"
        "/stats - Статистика\n"
        "\nКритерии: от 5 млн руб., от 14 дней"
    )
    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    action = query.data
    
    if action == "check_grants":
        await query.edit_message_text("⏳ <b>Запуск...</b>", parse_mode='HTML')
        
        try:
            new_grants = parser_core.process_new_grants()
            
            if new_grants:
                message = parser_core.format_telegram_message(new_grants)
                await send_long_message(context.bot, query.message.chat_id, message)
                
                # Генерация отчетов (функции должны быть в parser_core)
                if hasattr(parser_core, 'save_csv_report'):
                    parser_core.save_csv_report(new_grants)
                if hasattr(parser_core, 'save_html_report'):
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
                f"❌ <b>Ошибка:</b> {str(e)[:150]}",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
    
    elif action == "show_stats":
        stats_message = parser_core.format_stats_message()
        await query.edit_message_text(
            stats_message,
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    
    elif action == "download_csv":
        if os.path.exists(config.CSV_REPORT_FILE):
            await query.message.reply_document(
                document=open(config.CSV_REPORT_FILE, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.csv"
            )
        else:
            await query.message.reply_text("❌ Сначала запустите проверку")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    elif action == "download_html":
        if os.path.exists(config.HTML_REPORT_FILE):
            await query.message.reply_document(
                document=open(config.HTML_REPORT_FILE, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.html"
            )
        else:
            await query.reply_text("❌ Сначала запустите проверку")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    elif action == "help_info":
        await query.edit_message_text(
            "📚 <b>СПРАВКА</b>\n\nБот мониторит гранты для МГТУ.\nКритерии: от 5 млн руб., от 14 дней.",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    elif action == "back_menu":
        await query.edit_message_text(
            "📋 <b>ГЛАВНОЕ МЕНЮ</b>",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_long_message(bot, chat_id: int, text: str):
    """Отправка длинного сообщения"""
    max_length = 4000
    parts = []
    
    if len(text) <= max_length:
        parts = [text]
    else:
        current = ""
        for line in text.split('\n'):
            if len(current) + len(line) + 1 > max_length:
                parts.append(current)
                current = line
            else:
                current += '\n' + line if current else line
        if current:
            parts.append(current)
    
    for part in parts:
        await bot.send_message(chat_id=chat_id, text=part, parse_mode='HTML')

# ==================== ЗАПУСК БОТА (POLLING) ====================

def main():
    """Запуск бота в режиме POLLING"""
    
    storage.init_db()
    logger.info("✅ База данных инициализирована")
    
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 Запуск бота в режиме POLLING...")
    
    # ✅ POLLING: бот сам опрашивает Telegram, не нужен вебхук!
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
