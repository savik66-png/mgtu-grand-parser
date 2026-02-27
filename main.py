# main.py - УСТОЙЧИВАЯ ВЕРСИЯ С ЗАЩИТОЙ
import os
import sys
import time
import logging
import traceback
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Наши модули
import config
import storage
import parser_core

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout,  # Важно для хостингов!
    force=True
)
logger = logging.getLogger(__name__)

# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проверить гранты", callback_data="check_grants")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ])

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"🔍 /start от user_id={user_id}, ADMIN_IDS={config.ADMIN_IDS}")
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        await update.message.reply_text(
            "👋 <b>Бот грантов МГТУ</b>\n\nНажми «🔍 Проверить гранты»",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("⚠️ Внутренняя ошибка бота")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in config.ADMIN_IDS:
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        action = query.data
        logger.info(f"🔍 Кнопка: {action}")
        
        if action == "check_grants":
            await query.edit_message_text("⏳ <b>Запуск...</b>", parse_mode='HTML')
            
            # Запускаем парсер
            new_grants = parser_core.process_new_grants()
            
            if new_grants:
                message = parser_core.format_telegram_message(new_grants)
                # Отправляем частями если длинное
                for part in split_message(message):
                    await query.message.reply_text(part, parse_mode='HTML')
                await query.message.reply_text(f"✅ Готово! Найдено: {len(new_grants)}", reply_markup=get_main_keyboard())
            else:
                await query.message.reply_text("ℹ️ Новых грантов не найдено", reply_markup=get_main_keyboard())
                
        elif action == "show_stats":
            stats = storage.get_stats()
            await query.edit_message_text(
                f"📊 <b>Статистика</b>\n\n"
                f"В базе: {stats['total_grants']} грантов\n"
                f"Последний запуск: {stats['last_run_date']}",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
        elif action == "help":
            await query.edit_message_text(
                "📚 <b>Помощь</b>\n\n"
                "Критерии:\n• От 5 млн руб./год\n• От 14 дней на подготовку",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в кнопках: {e}\n{traceback.format_exc()}")
        await query.message.reply_text(f"⚠️ Ошибка: {str(e)[:100]}")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def split_message(text: str, max_len: int = 4000):
    """Разбивает длинный текст на части"""
    if len(text) <= max_len:
        return [text]
    parts = []
    current = ""
    for line in text.split('\n'):
        if len(current) + len(line) + 1 > max_len:
            parts.append(current)
            current = line
        else:
            current += '\n' + line if current else line
    if current:
        parts.append(current)
    return parts

# ==================== ГЛАВНЫЙ ЦИКЛ С ЗАЩИТОЙ ====================
def run_with_restart():
    """Запуск бота с авто-перезапуском при падении"""
    restart_count = 0
    max_restarts = 5
    
    while restart_count < max_restarts:
        try:
            logger.info(f"🚀 Запуск бота (попытка {restart_count + 1})...")
            
            # Инициализация
            storage.init_db()
            logger.info("✅ База данных готова")
            
            # Создаём приложение
            app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(button_handler))
            
            logger.info("✅ Обработчики зарегистрированы")
            
            # Запускаем polling с таймаутом
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                timeout=30  # Важно для хостингов!
            )
            
        except KeyboardInterrupt:
            logger.info("🛑 Остановка по сигналу")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"💥 Бот упал! Ошибка: {e}")
            logger.error(traceback.format_exc())
            
            if restart_count < max_restarts:
                wait_time = 2 ** restart_count  # Экспоненциальная задержка
                logger.info(f"🔄 Перезапуск через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                logger.error("❌ Превышено число перезапусков. Остановка.")
                break

if __name__ == "__main__":
    # Финальная точка входа
    logger.info("=== БОТ ГРАНТОВ МГТУ ЗАПУСКАЕТСЯ ===")
    logger.info(f"📦 Python: {sys.version}")
    logger.info(f"🔑 Token starts with: {config.TELEGRAM_BOT_TOKEN[:10] if config.TELEGRAM_BOT_TOKEN else 'NONE'}...")
    logger.info(f"👤 ADMIN_IDS: {config.ADMIN_IDS}")
    
    run_with_restart()
    
    logger.info("=== БОТ ОСТАНОВЛЕН ===")
