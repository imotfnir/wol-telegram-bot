import json
import os
import socket
from typing import Dict, List
from scapy.all import ARP, Ether, srp
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

UDP_IP: str = "0.0.0.0"
UDP_PORT: int = 10000
BROADCAST_IP: str = "192.168.0.255"
if (TOKEN := os.getenv("TELEGRAM_BOT_TOKEN")) is None:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable not set")

if (mac_table_json := os.getenv("MAC_TABLE")) is not None:
    DEFAULT_MAC_TABLE: Dict[str, str] = json.loads(mac_table_json.lower())
else:
    DEFAULT_MAC_TABLE: Dict[str, str] = {}
MAC_TABLE: Dict[str, str] = DEFAULT_MAC_TABLE.copy()


def send_wol(hostname: str) -> None:
    """Constructs and sends a Wake-on-LAN (WoL) magic packet."""
    mac_address: str = MAC_TABLE[hostname]
    mac_bytes: bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    magic_packet: bytes = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))


def send_sol(hostname: str) -> None:
    """Constructs and sends a Sleep-on-LAN (SoL) magic packet."""
    mac_address: str = MAC_TABLE[hostname]
    mac_bytes: bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))[
        ::-1
    ]
    magic_packet: bytes = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(magic_packet, (BROADCAST_IP, 9))


# States for ConversationHandler
(
    CHOOSING_ACTION,
    EDIT_CHOICE,
    EDIT_HOSTNAME,
    EDIT_MAC,
    ADD_HOSTNAME,
    ADD_MAC,
) = range(6)


