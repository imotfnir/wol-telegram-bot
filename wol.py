import os
import socket
import json
from telegram.ext import Application, CommandHandler, MessageHandler, filters

UDP_IP = "0.0.0.0"
UDP_PORT = 10000
BROADCAST_IP = "192.168.0.255"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable not set")
app = Application.builder().token(TOKEN).build()
mac_table_json = os.getenv("MAC_TABLE")
if mac_table_json:
    MAC_TABLE = json.loads(mac_table_json)
else:
    MAC_TABLE = {}

def send_wol(hostname):
    mac_address=MAC_TABLE[hostname]
    mac_bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))


async def start(update, context):
    await update.message.reply_text("Please enter the name of the device to be woken up, for example: /wol mypc\nCurrently supported are rigel, dell, paul")


async def wol(update, context):
    if not context.args:
        await update.message.reply_text("Please enter the name of the device to be woken up, for example: /wol dell")
        return

    hostname = context.args[0].lower()

    if hostname not in MAC_TABLE:
        await update.message.reply_text(f"Device {hostname} not found, please make sure the name is correct!")
        return

    send_wol(hostname)
    await update.message.reply_text(f"Sending WOL to {MAC_TABLE[hostname]}")
    return


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))

if __name__ == "__main__":
    app.run_polling()
