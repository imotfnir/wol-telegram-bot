import os
import socket
import json
import asyncio
from telegram import BotCommand
from telegram.ext import Application, CommandHandler

UDP_IP = "0.0.0.0"
UDP_PORT = 10000
BROADCAST_IP = "192.168.0.255"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable not set")

mac_table_json = os.getenv("MAC_TABLE")
if mac_table_json:
    MAC_TABLE = json.loads(mac_table_json)
else:
    MAC_TABLE = {}


def send_wol(hostname):
    """Constructs and sends a Wake-on-LAN (WoL) magic packet.

    Args:
        hostname (str): The identifier for the device to wake up. This key
            is used to look up the corresponding MAC address in the MAC_TABLE.
    """
    mac_address = MAC_TABLE[hostname]
    mac_bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))


# slash commands
async def set_bot_commands(application: Application):
    """Sets the bot's command list for the Telegram UI.

    This function is called via `post_init` in the Application builder.

    Args:
        application (Application): The running `telegram.ext.Application` instance.
    """
    commands = [
        BotCommand("start", "開始使用機器人"),
        BotCommand("help", "顯示幫助"),
        BotCommand("wol", "喚醒裝置"),
        BotCommand("status", "查看當前狀態"),
    ]
    await application.bot.set_my_commands(commands)


async def start(update, context):
    """Handles the /start command and sends a welcome message."""
    await update.message.reply_text(
        "Please enter the name of the device to be woken up, for example: /wol mypc\nCurrently supported are rigel, dell, paul"
    )


async def wol(update, context):
    """Handles the /wol command to wake up a device.

    It expects one argument: the hostname of the device to wake up.
    It replies with a confirmation or an error message.
    """
    if not context.args:
        await update.message.reply_text(
            "Please enter the name of the device to be woken up, for example: /wol dell"
        )
        return

    hostname = context.args[0].lower()

    if hostname not in MAC_TABLE:
        await update.message.reply_text(
            f"Device {hostname} not found, please make sure the name is correct!"
        )
        return

    send_wol(hostname)
    await update.message.reply_text(f"Sending WOL to {MAC_TABLE[hostname]}")
    return


app = Application.builder().token(TOKEN).post_init(set_bot_commands).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))


if __name__ == "__main__":
    app.run_polling()
