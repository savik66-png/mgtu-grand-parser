# main.py - ФИНАЛЬНАЯ ВЕРСИЯ
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Наши модули
import config
import storage
import parser_core

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL, 'INFO')
)
logger = logging.getLogger(__name__)

print(f"✅ CONFIG LOADED: ADMIN_IDS={config.ADMIN_IDS}")

# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проверить гранты", callback_data="check_grants")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton("📥 Скачать CSV", callback_data="download_csv"),
         InlineKeyboardButton("📥 Скачать HTML", callback_data="download_html")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help_info")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_menu")]])

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔍 /start from user_id={user_id}, ADMIN_IDS={config.ADMIN_IDS}")
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text(
        f"👋 <b>Привет!</b>\n\n"
        f"🤖 <b>Бот грантов МГТУ</b>\n\n"
        f"Нажми «🔍 Проверить гранты» для запуска парсера.",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    action = query.data
    print(f"🔍 Button pressed: {action}")
    
    # 🔍 ПРОВЕРКА ГРАНТОВ
    if action == "check_grants":
        await query.edit_message_text("⏳ <b>Запуск парсера...</b>", parse_mode='HTML')
        
        try:
            # Запускаем парсер из parser_core.py
            new_grants = parser_core.process_new_grants()
            
            if new_grants:
                # Формируем и отправляем сообщение
                message = parser_core.format_telegram_message(new_grants)
                await send_long_message(context.bot, query.message.chat_id, message)
                
                # Генерируем отчеты
                if hasattr(parser_core, 'save_csv_report'):
                    parser_core.save_csv_report(new_grants)
                if hasattr(parser_core, 'save_html_report'):
                    parser_core.save_html_report(new_grants)
                
                await query.message.reply_text(
                    f"✅ <b>Готово!</b>\nНайдено новых грантов: <b>{len(new_grants)}</b>",
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
            logger.error(f"❌ Ошибка парсера: {e}")
            await query.message.reply_text(
                f"❌ <b>Ошибка:</b>\n{str(e)[:200]}",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
    
    # 📊 СТАТИСТИКА
    elif action == "show_stats":
        if hasattr(parser_core, 'format_stats_message'):
            stats = parser_core.format_stats_message()
            await query.edit_message_text(stats, parse_mode='HTML', reply_markup=get_main_keyboard())
        else:
            await query.edit_message_text("📊 Статистика пока недоступна", reply_markup=get_main_keyboard())
    
    # 📥 СКАЧАТЬ ОТЧЕТЫ
    elif action == "download_csv":
        if os.path.exists(config.CSV_REPORT_FILE):
            await query.message.reply_document(
                document=open(config.CSV_REPORT_FILE, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.csv",
                caption="📄 CSV отчет"
            )
        else:
            await query.message.reply_text("❌ Сначала запустите проверку грантов")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    elif action == "download_html":
        if os.path.exists(config.HTML_REPORT_FILE):
            await query.message.reply_document(
                document=open(config.HTML_REPORT_FILE, 'rb'),
                filename=f"grants_{datetime.now().strftime('%d%m')}.html",
                caption="🌐 HTML отчет"
            )
        else:
            await query.message.reply_text("❌ Сначала запустите проверку грантов")
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
    
    # ℹ️ ПОМОЩЬ
    elif action == "help_info":
        await query.edit_message_text(
            "📚 <b>СПРАВКА</b>\n\n"
            "Бот мониторит гранты для МГТУ.\n\n"
            "Критерии:\n"
            "• От 5 млн руб./год\n"
            "• От 14 дней на подготовку\n"
            "• Соответствие Стратегии 2030",
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
    """Отправка длинного сообщения с разбивкой"""
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

# ==================== ЗАПУСК ====================
def main():
    print("🚀 STARTING FINAL BOT WITH POLLING...")
    
    # Инициализация БД
    storage.init_db()
    print("✅ Database initialized")
    
    # Создаём приложение
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Handlers registered. Starting polling...")
    
    # Запускаем polling (это работает на BotHost!)
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    
    print("🛑 Bot stopped")

if __name__ == "__main__":
    main()