# slash commands
async def set_bot_commands(application: Application) -> None:
    """Sets the bot's command list for the Telegram UI."""
    commands: List[BotCommand] = [
        BotCommand("start", "開始使用機器人"),
        BotCommand("help", "顯示幫助"),
        BotCommand("wol", "喚醒裝置"),
        BotCommand("sol", "哄睡裝置"),
        BotCommand("arp", "列出連線裝置並更新ARP表"),
        BotCommand("update_mac_table", "從區網更新MAC地址表"),
        BotCommand("print_mac_table", "顯示目前的MAC地址表"),
        BotCommand("edit_mac_table", "編輯MAC地址表"),
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

    result: List[tuple] = srp(packet, timeout=5, verbose=0)[0]

    scanned_devices: List[Dict[str, str]] = []
    for _, received in result:
        ip: str = received.psrc
        mac: str = received.hwsrc
        try:
            hostname: str = socket.gethostbyaddr(ip)[0].lower().split(".")[0]
        except socket.herror:
            hostname: str = None  # Cannot resolve hostname
        scanned_devices.append({"hostname": hostname, "ip": ip, "mac": mac})

    if not scanned_devices:
        await update.message.reply_text("No active devices found on the network.")
        return

    column_width: List[int] = [20, 15, 30]
    response: str = "Active devices on the network:\n"
    response += f"{'Host':<{column_width[0]}}{'IP':<{column_width[1]}}{'MAC':<{column_width[2]}}\n"
    for device in scanned_devices:
        # Prioritize hostname from MAC_TABLE, fallback to DNS-resolved hostname, then 'N/A'
        mac_table_hostname: str = next(
            (k for k, v in MAC_TABLE.items() if v == device["mac"]), None
        )
        mac_table_hostname = mac_table_hostname or device["hostname"] or "N/A"
        response += f"{mac_table_hostname:<{column_width[0]}}{device['ip']:<{column_width[1]}}{device['mac']:<{column_width[2]}}\n"
    print(response)
    await update.message.reply_markdown(f"```\n{response}\n```")


async def wol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /wol command to wake up a device."""
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
    """Handles the /sol command to sleep a device."""
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


async def update_mac_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Performs an ARP scan and updates the MAC_TABLE with newly found devices."""
    await update.message.reply_text("Updating MAC table via ARP scan...")

    target_ip: str = "192.168.0.1/24"  # TODO: Make this configurable
    arp_packet: ARP = ARP(pdst=target_ip)
    ether_packet: Ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether_packet / arp_packet

    result: List[tuple] = srp(packet, timeout=5, verbose=0)[0]

    updated_count: int = 0
    added_count: int = 0

    scanned_devices: Dict[str, str] = {}
    for _, received in result:
        ip: str = received.psrc
        mac: str = received.hwsrc
        try:
            hostname: str = socket.gethostbyaddr(ip)[0].lower().split(".")[0]
            scanned_devices[hostname] = mac
        except socket.herror:
            pass  # Cannot resolve hostname

    for hostname, mac in scanned_devices.items():
        if hostname in MAC_TABLE:
            if MAC_TABLE[hostname] != mac:
                MAC_TABLE[hostname] = mac
                updated_count += 1
        else:
            MAC_TABLE[hostname] = mac
            added_count += 1

    await update.message.reply_text(
        f"MAC table update complete. Added: {added_count}, Updated: {updated_count}"
    )


async def print_mac_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prints the current MAC address table."""
    if not MAC_TABLE:
        await update.message.reply_text("MAC table is empty.")
        return

    column_width: List[int] = [20, 20]
    response = "Current MAC Table:\n"
    response += f"{'Hostname':<{column_width[0]}}{'MAC Address':<{column_width[1]}}\n"
    for hostname, mac in MAC_TABLE.items():
        response += f"{hostname:<{column_width[0]}}{mac:<{column_width[1]}}\n"
    print(response)
    await update.message.reply_markdown(f"```\n{response}\n```")


async def edit_mac_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to edit the MAC table."""
    await update.message.reply_text(
        "Do you want to [edit] or [add] an entry? You can also /cancel."
    )
    return CHOOSING_ACTION


async def prompt_edit_or_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice to either edit or add an entry."""
    user_choice = update.message.text.lower()
    if user_choice == "edit":
        if not MAC_TABLE:
            await update.message.reply_text(
                "MAC table is empty, nothing to edit. You can [add] an entry or /cancel."
            )
            return CHOOSING_ACTION

        response = "Current MAC Table:\n"
        response += f"{'Index':<5}{'Hostname':<20}{'MAC Address':<20}\n"
        context.user_data["mac_table_keys"] = list(MAC_TABLE.keys())
        for i, hostname in enumerate(context.user_data["mac_table_keys"]):
            response += f"{i:<5}{hostname:<20}{MAC_TABLE[hostname]:<20}\n"

        await update.message.reply_markdown(f"```\n{response}\n```")
        await update.message.reply_text("Please enter the index of the entry to edit.")
        return EDIT_CHOICE
    elif user_choice == "add":
        await update.message.reply_text("Please enter the hostname for the new entry.")
        return ADD_HOSTNAME
    else:
        await update.message.reply_text(
            "Invalid choice. Please choose [edit] or [add]. You can also /cancel."
        )
        return CHOOSING_ACTION


async def receive_edit_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives the index of the entry to edit."""
    try:
        choice = int(update.message.text)
        keys = context.user_data["mac_table_keys"]
        if 0 <= choice < len(keys):
            context.user_data["edit_key"] = keys[choice]
            await update.message.reply_text(
                f"Editing entry for '{keys[choice]}'. Please enter the new hostname."
            )
            return EDIT_HOSTNAME
        else:
            await update.message.reply_text("Invalid index. Please try again.")
            return EDIT_CHOICE
    except (ValueError, KeyError):
        await update.message.reply_text("Invalid input. Please enter a number.")
        return EDIT_CHOICE


async def receive_edit_hostname(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives the new hostname for the entry being edited."""
    context.user_data["new_hostname"] = update.message.text.lower()
    await update.message.reply_text("Please enter the new MAC address.")
    return EDIT_MAC


async def receive_edit_mac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the new MAC address and finalizes the edit."""
    global MAC_TABLE
    old_key = context.user_data["edit_key"]
    new_hostname = context.user_data["new_hostname"]
    new_mac = update.message.text.lower()

    # Create a new dictionary to preserve order
    new_mac_table = {}
    for key, value in MAC_TABLE.items():
        if key == old_key:
            new_mac_table[new_hostname] = new_mac
        else:
            new_mac_table[key] = value
    MAC_TABLE = new_mac_table

    await update.message.reply_text(f"Entry updated: {new_hostname} - {new_mac}")
    context.user_data.clear()
    return ConversationHandler.END


async def receive_add_hostname(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives the hostname for the new entry."""
    context.user_data["new_hostname"] = update.message.text.lower()
    await update.message.reply_text("Please enter the MAC address for the new entry.")
    return ADD_MAC


async def receive_add_mac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the MAC address and adds the new entry."""
    hostname = context.user_data["new_hostname"]
    mac = update.message.text.lower()
    MAC_TABLE[hostname] = mac
    await update.message.reply_text(f"New entry added: {hostname} - {mac}")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


app: Application = (
    Application.builder().token(TOKEN).post_init(set_bot_commands).build()
)

edit_mac_table_handler = ConversationHandler(
    entry_points=[CommandHandler("edit_mac_table", edit_mac_start)],
    states={
        CHOOSING_ACTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, prompt_edit_or_add)
        ],
        ADD_HOSTNAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_hostname)
        ],
        ADD_MAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_mac)],
        EDIT_CHOICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_choice)
        ],
        EDIT_HOSTNAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_hostname)
        ],
        EDIT_MAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_mac)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("wol", wol))
app.add_handler(CommandHandler("arp", arp))
app.add_handler(CommandHandler("sol", sol))
app.add_handler(CommandHandler("update_mac_table", update_mac_table))
app.add_handler(CommandHandler("print_mac_table", print_mac_table))
app.add_handler(edit_mac_table_handler)


if __name__ == "__main__":
    app.run_polling()
