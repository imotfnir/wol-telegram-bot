import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

UDP_IP = "0.0.0.0"
UDP_PORT = 10000
BROADCAST_IP = "192.168.0.255"

MAC_TABLE = {
    "rigel": "04:D9:F5:F3:D0:67",
    "dell": "00:D4:9E:9B:1E:A5",
    "paul": "60:45:CB:9D:AC:6B",
    "paullt": "A0:80:69:F7:1E:1C"
}

TOKEN = "7830008810:AAGeink0jwQ5XZoRpS4DoLe7eIgAYePo9aU"
app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Please enter the name of the device to be woken up, for example: /wol mypc\nCurrently supported are rigel, dell, paul")

async def wol(update: Update, context):
    if not context.args:
        await update.message.reply_text("Please enter the name of the device to be woken up, for example: /wol dell")
        return

    device_name = context.args[0].lower()

    if device_name not in MAC_TABLE:
        await update.message.reply_text(f"Device {device_name} not found, please make sure the name is correct!")
        return

    mac_address = MAC_TABLE[device_name]
    os.system("wakeonlan -i {} {}".format(BROADCAST_IP, mac_address))
    await update.message.reply_text(f"Sending WOL to {mac_address}")
    return


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))

app.run_polling()

