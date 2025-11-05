import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import json
import random
import tempfile

# دریافت توکن از متغیر محیطی - نسخه ایمن برای Render
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8320821562:AAGtOOvNY-errWP8MSVPdIJOaVllsNXYFmU')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8064413702'))

# در Render از دیتابیس موقت استفاده کنید
DATA_FILE = os.path.join(tempfile.gettempdir(), "user_data.json")

# کانال‌های اجباری
REQUIRED_CHANNELS = [
    {"name": "کانال MD روبلاکس", "link": "https://t.me/MDroblox", "id": "@MDroblox"},
    {"name": "Roblox Exploit IR", "link": "https://t.me/Robloxexploit_ir", "id": "@Robloxexploit_ir"}
]

print("🟢 شروع ربات...")
print(f"🔧 توکن: {'✅ موجود' if TOKEN else '❌ مفقود'}")
print(f"🔧 فایل داده: {DATA_FILE}")

# بارگذاری داده‌ها - نسخه اصلاح شده
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # اطمینان از وجود کلید users
                if "users" not in data:
                    data["users"] = {}
                return data
        else:
            # اگر فایل وجود ندارد، ساختار اولیه ایجاد شود
            return {"users": {}}
    except (json.JSONDecodeError, Exception) as e:
        print(f"خطا در بارگذاری داده‌ها: {e}")
        # در صورت خطا، ساختار اولیه برگردانده شود
        return {"users": {}}

# ذخیره داده‌ها
def save_data(data):
    try:
        # اطمینان از وجود کلید users قبل از ذخیره
        if "users" not in data:
            data["users"] = {}

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"خطا در ذخیره داده‌ها: {e}")
        return False

