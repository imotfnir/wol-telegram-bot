from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "7830008810:AAGeink0jwQ5XZoRpS4DoLe7eIgAYePo9aU"
app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Hello! 我是你的 Telegram Bot!")

async def wol(update: Update, context):
    if not context.args:
        await update.message.reply_text("請輸入要喚醒的裝置名稱，例如：/wol mypc")
        return

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))


app.run_polling()

