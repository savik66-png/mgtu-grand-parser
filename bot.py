import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s", force=True)

TOKEN = "8097523464:AAE14lgMGIvv11i7_HTqW5yGvA9IUEHyNWg"

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"ПОЛУЧЕНО: {update.message.text} от {update.effective_user.id}")
    await update.message.reply_text(f"Получил: {update.message.text}")

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, echo))
app.run_polling(drop_pending_updates=False)