# تابع برای بررسی عضویت کاربر در گروه
async def is_user_in_group(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# تابع برای تبدیل مقدار به فرمت زیبا
def format_coin_amount(amount):
    if amount >= 1000000000:  # 1 میلیارد
        return f"{amount / 1000000000:.1f}B coin"
    elif amount >= 1000000:  # 1 میلیون
        return f"{amount / 1000000:.1f}M coin"
    elif amount >= 1000:  # 1 هزار
        return f"{amount / 1000:.1f}K coin"
    else:
        return f"{amount} coin"

# تابع برای تبدیل رشته به عدد (پشتیبانی از k, m, b)
def parse_amount(amount_str):
    if not amount_str:
        return None

    amount_str = amount_str.lower().strip()

    try:
        if amount_str.endswith('b'):
            return int(float(amount_str[:-1]) * 1000000000)
        elif amount_str.endswith('m'):
            return int(float(amount_str[:-1]) * 1000000)
        elif amount_str.endswith('k'):
            return int(float(amount_str[:-1]) * 1000)
        else:
            return int(amount_str)
    except (ValueError, TypeError):
        return None

# تابع برای دریافت لیست تمام اعضای گروه
async def get_all_group_members(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        members = []
        async for member in context.bot.get_chat_members(chat_id):
            if member.user.is_bot:
                continue
            members.append(member.user)
        return members
    except Exception as e:
        print(f"خطا در دریافت لیست اعضا: {e}")
        return []

# بررسی عضویت در کانال‌های اجباری
async def check_membership(user_id, context):
    not_joined = []

    for channel in REQUIRED_CHANNELS:
        try:
            chat_id = channel["id"]
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(channel)
        except Exception as e:
            print(f"خطا در بررسی کانال {channel['name']}: {e}")
            not_joined.append(channel)

    return not_joined

# تابع برای بررسی عضویت اجباری قبل از اجرای هر دستور
async def check_membership_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str = None):
    user = update.effective_user
    
    # دستوراتی که نیاز به بررسی عضویت ندارند
    exempt_commands = ['start', 'cancel']
    
    if command_name in exempt_commands:
        return True
        
    # بررسی عضویت
    not_joined = await check_membership(user.id, context)
    
    if not_joined:
        channels_text = "\n".join([f"• {ch['name']} - {ch['link']}" for ch in not_joined])
        
        if update.message.chat.type == "private":
            # در پیوی
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"🔗 {channel['name']}", url=channel["link"])])
            keyboard.append([InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🔒 **برای استفاده از ربات، ابتدا در کانال‌های زیر عضو شوید:**\n\n"
                f"{channels_text}\n\n"
                f"پس از عضویت در تمام کانال‌ها روی دکمه '✅ تأیید عضویت' کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            # در گروه
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"🔗 {channel['name']}", url=channel["link"])])
            keyboard.append([InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership_group")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🔒 **برای استفاده از دستورات ربات، ابتدا در کانال‌های زیر عضو شوید:**\n\n"
                f"{channels_text}\n\n"
                f"پس از عضویت در تمام کانال‌ها روی دکمه '✅ تأیید عضویت' کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        return False
    
    return True

# منوها
def get_main_keyboard():
    keyboard = [
        ["📞 ارسال پیام به پشتیبانی"],
        ["🎮 آموزش Blox Fruit", "💰 فروت ولیو"],
        ["🛍 خدمات", "خرید پرم و گیم پس 🛒"],
        ["لوایتان", "گرفتن سرور پرایوت"],
        ["🛠 اسکریپت", "📥 دانلود دلتا"],
        ["کلید دلتا"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_script_keyboard():
    keyboard = [
        ["🎮 بلاکس فروت", "🛡️ گروگاردن"],
        ["🌙 99شب", "⚔️ استیل براینت"],
        ["🔙 بازگشت به منوی اصلی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ لغو"]], resize_keyboard=True)

def get_membership_keyboard():
    buttons = []
    for channel in REQUIRED_CHANNELS:
        buttons.append([InlineKeyboardButton(f"🔗 {channel['name']}", url=channel["link"])])
    buttons.append([InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership")])
    return InlineKeyboardMarkup(buttons)

def get_membership_keyboard_group():
    buttons = []
    for channel in REQUIRED_CHANNELS:
        buttons.append([InlineKeyboardButton(f"🔗 {channel['name']}", url=channel["link"])])
    buttons.append([InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership_group")])
    return InlineKeyboardMarkup(buttons)

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # بررسی عضویت
    not_joined = await check_membership(user.id, context)

    if not_joined:
        if update.message.chat.type == "private":
            await update.message.reply_text(
                f"🔒 **برای استفاده از ربات، ابتدا در کانال‌های زیر عضو شوید:**\n\n"
                f"{' '.join([f'• {ch['name']} - {ch['link']}' for ch in not_joined])}\n\n"
                f"پس از عضویت در تمام کانال‌ها روی دکمه '✅ تأیید عضویت' کلیک کنید.",
                reply_markup=get_membership_keyboard(),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                f"🔒 **برای استفاده از ربات، ابتدا در کانال‌های زیر عضو شوید:**\n\n"
                f"{' '.join([f'• {ch['name']} - {ch['link']}' for ch in not_joined])}\n\n"
                f"پس از عضویت در تمام کانال‌ها روی دکمه '✅ تأیید عضویت' کلیک کنید.",
                reply_markup=get_membership_keyboard_group(),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    else:
        if update.message.chat.type == "private":
            await update.message.reply_text(
                "🎉 **به ربات MD روبلاکس خوش آمدید!**\n\n"
                "✅ عضویت شما در تمام کانال‌ها تأیید شد\n\n"
                "💡 از دستورات موجود در منوی پایین استفاده کنید:",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🤖 **ربات MD روبلاکس**\n\n"
                "✅ عضویت شما در تمام کانال‌ها تأیید شد\n\n"
                "از دستورات زیر استفاده کنید:\n"
                "• /bal - مشاهده موجودی\n"
                "• /pay - پرداخت به کاربر دیگر\n"
                "• /bet - شرط بندی\n"
                "• /add - اضافه کردن موجودی (ادمین)\n"
                "• /rem - کم کردن موجودی (ادمین)\n"
                "• /resetbal - ریست کردن موجودی تمام کاربران (ادمین)\n"
                "• /alladd - اضافه کردن موجودی به تمام کاربران (ادمین)\n"
                "• /global - مشاهده لیدربرد",
                parse_mode='Markdown'
            )

# دستور BAL - نمایش موجودی (هم در گروه و هم پیوی)
async def bal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "bal"):
        return

    user = update.effective_user
    data = load_data()

    user_id_str = str(user.id)

    # اطمینان از وجود کاربر در دیتابیس - نسخه ایمن
    if "users" not in data:
        data["users"] = {}

    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "balance": 0,
            "name": user.first_name or f"User_{user.id}"
        }
        if not save_data(data):
            await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")
            return
        balance = 0
    else:
        balance = data["users"][user_id_str].get("balance", 0)

    user_name = user.first_name or f"User_{user.id}"
    formatted_balance = format_coin_amount(balance)
    
    if update.message.chat.type == "private":
        await update.message.reply_text(
            f"💰 **موجودی شما:** {formatted_balance}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"💰 **موجودی {user_name}:** {formatted_balance}",
            parse_mode='Markdown'
        )

# دستور PAY - پرداخت به کاربر دیگر (هم در گروه و هم پیوی)
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "pay"):
        return

    user = update.effective_user
    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    # بررسی ریپلای
    if not update.message.reply_to_message:
        user_balance = data['users'].get(str(user.id), {}).get('balance', 0)
        formatted_balance = format_coin_amount(user_balance)
        await update.message.reply_text(
            "💰 **پرداخت coin**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/pay [مبلغ]` (با ریپلای روی پیام کاربر)\n\n"
            "📝 **مثال‌ها:**\n"
            "`/pay 1000` - پرداخت 1000 coin\n"
            "`/pay 1k` - پرداخت 1,000 coin\n"
            "`/pay 1.5k` - پرداخت 1,500 coin\n"
            "`/pay 1m` - پرداخت 1,000,000 coin\n"
            "`/pay 1b` - پرداخت 1,000,000,000 coin\n\n"
            f"💰 **موجودی فعلی شما:** {formatted_balance}",
            parse_mode='Markdown'
        )
        return

    if not context.args or len(context.args) < 1:
        user_balance = data['users'].get(str(user.id), {}).get('balance', 0)
        formatted_balance = format_coin_amount(user_balance)
        await update.message.reply_text(
            "💰 **پرداخت coin**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/pay [مبلغ]` (با ریپلای روی پیام کاربر)\n\n"
            "📝 **مثال‌ها:**\n"
            "`/pay 1000` - پرداخت 1000 coin\n"
            "`/pay 1k` - پرداخت 1,000 coin\n"
            "`/pay 1.5k` - پرداخت 1,500 coin\n"
            "`/pay 1m` - پرداخت 1,000,000 coin\n"
            "`/pay 1b` - پرداخت 1,000,000,000 coin\n\n"
            f"💰 **موجودی فعلی شما:** {formatted_balance}",
            parse_mode='Markdown'
        )
        return

    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ **مبلغ نامعتبر!**\n\n"
            "✅ **فرمت‌های معتبر:**\n"
            "• `1000` - عدد معمولی\n"
            "• `1k` یا `1K` - هزار\n"
            "• `1.5k` - یک و نیم هزار\n"
            "• `1m` یا `1M` - میلیون\n"
            "• `1b` یا `1B` - میلیارد",
            parse_mode='Markdown'
        )
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user:
        await update.message.reply_text("❌ کاربر مورد نظر یافت نشد!")
        return

    # بررسی اینکه کاربر به خودش پول ندهد
    if user.id == target_user.id:
        await update.message.reply_text("❌ نمی‌توانید به خودتان coin بدهید!")
        return

    # بررسی عضویت کاربر هدف در گروه (اگر در گروه هستیم)
    if update.message.chat.type != "private":
        if not await is_user_in_group(context, target_user.id, update.message.chat.id):
            await update.message.reply_text("❌ کاربر مورد نظر در این گروه عضو نیست!")
            return

    user_id_str = str(user.id)
    target_user_id_str = str(target_user.id)

    # اطمینان از وجود کاربر در دیتابیس
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "balance": 0,
            "name": user.first_name or f"User_{user.id}"
        }

    user_balance = data["users"][user_id_str].get("balance", 0)

    # بررسی موجودی کاربر
    if user_balance < amount:
        formatted_user_balance = format_coin_amount(user_balance)
        formatted_amount = format_coin_amount(amount)
        await update.message.reply_text(
            f"❌ **موجودی کافی نیست!**\n\n"
            f"💰 موجودی شما: {formatted_user_balance}\n"
            f"💸 مبلغ درخواستی: {formatted_amount}",
            parse_mode='Markdown'
        )
        return

    # انجام تراکنش
    data["users"][user_id_str]["balance"] = user_balance - amount

    if target_user_id_str not in data["users"]:
        data["users"][target_user_id_str] = {
            "balance": amount,
            "name": target_user.first_name or f"User_{target_user.id}"
        }
    else:
        target_old_balance = data["users"][target_user_id_str].get("balance", 0)
        data["users"][target_user_id_str]["balance"] = target_old_balance + amount

    if save_data(data):
        user_name = user.first_name or f"User_{user.id}"
        target_name = target_user.first_name or f"User_{target_user.id}"
        formatted_amount = format_coin_amount(amount)
        formatted_new_balance = format_coin_amount(data['users'][user_id_str]['balance'])

        await update.message.reply_text(
            f"✅ **پرداخت موفق!**\n\n"
            f"👤 از: {user_name}\n"
            f"👤 به: {target_name}\n"
            f"💰 مبلغ: {formatted_amount}\n"
            f"💳 موجودی جدید شما: {formatted_new_balance}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور BET - شرط بندی (هم در گروه و هم پیوی)
async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "bet"):
        return

    user = update.effective_user
    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    if not context.args or len(context.args) < 2:
        user_balance = data['users'].get(str(user.id), {}).get('balance', 0)
        formatted_balance = format_coin_amount(user_balance)
        await update.message.reply_text(
            "🎲 **شرط بندی**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/bet [مبلغ] [e/h]`\n\n"
            "📝 **معنی حروف:**\n"
            "`e` = زوج (Even)\n"
            "`h` = فرد (Odd)\n\n"
            "🎯 **مثال‌ها:**\n"
            "`/bet 1000 e` - شرط 1000 coin روی زوج\n"
            "`/bet 1k h` - شرط 1,000 coin روی فرد\n"
            "`/bet 1.5k e` - شرط 1,500 coin روی زوج\n"
            "`/bet 1m h` - شرط 1,000,000 coin روی فرد\n\n"
            f"💰 **موجودی فعلی شما:** {formatted_balance}",
            parse_mode='Markdown'
        )
        return

    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ **مبلغ نامعتبر!**\n\n"
            "✅ **فرمت‌های معتبر:**\n"
            "• `1000` - عدد معمولی\n"
            "• `1k` یا `1K` - هزار\n"
            "• `1.5k` - یک و نیم هزار\n"
            "• `1m` یا `1M` - میلیون\n"
            "• `1b` یا `1B` - میلیارد",
            parse_mode='Markdown'
        )
        return

    bet_type = context.args[1].lower()
    if bet_type not in ['e', 'h']:
        await update.message.reply_text("❌ نوع شرط نامعتبر! از e برای زوج و h برای فرد استفاده کنید.")
        return

    user_id_str = str(user.id)

    # اطمینان از وجود کاربر در دیتابیس
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "balance": 0,
            "name": user.first_name or f"User_{user.id}"
        }

    user_balance = data["users"][user_id_str].get("balance", 0)

    # بررسی موجودی
    if user_balance < amount:
        formatted_user_balance = format_coin_amount(user_balance)
        formatted_amount = format_coin_amount(amount)
        await update.message.reply_text(
            f"❌ **موجودی کافی نیست!**\n\n"
            f"💰 موجودی شما: {formatted_user_balance}\n"
            f"💸 مبلغ شرط: {formatted_amount}",
            parse_mode='Markdown'
        )
        return

    # تولید عدد تصادفی
    dice_number = random.randint(1, 6)
    is_even = dice_number % 2 == 0

    # بررسی برنده
    user_won = False
    if (bet_type == 'e' and is_even) or (bet_type == 'h' and not is_even):
        user_won = True

    # محاسبه نتیجه
    if user_won:
        new_balance = user_balance + amount
        result_text = "🎉 **برنده شدید!**"
        emoji = "🎊"
    else:
        new_balance = user_balance - amount
        result_text = "💔 **باختید!**"
        emoji = "😢"

    data["users"][user_id_str]["balance"] = new_balance

    if save_data(data):
        bet_type_text = "زوج 🎯" if bet_type == 'e' else "فرد 🎯"
        dice_result = "زوج" if is_even else "فرد"
        user_name = user.first_name or f"User_{user.id}"
        formatted_amount = format_coin_amount(amount)
        formatted_new_balance = format_coin_amount(new_balance)

        await update.message.reply_text(
            f"{emoji} **نتیجه شرط‌بندی**\n\n"
            f"👤 کاربر: {user_name}\n"
            f"🎲 عدد تاس: {dice_number} ({dice_result})\n"
            f"🎯 شرط شما: {bet_type_text}\n"
            f"💰 مبلغ شرط: {formatted_amount}\n"
            f"🏆 نتیجه: {result_text}\n"
            f"💳 موجودی جدید: {formatted_new_balance}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور ADD - اضافه کردن موجودی (فقط ادمین)
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "add"):
        return

    user = update.effective_user

    # بررسی ادمین بودن
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ این دستور فقط برای ادمین قابل استفاده است!")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "💰 **اضافه کردن موجودی**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/add [مبلغ]` (با ریپلای روی پیام کاربر)\n\n"
            "📝 **مثال‌ها:**\n"
            "`/add 1000` - اضافه کردن 1000 coin\n"
            "`/add 1k` - اضافه کردن 1,000 coin\n"
            "`/add 1.5k` - اضافه کردن 1,500 coin\n"
            "`/add 1m` - اضافه کردن 1,000,000 coin\n"
            "`/add 1b` - اضافه کردن 1,000,000,000 coin",
            parse_mode='Markdown'
        )
        return

    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ **مبلغ نامعتبر!**\n\n"
            "✅ **فرمت‌های معتبر:**\n"
            "• `1000` - عدد معمولی\n"
            "• `1k` یا `1K` - هزار\n"
            "• `1.5k` - یک و نیم هزار\n"
            "• `1m` یا `1M` - میلیون\n"
            "• `1b` یا `1B` - میلیارد",
            parse_mode='Markdown'
        )
        return

    # بررسی ریپلای
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید!")
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user:
        await update.message.reply_text("❌ کاربر مورد نظر یافت نشد!")
        return

    # بررسی عضویت کاربر هدف در گروه (اگر در گروه هستیم)
    if update.message.chat.type != "private":
        if not await is_user_in_group(context, target_user.id, update.message.chat.id):
            await update.message.reply_text("❌ کاربر مورد نظر در این گروه عضو نیست!")
            return

    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    target_user_id_str = str(target_user.id)

    if target_user_id_str not in data["users"]:
        data["users"][target_user_id_str] = {
            "balance": amount,
            "name": target_user.first_name or f"User_{target_user.id}"
        }
        new_balance = amount
    else:
        old_balance = data["users"][target_user_id_str].get("balance", 0)
        data["users"][target_user_id_str]["balance"] = old_balance + amount
        new_balance = old_balance + amount

    if save_data(data):
        target_name = target_user.first_name or f"User_{target_user.id}"
        formatted_amount = format_coin_amount(amount)
        formatted_new_balance = format_coin_amount(new_balance)

        await update.message.reply_text(
            f"✅ **موجودی اضافه شد!**\n\n"
            f"👤 کاربر: {target_name}\n"
            f"💰 مبلغ: {formatted_amount}\n"
            f"💳 موجودی جدید: {formatted_new_balance}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور REM - کم کردن موجودی (فقط ادمین)
async def rem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "rem"):
        return

    user = update.effective_user

    # بررسی ادمین بودن
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ این دستور فقط برای ادمین قابل استفاده است!")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "💰 **کم کردن موجودی**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/rem [مبلغ]` (با ریپلای روی پیام کاربر)\n\n"
            "📝 **مثال‌ها:**\n"
            "`/rem 1000` - کم کردن 1000 coin\n"
            "`/rem 1k` - کم کردن 1,000 coin\n"
            "`/rem 1.5k` - کم کردن 1,500 coin\n"
            "`/rem 1m` - کم کردن 1,000,000 coin\n"
            "`/rem 1b` - کم کردن 1,000,000,000 coin",
            parse_mode='Markdown'
        )
        return

    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ **مبلغ نامعتبر!**\n\n"
            "✅ **فرمت‌های معتبر:**\n"
            "• `1000` - عدد معمولی\n"
            "• `1k` یا `1K` - هزار\n"
            "• `1.5k` - یک و نیم هزار\n"
            "• `1m` یا `1M` - میلیون\n"
            "• `1b` یا `1B` - میلیارد",
            parse_mode='Markdown'
        )
        return

    # بررسی ریپلای
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید!")
        return

    target_user = update.message.reply_to_message.from_user
    if not target_user:
        await update.message.reply_text("❌ کاربر مورد نظر یافت نشد!")
        return

    # بررسی عضویت کاربر هدف در گروه (اگر در گروه هستیم)
    if update.message.chat.type != "private":
        if not await is_user_in_group(context, target_user.id, update.message.chat.id):
            await update.message.reply_text("❌ کاربر مورد نظر در این گروه عضو نیست!")
            return

    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    target_user_id_str = str(target_user.id)

    if target_user_id_str not in data["users"]:
        data["users"][target_user_id_str] = {
            "balance": 0,
            "name": target_user.first_name or f"User_{target_user.id}"
        }

    old_balance = data["users"][target_user_id_str].get("balance", 0)

    # انجام کم کردن حتی اگر موجودی کافی نباشد (منفی شدن)
    new_balance = old_balance - amount
    data["users"][target_user_id_str]["balance"] = new_balance

    if save_data(data):
        target_name = target_user.first_name or f"User_{target_user.id}"
        formatted_amount = format_coin_amount(amount)
        formatted_new_balance = format_coin_amount(new_balance)

        await update.message.reply_text(
            f"✅ **موجودی کم شد!**\n\n"
            f"👤 کاربر: {target_name}\n"
            f"💰 مبلغ: {formatted_amount}\n"
            f"💳 موجودی جدید: {formatted_new_balance}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور RESETBAL - ریست کردن موجودی تمام کاربران گروه (فقط ادمین)
async def resetbal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "resetbal"):
        return

    user = update.effective_user

    # بررسی ادمین بودن
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ این دستور فقط برای ادمین قابل استفاده است!")
        return

    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    # دریافت تمام اعضای گروه (اگر در گروه هستیم)
    reset_count = 0
    if update.message.chat.type != "private":
        group_members = await get_all_group_members(context, update.message.chat.id)
        for member in group_members:
            member_id_str = str(member.id)
            # ایجاد یا آپدیت کاربر در دیتابیس
            if member_id_str not in data["users"]:
                data["users"][member_id_str] = {
                    "balance": 0,
                    "name": member.first_name or f"User_{member.id}"
                }
            else:
                data["users"][member_id_str]["balance"] = 0
            reset_count += 1
    else:
        # در پیوی، تمام کاربران ریست می‌شوند
        for user_id_str in data["users"]:
            data["users"][user_id_str]["balance"] = 0
            reset_count += 1

    if save_data(data):
        await update.message.reply_text(
            f"✅ **موجودی تمام کاربران ریست شد!**\n\n"
            f"👥 تعداد کاربران: {reset_count} نفر\n"
            f"💰 موجودی همه کاربران 0 coin شد",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور ALLADD - اضافه کردن موجودی به تمام کاربران گروه (فقط ادمین)
async def alladd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "alladd"):
        return

    user = update.effective_user

    # بررسی ادمین بودن
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ این دستور فقط برای ادمین قابل استفاده است!")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "💰 **اضافه کردن موجودی به تمام کاربران**\n\n"
            "❌ **فرمت دستور:**\n"
            "`/alladd [مبلغ]`\n\n"
            "📝 **مثال‌ها:**\n"
            "`/alladd 100` - به تمام کاربران گروه 100 coin اضافه می‌شود\n"
            "`/alladd 1k` - به تمام کاربران گروه 1,000 coin اضافه می‌شود\n"
            "`/alladd 1.5k` - به تمام کاربران گروه 1,500 coin اضافه می‌شود\n"
            "`/alladd 1m` - به تمام کاربران گروه 1,000,000 coin اضافه می‌شود",
            parse_mode='Markdown'
        )
        return

    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ **مبلغ نامعتبر!**\n\n"
            "✅ **فرمت‌های معتبر:**\n"
            "• `1000` - عدد معمولی\n"
            "• `1k` یا `1K` - هزار\n"
            "• `1.5k` - یک و نیم هزار\n"
            "• `1m` یا `1M` - میلیون\n"
            "• `1b` یا `1B` - میلیارد",
            parse_mode='Markdown'
        )
        return

    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data:
        data["users"] = {}

    # دریافت تمام اعضای گروه (اگر در گروه هستیم)
    added_count = 0
    if update.message.chat.type != "private":
        group_members = await get_all_group_members(context, update.message.chat.id)
        for member in group_members:
            member_id_str = str(member.id)
            if member_id_str not in data["users"]:
                data["users"][member_id_str] = {
                    "balance": amount,
                    "name": member.first_name or f"User_{member.id}"
                }
            else:
                old_balance = data["users"][member_id_str].get("balance", 0)
                data["users"][member_id_str]["balance"] = old_balance + amount
            added_count += 1
    else:
        # در پیوی، به تمام کاربران اضافه می‌شود
        for user_id_str in data["users"]:
            old_balance = data["users"][user_id_str].get("balance", 0)
            data["users"][user_id_str]["balance"] = old_balance + amount
            added_count += 1

    if save_data(data):
        formatted_amount = format_coin_amount(amount)
        await update.message.reply_text(
            f"✅ **موجودی به تمام کاربران اضافه شد!**\n\n"
            f"👥 تعداد کاربران: {added_count} نفر\n"
            f"💰 مبلغ اضافه شده: {formatted_amount} به هر کاربر",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در ذخیره‌سازی داده‌ها!")

# دستور GLOBAL - نمایش لیدربرد تمام کاربران
async def global_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی عضویت
    if not await check_membership_middleware(update, context, "global"):
        return

    data = load_data()

    # اطمینان از وجود ساختار users
    if "users" not in data or not data["users"]:
        await update.message.reply_text("📊 **هنوز هیچ کاربری در سیستم ثبت نشده است!**")
        return

    # ایجاد لیست کاربران با موجودی
    users_list = []
    for user_id, user_data in data["users"].items():
        if "balance" in user_data and "name" in user_data:
            users_list.append({
                "name": user_data["name"],
                "balance": user_data["balance"],
                "id": user_id
            })

    # مرتب‌سازی بر اساس موجودی (نزولی)
    users_list.sort(key=lambda x: x["balance"], reverse=True)

    # گرفتن 20 کاربر برتر
    top_users = users_list[:20]

    # ساخت متن لیدربرد
    leaderboard_text = "🏆 **لیدربرد جهانی**\n\n"

    for i, user in enumerate(top_users, 1):
        medal = ""
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        formatted_balance = format_coin_amount(user["balance"])
        leaderboard_text += f"{medal} {user['name']} - {formatted_balance}\n"

    await update.message.reply_text(leaderboard_text, parse_mode='Markdown')

# هندلر دکمه‌ها - نسخه اصلاح شده
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_membership":
        not_joined = await check_membership(user_id, context)

        if not_joined:
            channels_text = "\n".join([f"• {ch['name']} - {ch['link']}" for ch in not_joined])
            await query.edit_message_text(
                f"❌ **هنوز در کانال‌های زیر عضو نیستید:**\n\n"
                f"{channels_text}\n\n"
                f"لطفاً ابتدا در تمام کانال‌ها عضو شوید سپس روی تأیید عضویت کلیک کنید.",
                reply_markup=get_membership_keyboard(),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await query.edit_message_text(
                "✅ **عضویت شما در تمام کانال‌ها تأیید شد!**\n\n"
                "اکنون می‌توانید از دستورات ربات استفاده کنید.",
                reply_markup=get_main_keyboard()
            )

    elif query.data == "check_membership_group":
        not_joined = await check_membership(user_id, context)

        if not_joined:
            channels_text = "\n".join([f"• {ch['name']} - {ch['link']}" for ch in not_joined])
            await query.edit_message_text(
                f"❌ **هنوز در کانال‌های زیر عضو نیستید:**\n\n"
                f"{channels_text}\n\n"
                f"لطفاً ابتدا در تمام کانال‌ها عضو شوید سپس روی تأیید عضویت کلیک کنید.",
                reply_markup=get_membership_keyboard_group(),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await query.edit_message_text(
                "✅ **عضویت شما در تمام کانال‌ها تأیید شد!**\n\n"
                "اکنون می‌توانید از دستورات ربات استفاده کنید."
            )

    elif query.data.startswith("reply_delta_"):
        user_id_to_reply = int(query.data.replace("reply_delta_", ""))
        context.user_data['waiting_for_admin_reply_to'] = user_id_to_reply
        await query.message.reply_text(
            f"📝 در حال پاسخ به کاربر {user_id_to_reply}\n\nلطفاً پاسخ خود را ارسال کنید:",
            reply_markup=get_cancel_keyboard()
        )

    elif query.data.startswith("accept_"):
        user_id_to_notify = int(query.data.replace("accept_", ""))
        try:
            await context.bot.send_message(
                chat_id=user_id_to_notify,
                text="✅ **عکس شما تأیید شد!**\n\nلطفاً وارد گروه زیر شوید:\nhttps://t.me/+hv5doxIypENhMTU0"
            )
            await query.edit_message_text("✅ کاربر مطلع شد")
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در ارسال پیام: {e}")

    elif query.data.startswith("reject_"):
        user_id_to_notify = int(query.data.replace("reject_", ""))
        try:
            await context.bot.send_message(
                chat_id=user_id_to_notify,
                text="❌ **عکس شما رد شد**\n\nمتأسفانه عکس شما قابل قبول نبود. امیدواریم دفعه بعدی قبول شوید."
            )
            await query.edit_message_text("❌ کاربر مطلع شد")
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در ارسال پیام: {e}")

# هندلر پیام‌های متنی - نسخه اصلاح شده
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    text = update.message.text
    user_id = update.effective_user.id

    # بررسی عضویت برای تمام دستورات (به جز لغو و استارت)
    if text not in ["❌ لغو", "/start"] and not context.user_data.get('bypass_check'):
        not_joined = await check_membership(user_id, context)
        if not_joined:
            channels_text = "\n".join([f"• {ch['name']} - {ch['link']}" for ch in not_joined])
            await update.message.reply_text(
                f"❌ **لطفاً ابتدا در کانال‌های اجباری عضو شوید:**\n\n"
                f"{channels_text}\n\n"
                f"از دستور /start استفاده کنید.",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            return

    # پردازش دستورات
    if text == "❌ لغو":
        context.user_data.clear()
        await update.message.reply_text(
            "✅ عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )

    elif text == "🔙 بازگشت به منوی اصلی":
        context.user_data.clear()
        await update.message.reply_text(
            "🔙 به منوی اصلی بازگشتید.",
            reply_markup=get_main_keyboard()
        )

    elif text == "📞 ارسال پیام به پشتیبانی":
        await update.message.reply_text(
            "📞 **پشتیبانی**\n\n"
            "برای ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n"
            "👤 @madaraking0",
            parse_mode='Markdown'
        )

    elif text == "💰 فروت ولیو":
        await update.message.reply_text(
            "💰 **فروت ولیو**\n\n"
            "برای مشاهده ارزش میوه‌ها به سایت زیر مراجعه کنید:\n"
            "🌐 https://bloxfruitsvalues.com/calculator",
            parse_mode='Markdown'
        )

    elif text == "🛍 خدمات":
        await update.message.reply_text(
            "🛍 **خدمات**\n\n"
            "برای سفارش خدمات به آیدی زیر پیام دهید:\n"
            "👤 @kobes2221",
            parse_mode='Markdown'
        )

    elif text == "خرید پرم و گیم پس 🛒":
        await update.message.reply_text(
            "🛒 **خرید پرم و گیم پس**\n\n"
            "برای خرید به آیدی زیر مراجعه کنید:\n"
            "👤 @PKGOMNAM7",
            parse_mode='Markdown'
        )

    elif text == "لوایتان":
        context.user_data['waiting_for_loyatan'] = True
        await update.message.reply_text(
            "📸 **لوایتان**\n\n"
            "لطفاً عکس مربوطه را ارسال کنید:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )

    elif text == "گرفتن سرور پرایوت":
        await update.message.reply_text(
            "🎮 **سرور پرایوت**\n\n"
            "سرور ۱:\n"
            "https://www.roblox.com/share?code=a582b1dc6de83e499c1effb20d3f6fe7&type=Server\n\n"
            "سرور ۲:\n"
            "به زودی...",
            parse_mode='Markdown'
        )

    elif text == "🛠 اسکریپت":
        await update.message.reply_text(
            "🛠 **اسکریپت‌ها**\n\n"
            "لطفاً یکی از اسکریپت‌ها را انتخاب کنید:",
            reply_markup=get_script_keyboard(),
            parse_mode='Markdown'
        )

    elif text == "📥 دانلود دلتا":
        await update.message.reply_text(
            "📥 **دانلود دلتا**\n\n"
            "🔗 لینک دانلود:\n"
            "https://deltaexploits.net/Delta.apk\n\n"
            "🌐 سایت رسمی:\n"
            "https://deltaexploits.net\n\n"
            "⚠️ حتماً از VPN استفاده کنید!",
            parse_mode='Markdown'
        )

    elif text == "کلید دلتا":
        context.user_data['waiting_for_delta'] = True
        await update.message.reply_text(
            "🔑 **کلید دلتا**\n\n"
            "لطفاً لینک کلید خود را ارسال کنید:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )

    elif text in ["🎮 بلاکس فروت", "🛡️ گروگاردن", "🌙 99شب", "⚔️ استیل براینت"]:
        await update.message.reply_text(
            "⏳ **این بخش در حال توسعه است...**\n\n"
            "به زودی در دسترس خواهد بود.",
            parse_mode='Markdown'
        )

    elif text == "🎮 آموزش Blox Fruit":
        await update.message.reply_text(
            "📚 **آموزش Blox Fruit**\n\n"
            "این بخش به زودی تکمیل خواهد شد...",
            parse_mode='Markdown'
        )

    elif context.user_data.get('waiting_for_delta'):
        # پردازش لینک دلتا
        user = update.effective_user
        delta_link = text

        # ارسال به ادمین
        try:
            keyboard = [
                [
                    InlineKeyboardButton("📝 پاسخ به کاربر", callback_data=f"reply_delta_{user.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔗 **درخواست کلید دلتا**\n\n"
                     f"👤 کاربر: {user.first_name}\n"
                     f"🆔 آیدی: {user.id}\n"
                     f"📎 لینک: {delta_link}",
                reply_markup=reply_markup
            )

            await update.message.reply_text(
                "✅ **لینک شما ارسال شد**\n\n"
                "منتظر پاسخ ادمین باشید...",
                reply_markup=get_main_keyboard()
            )
            context.user_data.pop('waiting_for_delta', None)

        except Exception as e:
            await update.message.reply_text(
                "❌ خطا در ارسال لینک. لطفاً مجدداً تلاش کنید."
            )

    elif context.user_data.get('waiting_for_admin_reply_to') and user_id == ADMIN_ID:
        # پاسخ ادمین به کاربر
        target_user_id = context.user_data['waiting_for_admin_reply_to']
        admin_reply = text

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"📩 **پاسخ از ادمین:**\n\n{admin_reply}"
            )
            await update.message.reply_text("✅ پاسخ شما ارسال شد")
            context.user_data.pop('waiting_for_admin_reply_to', None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پاسخ: {e}")

# هندلر عکس‌ها (فقط در پیوی)
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    if context.user_data.get('waiting_for_loyatan'):
        user = update.effective_user
        photo = update.message.photo[-1]

        # ارسال به ادمین
        try:
            keyboard = [
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user.id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=f"📸 **عکس لوایتان**\n\n"
                       f"👤 کاربر: {user.first_name}\n"
                       f"🆔 آیدی: {user.id}",
                reply_markup=reply_markup
            )

            await update.message.reply_text(
                "✅ **عکس شما ارسال شد**\n\n"
                "منتظر تأیید ادمین باشید...",
                reply_markup=get_main_keyboard()
            )
            context.user_data.pop('waiting_for_loyatan', None)

        except Exception as e:
            await update.message.reply_text(
                "❌ خطا در ارسال عکس. لطفاً مجدداً تلاش کنید."
            )

# تنظیم دستورات برای منوی پایین
async def set_commands(application):
    commands = [
        ("start", "شروع ربات"),
        ("bal", "مشاهده موجودی"),
        ("pay", "پرداخت به کاربر دیگر"),
        ("bet", "شرط بندی"),
        ("add", "اضافه کردن موجودی - ادمین"),
        ("rem", "کم کردن موجودی - ادمین"),
        ("resetbal", "ریست کردن موجودی تمام کاربران - ادمین"),
        ("alladd", "اضافه کردن موجودی به تمام کاربران - ادمین"),
        ("global", "مشاهده لیدربرد جهانی")
    ]
    await application.bot.set_my_commands(commands)

# اصلی - نسخه اصلاح شده برای Render
def main():
    try:
        print("🔧 شروع main function...")
        
        # بررسی توکن
        if not TOKEN:
            print("❌ توکن ربات تنظیم نشده! لطفا TELEGRAM_BOT_TOKEN را تنظیم کنید.")
            return
        
        # ایجاد اپلیکیشن
        application = Application.builder().token(TOKEN).build()
        print("✅ اپلیکیشن ساخته شد")

        # تنظیم دستورات برای منوی پایین
        application.post_init = set_commands

        # افزودن هندلرها
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("bal", bal_command))
        application.add_handler(CommandHandler("pay", pay_command))
        application.add_handler(CommandHandler("bet", bet_command))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("rem", rem_command))
        application.add_handler(CommandHandler("resetbal", resetbal_command))
        application.add_handler(CommandHandler("alladd", alladd_command))
        application.add_handler(CommandHandler("global", global_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

        # اجرای ربات
        print("🤖 ربات فعال شد...")
        print("💰 سیستم اقتصادی فعال (هم در گروه و هم پیوی)")
        print("🎲 شرط بندی فعال (هم در گروه و هم پیوی)")
        print("👑 دستورات ادمین فعال")
        print("📊 لیدربرد جهانی فعال")
        print("🔢 پشتیبانی از فرمت‌های k, m, b")
        print("🔒 سیستم عضویت اجباری فعال (هم در گروه و هم پیوی)")
        print("📢 کانال‌های اجباری:")
        for channel in REQUIRED_CHANNELS:
            print(f"   • {channel['name']}: {channel['link']}")
        
        application.run_polling()
        
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
