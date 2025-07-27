import json
import os
import socket
from typing import Dict, List
from scapy.all import ARP, Ether, srp
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

UDP_IP: str = "0.0.0.0"
UDP_PORT: int = 10000
BROADCAST_IP: str = "192.168.0.255"
if (TOKEN := os.getenv("TELEGRAM_BOT_TOKEN")) is None:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable not set")

if (mac_table_json := os.getenv("MAC_TABLE")) is not None:
    MAC_TABLE: Dict[str, str] = json.loads(mac_table_json.lower())
else:
    MAC_TABLE: Dict[str, str] = []


def send_wol(hostname: str) -> None:
    """Constructs and sends a Wake-on-LAN (WoL) magic packet.

    Args:
        hostname (str): The identifier for the device to wake up. This key
            is used to look up the corresponding MAC address in the MAC_TABLE.
    """
    mac_address: str = MAC_TABLE[hostname]
    mac_bytes: bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    magic_packet: bytes = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))

def send_sol(hostname: str) -> None:
    """Constructs and sends a Sleep-on-LAN (SoL) magic packet.

    Args:
        hostname (str): The identifier for the device to wake up. This key
            is used to look up the corresponding MAC address in the MAC_TABLE.
    """
    mac_address: str = MAC_TABLE[hostname]
    mac_bytes: bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))[::-1]
    magic_packet: bytes = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))


# slash commands
async def set_bot_commands(application: Application) -> None:
    """Sets the bot's command list for the Telegram UI.

    This function is called via `post_init` in the Application builder.

    Args:
        application (Application): The running `telegram.ext.Application` instance.
    """
    commands: List[BotCommand] = [
        BotCommand("start", "開始使用機器人"),
        BotCommand("help", "顯示幫助"),
        BotCommand("wol", "喚醒裝置"),
        BotCommand("sol", "哄睡裝置"),
        BotCommand("arp", "列出連線裝置並更新ARP表"),
    ]
    await application.bot.set_my_commands(commands)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and sends a welcome message."""
    await update.message.reply_text(
        "Please enter the name of the device to be woken up\n"
        "for example: /wol mypc\n"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command and sends a help message."""
    await update.message.reply_text(
        "This bot allows you to wake up devices on your network using Wake-on-LAN.\n"
        "Use `/wol <hostname>` to wake up a device. Supported hostnames are:\n"
        + ", ".join(MAC_TABLE.keys())
    )


async def arp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Performs an ARP scan of the local network and returns the results."""
    await update.message.reply_text("Starting ARP scan... This may take a moment.")

    target_ip: str = "192.168.0.1/24"  # TODO: Make this configurable
    arp_packet: ARP = ARP(pdst=target_ip)
    ether_packet: Ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether_packet / arp_packet

    result: List[tuple] = srp(packet, timeout=2, verbose=0)[0]

    clients: List[Dict[str, str]] = []
    for _, received in result:
        clients.append({"ip": received.psrc, "mac": received.hwsrc})

    if not clients:
        await update.message.reply_text("No active devices found on the network.")
        return
    column_width: List[int] = [15, 15, 30]
    response: str = "Active devices on the network:\n"
    response += f"{"Host":<{column_width[0]}}{"IP":<{column_width[1]}}{"MAC":<{column_width[2]}}\n"
    for client in clients:
        hostname: str = next(
            (k for k, v in MAC_TABLE.items() if v == client["mac"]), None
        )
        if client["mac"] in MAC_TABLE.values():
            response += f"{hostname:<{column_width[0]}}{client['ip']:<{column_width[1]}}{client['mac']:<{column_width[2]}}\n"
        else:
            response += f"{"N/A":<{column_width[0]}}{client['ip']:<{column_width[1]}}{client['mac']:<{column_width[2]}}\n"

    await update.message.reply_markdown(f"```\n{response}\n```")


async def wol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /wol command to wake up a device.

    It expects one argument: the hostname of the device to wake up.
    It replies with a confirmation or an error message.
    """
    if not context.args:
        await update.message.reply_text(
            "Please enter the name of the device to be woken up, for example: /wol dell"
        )
        return

    hostname: str = context.args[0].lower()

    if hostname not in MAC_TABLE:
        await update.message.reply_text(
            f"Device {hostname} not found, please make sure the name is correct!"
        )
        return

    send_wol(hostname)
    await update.message.reply_text(f"Sending WOL to {MAC_TABLE[hostname]}")
    return

async def sol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /sol command to sleep a device.

    It expects one argument: the hostname of the device to sleep.
    It replies with a confirmation or an error message.
    """
    if not context.args:
        await update.message.reply_text(
            "Please enter the name of the device to be sleep, for example: /sol dell"
        )
        return

    hostname: str = context.args[0].lower()

    if hostname not in MAC_TABLE:
        await update.message.reply_text(
            f"Device {hostname} not found, please make sure the name is correct!"
        )
        return

    send_sol(hostname)
    await update.message.reply_text(f"Sending SOL to {MAC_TABLE[hostname]}")
    return

app: Application = (
    Application.builder().token(TOKEN).post_init(set_bot_commands).build()
)
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))
app.add_handler(CommandHandler("arp", arp))
app.add_handler(CommandHandler("sol", sol))


if __name__ == "__main__":
    app.run_polling()
