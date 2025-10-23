from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import json
import os
import urllib.parse
from datetime import datetime

# Conversation states
SELECTING_ORDER_TYPE, ENTERING_AMOUNT, SELECTING_CURRENCY, SELECTING_PAYMENT_METHOD, ENTERING_PRICE, WAITING_FOR_SEARCH_TYPE, WAITING_FOR_SEARCH_INPUT, SEARCH_CURRENCY, SEARCH_PAYMENT = range(9)

# Admin conversation states
ROLE_PASSWORD, ADMIN_MENU, CHANGE_PASSWORD, ADD_ADMIN, REMOVE_ADMIN, ADMIN_WORKING, RESET_ADMIN_TIME = range(9, 16)

# Global variables
order_counter = 0
DATA_FILE = "bot_data.json"
ADMIN_DATA_FILE = "admin_data.json"
active_orders = {}
user_recent_orders = {}

# Your credentials
BOT_TOKEN = "8270322197:AAHBGcSY2b7MryjA7XJVEldspLrrHUTHinc"
CHANNEL_ID = "-1002590779764"
ADMIN_ID = 7111040655

# Price limitations for each currency
PRICE_LIMITS = {
    "SYP": {"min": 9000, "max": 15000},
    "EGP": {"min": 30, "max": 50},
    "USD": {"min": 0.8, "max": 1.5}
}

# Payment methods for each currency
PAYMENT_METHODS = {
    "SYP": ["شام كاش", "سيرياتيل كاش", "كاش MTN", "البنك الإسلامي", "بنك البركة", "بنك بيمو"],
    "EGP": ["فودافون كاش", "أورانج كاش", "إتصالات كاش", "إنستا باي", "بنك مصر", "البنك الأهلي", "CIB بنك", "بنك الإسكندرية"],
    "USD": ["شام كاش $", "Airtm", "Payeer", "Paypal", "Revolut", "Neteller", "Skrill", "Webmoney", "Wise", "Whish"]
}

# Currency display names
CURRENCY_DISPLAY = {
    "SYP": "ليرة سورية",
    "EGP": "جنيه مصري",
    "USD": "$"
}

# Default admin data
DEFAULT_ADMIN_DATA = {
    "role_password": "Master911911$$$",
    "admins": [
        {"id": 7111040655, "username": "Oxedia_Admin", "name": "Oxedia Admin", "added_time": datetime.now().isoformat()}
    ],
    "work_sessions": {},
    "current_active_admin": None
}

# Load data from file
def load_data():
    global order_counter, active_orders, user_recent_orders
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                order_counter = data.get('order_counter', 0)
                active_orders = data.get('active_orders', {})
                user_recent_orders = data.get('user_recent_orders', {})
    except:
        order_counter = 0
        active_orders = {}
        user_recent_orders = {}

# Save data from file
def save_data():
    data = {
        'order_counter': order_counter,
        'active_orders': active_orders,
        'user_recent_orders': user_recent_orders
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Load admin data from file
def load_admin_data():
    try:
        if os.path.exists(ADMIN_DATA_FILE):
            with open(ADMIN_DATA_FILE, 'r') as f:
                return json.load(f)
        else:
            return DEFAULT_ADMIN_DATA.copy()
    except:
        return DEFAULT_ADMIN_DATA.copy()

# Save admin data to file
def save_admin_data(admin_data):
    with open(ADMIN_DATA_FILE, 'w') as f:
        json.dump(admin_data, f, indent=4)

# Check if user is admin
def is_admin(user_id, username):
    admin_data = load_admin_data()
    for admin in admin_data['admins']:
        if admin['id'] == user_id:
            return True
        if username and admin.get('username') and admin['username'].lower() == username.lower():
            return True
    return False

# Check if user is master admin
def is_master_admin(user_id, username):
    return user_id == ADMIN_ID or (username and username.lower() == "oxedia_admin")

# Get current active admin info
def get_current_active_admin():
    admin_data = load_admin_data()
    current_admin_id = admin_data.get('current_active_admin')
    if not current_admin_id:
        return None

    for admin in admin_data['admins']:
        if admin['id'] == current_admin_id:
            return admin
    return None

# Format price based on currency
def format_price(price, currency):
    if currency == "USD":
        return format(float(price), '.3f')
    else:
        return format(float(price), '.2f')

# Format amount (always 2 decimal places)
def format_amount(amount):
    return format(float(amount), '.2f')

# Format amount display for ads
def format_amount_display(amount, amount_type):
    if amount_type == 'range':
        # Keep the original separator (- or ~) for display
        return amount
    else:
        return format_amount(float(amount))

# Cleanup user orders
def cleanup_user_orders(user_id):
    if user_id in user_recent_orders:
        user_recent_orders[user_id] = [order_id for order_id in user_recent_orders[user_id] if order_id in active_orders]
        if not user_recent_orders[user_id]:
            del user_recent_orders[user_id]

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **أهلاً بك في Oxedia - منصة الوساطة المالية الرائدة!**\n\n"
        "💎 **خدماتنا:**\n"
        "• تداول آمن للعملات الرقمية\n"
        "• وساطة مضمونة بين البائع والمشتري\n"
        "• أسعار تنافسية وشفافية كاملة\n\n"
        "📈 **لبدء التداول وإضافة إعلان جديد:**\n"
        "↳ إضغط /menu\n\n"
        "🛡️ **جميع الصفقات تحت إشراف إدارة Oxedia**\n"
        "لضمان أمان معاملاتك وحمايتها 💯"
    )
    return ConversationHandler.END

# Done command
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_recent_orders or not user_recent_orders[user_id]:
        await update.message.reply_text("❌ ليس لديك أي إعلانات نشطة لإكمالها.\n\nاستخدم /menu لإنشاء إعلان جديد.")
        return

    recent_order_id = user_recent_orders[user_id][-1]

    if recent_order_id not in active_orders:
        await update.message.reply_text("❌ الإعلان غير موجود أو تم إكماله مسبقاً.")
        cleanup_user_orders(user_id)
        save_data()
        return

    await complete_order(update, context, recent_order_id, user_id)

# Complete order with strikethrough
async def complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, user_id: int):
    order_data = active_orders[order_id]

    try:
        strikethrough_text = create_strikethrough_ad_text(order_data, order_id)

        await context.bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=order_data['channel_message_id'],
            text=strikethrough_text,
            parse_mode='HTML'
        )

        del active_orders[order_id]
        user_recent_orders[user_id].remove(order_id)
        cleanup_user_orders(user_id)

        await update.message.reply_text(
            f"✅ تم إكمال الطلب بنجاح!\n\n"
            f"🆔 رقم الإعلان: #{order_id}\n"
            f" النوع: {order_data['order_type_display']}\n"
            f" الكمية: {order_data['amount']}\n"
            f" السعر: {order_data['price']} {order_data['currency_display']}\n\n"
            f"لإضافة إعلان جديد إضغط على /menu"
        )

        save_data()
        await notify_admin_completion(context, order_id, order_data, user_id)

    except Exception as e:
        error_message = f"❌ فشل في إكمال الطلب: {e}\n\n"
        if "Message to edit not found" in str(e):
            error_message += "الإعلان غير موجود في القناة (ربما تم إكماله مسبقاً)."
        else:
            error_message += "الرجاء المحاولة مرة أخرى أو التواصل مع الأدمن."
        await update.message.reply_text(error_message)

# Notify admin about completion
async def notify_admin_completion(context: ContextTypes.DEFAULT_TYPE, order_id: int, order_data: dict, user_id: int):
    try:
        admin_message = (
            f" تم إكمال الطلب من قبل المعلن ✅!\n"
            f"\n🆔 رقم الإعلان: #{order_id}\n"
            f"👤 التاجر: @{order_data['trader_username'] if order_data['trader_username'] else order_data['trader_name']}\n"
            f"🔗 الرقم: {user_id}\n"
            f" النوع: {order_data['order_type_display']}\n"
            f" الكمية: {order_data['amount']}\n"
            f" السعر: {order_data['price']} {order_data['currency_display']}"
        )

        # Send to active admin if available, otherwise to Oxedia_Admin
        current_admin = get_current_active_admin()
        if current_admin:
            target_admin_id = current_admin['id']
        else:
            target_admin_id = ADMIN_ID

        await context.bot.send_message(chat_id=target_admin_id, text=admin_message)
    except Exception as e:
        print(f"Failed to send admin completion notification: {e}")

# Menu command
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [KeyboardButton("🟢 إنشاء إعلان شراء 🟢"), KeyboardButton("🔴 إنشاء إعلان بيع 🔴")],
        [KeyboardButton("🗓 إعلاناتي"), KeyboardButton("🔍 إبحث عن طلبك")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(" الرجاء اختيار نوع الإعلان أو البحث عن طلبات:", reply_markup=reply_markup)
    return SELECTING_ORDER_TYPE

# Handle "🗓 إعلاناتي" button
async def handle_my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_recent_orders or not user_recent_orders[user_id]:
        await update.message.reply_text("❌ ليس لديك أي إعلانات نشطة.\n\nاستخدم الأزرار أعلاه لإضافة إعلان جديد.")
        return await menu_command(update, context)

    user_active_ads = [(order_id, active_orders[order_id]) for order_id in user_recent_orders[user_id] if order_id in active_orders]

    if not user_active_ads:
        await update.message.reply_text("❌ ليس لديك أي إعلانات نشطة.\n\nاستخدم الأزرار أعلاه لإضافة إعلان جديد.")
        return await menu_command(update, context)

    message_text = "📋 إعلاناتك النشطة:\n\n"
    for order_id, ad_data in user_active_ads:
        message_text += f"\n🆔 رقم الإعلان: #{order_id}\n"
        message_text += f" النوع: {ad_data['order_type_display']}\n"
        message_text += f" الكمية: {ad_data['amount']}\n"
        message_text += f" السعر: {ad_data['price']} {ad_data['currency_display']}\n"
        message_text += f" طريقة الدفع: {ad_data['payment_method']}\n"
        message_text += f"✅ إكمال هذا الطلب: /done_{order_id}\n\n"

    message_text += "\nلإضافة إعلان جديد إضغط على /menu"

    keyboard = [
        [KeyboardButton("🟢 إنشاء إعلان شراء 🟢"), KeyboardButton("🔴 إنشاء إعلان بيع 🔴")],
        [KeyboardButton("🗓 إعلاناتي"), KeyboardButton("🔍 إبحث عن طلبك")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return SELECTING_ORDER_TYPE

# Handle individual ad completion via command
async def handle_specific_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    command_text = update.message.text

    try:
        order_id = int(command_text.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ رقم الإعلان غير صحيح!")
        return await menu_command(update, context)

    if order_id not in active_orders:
        await update.message.reply_text("❌ هذا الإعلان غير موجود او تم إكماله مسبقاً")
        return await menu_command(update, context)

    if user_id not in user_recent_orders or order_id not in user_recent_orders[user_id]:
        await update.message.reply_text("❌ هذا الإعلان لا ينتمي إليك!")
        return await menu_command(update, context)

    await complete_order(update, context, order_id, user_id)
    return await menu_command(update, context)

# Handle search currency selection
async def handle_search_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("SYP - الليرة السورية"), KeyboardButton("EGP - الجنيه المصري")],
        [KeyboardButton("USD - الدولار الأمريكي")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("💰 اختر العملة للبحث:", reply_markup=reply_markup)
    return SEARCH_CURRENCY

# Handle search payment method selection
async def handle_search_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency_input = update.message.text

    if "SYP" in currency_input:
        currency, currency_display = "SYP", "ليرة سورية"
    elif "EGP" in currency_input:
        currency, currency_display = "EGP", "جنيه مصري"
    elif "USD" in currency_input:
        currency, currency_display = "USD", "$"
    else:
        await update.message.reply_text("❌ خطا اضغط على /cancel للإلغاء")
        return SEARCH_CURRENCY

    context.user_data['search_currency'] = currency
    context.user_data['search_currency_display'] = currency_display

    payment_methods = PAYMENT_METHODS[currency]
    keyboard = []
    row = []
    for method in payment_methods:
        row.append(KeyboardButton(method))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"💳 اختر طريقة الدفع للبحث في {currency_display}:", reply_markup=reply_markup)
    return SEARCH_PAYMENT

# Handle search results
async def handle_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    currency = context.user_data.get('search_currency', 'SYP')

    if payment_method not in PAYMENT_METHODS[currency]:
        await update.message.reply_text("❌ خطا اضغط على /cancel للإلغاء")
        return SEARCH_PAYMENT

    matching_orders = [(order_id, order_data) for order_id, order_data in active_orders.items()
                      if order_data['currency'] == currency and order_data['payment_method'] == payment_method]

    if not matching_orders:
        await update.message.reply_text(
            f"❌ لا توجد إعلانات نشطة تطابق بحثك:\n\n"
            f"• العملة: {context.user_data['search_currency_display']}\n"
            f"• طريقة الدفع: {payment_method}\n\n"
            f"الرجاء المحاولة بمعايير بحث أخرى."
        )
        return await menu_command(update, context)

    message_text = f"🔍 نتائج البحث:\n\n• العملة: {context.user_data['search_currency_display']}\n• طريقة الدفع: {payment_method}\n• عدد النتائج: {len(matching_orders)}\n\n━━━━━━━━━━━━━━━━━━\n\n"

    for i, (order_id, order_data) in enumerate(matching_orders, 1):
        message_text += f"📋 الإعلان #{i}:\n🆔 رقم الإعلان: #{order_id}\n النوع: {order_data['order_type_display']}\n الكمية: {order_data['amount']}\n السعر: {order_data['price']} {order_data['currency_display']}\n طريقة الدفع: {order_data['payment_method']}\n━━━━━━━━━━━━━━━━━━\n\n"

    message_text += "👤 للطلب إرسل رقم الإعلان على : @SYR_P2P\n\nللبحث مرة أخرى إضغط على /menu"
    await update.message.reply_text(message_text)

    context.user_data.pop('search_currency', None)
    context.user_data.pop('search_currency_display', None)
    return ConversationHandler.END

# Handle order type selection
async def handle_order_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if user_input == "🔍 إبحث عن طلبك":
        return await handle_search_currency(update, context)

    if user_input == "🗓 إعلاناتي":
        return await handle_my_ads(update, context)

    if user_input == "🟢 إنشاء إعلان شراء 🟢":
        order_type, order_type_display = "BUY", "🟢 شراء USDT 🟢"
    elif user_input == "🔴 إنشاء إعلان بيع 🔴":
        order_type, order_type_display = "SELL", "🔴 بيع USDT 🔴"
    else:
        await update.message.reply_text("❌ خطا اضغط على /cancel للإلغاء")
        return SELECTING_ORDER_TYPE

    context.user_data['order_type'] = order_type
    context.user_data['order_type_display'] = order_type_display

    # Different message based on order type
    if order_type == "BUY":
        amount_message = "الرجاء إدخال الكمية:🟢شراء USDT🟢"
    else:  # SELL
        amount_message = "الرجاء إدخال الكمية:🔴بيع USDT🔴"

    await update.message.reply_text(
        f"{amount_message}\n\n"
        "• يمكن إدخال مبلغ محدد مثل: 500 أو 1000.50\n"
        "• أو يمكن إدخال نطاق مثل: 50-300 أو 50~300\n\n"
        "📝 أمثلة:\n500 (مبلغ محدد)\n100-500 (نطاق من 100 إلى 500)\n100~500 (نطاق من 100 إلى 500)\n"
        "━━━━━━━━━━━━━━━━━━\nإضغط على 👈 /cancel للإلغاء"
    )
    return ENTERING_AMOUNT

# Handle amount input - MODIFIED: Accept both - and ~ as range separators
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()

    # Check if it's a range (contains - or ~)
    is_range = '-' in amount_text or '~' in amount_text

    if not is_range:
        # Single amount
        try:
            amount = float(amount_text)
            if amount <= 0:
                await update.message.reply_text("❌ الرجاء إدخال رقم موجب!")
                return ENTERING_AMOUNT
            context.user_data['amount'] = format_amount(amount)
            context.user_data['amount_type'] = 'single'
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال أرقام فقط! مثال: 500 أو 1000.50 أو 50-300 أو 50~300")
            return ENTERING_AMOUNT
    else:
        # Range amount
        try:
            # Use the original separator for storage
            separator = '-' if '-' in amount_text else '~'
            range_parts = amount_text.split(separator)

            if len(range_parts) != 2:
                await update.message.reply_text("❌ تنسيق النطاق غير صحيح! استخدم: رقم-رقم أو رقم~رقم مثال: 50-300 أو 50~300")
                return ENTERING_AMOUNT

            min_amount, max_amount = float(range_parts[0].strip()), float(range_parts[1].strip())

            if min_amount <= 0 or max_amount <= 0:
                await update.message.reply_text("❌ الرجاء إدخال أرقام موجبة في النطاق!")
                return ENTERING_AMOUNT

            if min_amount >= max_amount:
                await update.message.reply_text("❌ الرقم الأول يجب أن يكون أقل من الرقم الثاني في النطاق!")
                return ENTERING_AMOUNT

            min_formatted, max_formatted = format_amount(min_amount), format_amount(max_amount)
            # Store with original separator
            context.user_data['amount'] = f"{min_formatted}{separator}{max_formatted}"
            context.user_data['amount_type'] = 'range'

        except ValueError:
            await update.message.reply_text("❌ تنسيق النطاق غير صحيح! استخدم: رقم-رقم أو رقم~رقم مثال: 50-300 أو 50~300")
            return ENTERING_AMOUNT

    keyboard = [
        [KeyboardButton("SYP - الليرة السورية"), KeyboardButton("EGP - الجنيه المصري")],
        [KeyboardButton("USD - الدولار الأمريكي")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("💰 الرجاء اختيار العملة التي تريد استخدامها:", reply_markup=reply_markup)
    return SELECTING_CURRENCY

# Handle currency selection
async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency_input = update.message.text

    if "SYP" in currency_input:
        currency, currency_display = "SYP", "ليرة سورية"
    elif "EGP" in currency_input:
        currency, currency_display = "EGP", "جنيه مصري"
    elif "USD" in currency_input:
        currency, currency_display = "USD", "$"
    else:
        await update.message.reply_text("❌ خطا اضغط على /cancel للإلغاء")
        return SELECTING_CURRENCY

    context.user_data['currency'] = currency
    context.user_data['currency_display'] = currency_display
    context.user_data['price_limits'] = PRICE_LIMITS[currency]

    payment_methods = PAYMENT_METHODS[currency]
    keyboard = []
    row = []
    for method in payment_methods:
        row.append(KeyboardButton(method))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"💳 الرجاء اختيار طريقة الدفع للعملة {currency_display}:", reply_markup=reply_markup)
    return SELECTING_PAYMENT_METHOD

# Handle payment method selection
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_method = update.message.text
    currency = context.user_data.get('currency', 'SYP')

    if payment_method not in PAYMENT_METHODS[currency]:
        await update.message.reply_text("❌ خطا اضغط على /cancel للإلغاء")
        return SELECTING_PAYMENT_METHOD

    context.user_data['payment_method'] = payment_method

    price_limits = context.user_data.get('price_limits', PRICE_LIMITS["SYP"])
    currency_display = context.user_data.get('currency_display', 'ليرة سورية')
    currency = context.user_data.get('currency', 'SYP')

    example_price = price_limits['min'] + (price_limits['max'] - price_limits['min']) / 2
    example_formatted = format_price(example_price, currency)

    await update.message.reply_text(
        f"💵 الرجاء إدخال السعر ({currency_display}):\n\n حدود السعر المسموحة:\n"
        f"• من {format_price(price_limits['min'], currency)} إلى {format_price(price_limits['max'], currency)} {currency_display}\n\n"
        f"📝 مثال: {example_formatted}\n━━━━━━━━━━━━━━━━━━\nإضغط على 👈 /cancel للإلغاء"
    )
    return ENTERING_PRICE

# Handle price input
async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_text = update.message.text.strip()

    try:
        price = float(price_text)
        currency = context.user_data.get('currency', 'SYP')
        price_formatted = format_price(price, currency)
        price_float = float(price_formatted)
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال سعر صحيح (أرقام فقط)!")
        return ENTERING_PRICE

    price_limits = context.user_data.get('price_limits', PRICE_LIMITS["SYP"])
    currency_display = context.user_data.get('currency_display', 'ليرة سورية')
    currency = context.user_data.get('currency', 'SYP')

    if price_float < price_limits['min'] or price_float > price_limits['max']:
        await update.message.reply_text(
            f"❌ السعر خارج النطاق المسموح!\n\n يجب أن يكون السعر بين:\n"
            f"• {format_price(price_limits['min'], currency)} و {format_price(price_limits['max'], currency)} {currency_display}\n\n"
            f"الرجاء إدخال سعر ضمن هذا النطاق."
        )
        return ENTERING_PRICE

    context.user_data['price'] = price_formatted
    await finalize_ad_creation(update, context)
    return ConversationHandler.END

# Finalize ad creation and send to channel
async def finalize_ad_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name or "مجهول"

    context.user_data['user_id'] = user_id
    context.user_data['username'] = username
    context.user_data['first_name'] = first_name

    global order_counter
    order_counter += 1
    save_data()

    global active_orders, user_recent_orders
    active_orders[order_counter] = {
        'order_type': context.user_data['order_type'],
        'order_type_display': context.user_data['order_type_display'],
        'amount': context.user_data['amount'],
        'amount_type': context.user_data.get('amount_type', 'single'),
        'price': context.user_data['price'],
        'payment_method': context.user_data['payment_method'],
        'currency': context.user_data['currency'],
        'currency_display': context.user_data['currency_display'],
        'trader_id': user_id,
        'trader_username': username,
        'trader_name': first_name,
        'ad_text': create_ad_text(context.user_data, order_counter),
        'creation_time': datetime.now().isoformat()
    }

    if user_id not in user_recent_orders:
        user_recent_orders[user_id] = []
    user_recent_orders[user_id].append(order_counter)

    save_data()

    ad_text = create_ad_text(context.user_data, order_counter)
    confirmation_text = f"✅ تم إنشاء الإعلان بنجاح!\n\n{ad_text}\n━━━━━━━━━━━━━━━━━━━━━━\nلإلغاء الطلب ❌ إكبس على /done\n\nلإضافة إعلان جديد إضغط على /menu\n"
    await update.message.reply_text(confirmation_text, reply_markup=None)

    try:
        button_text = "📉 بيع العملات" if context.user_data['order_type'] == "BUY" else "📈 شراء العملات"
        order_info = create_ad_text(context.user_data, order_counter)
        encoded_text = urllib.parse.quote(order_info)

        keyboard = [[
            InlineKeyboardButton(button_text, url=f"https://t.me/SYR_P2P"),
            InlineKeyboardButton("📋 مشاركة الإعلان", url=f"https://t.me/share/url?url={encoded_text}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        channel_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=ad_text, reply_markup=reply_markup)
        active_orders[order_counter]['channel_message_id'] = channel_message.message_id
        save_data()

    except Exception as e:
        error_message = f"❌ خطأ في إرسال الإعلان للقناة: {e}\n\nالرجاء التحقق من صلاحيات البوت في القناة"
        await update.message.reply_text(error_message)
        await update.message.reply_text(f"📋 هذا هو نص الإعلان لنشره يدوياً:\n\n{ad_text}")

    await send_admin_notification(context, order_counter, context.user_data)
    context.user_data.clear()

# Send admin notification
async def send_admin_notification(context: ContextTypes.DEFAULT_TYPE, order_number: int, user_data: dict):
    try:
        user_id = user_data['user_id']
        username = user_data.get('username')
        first_name = user_data.get('first_name', 'مجهول')

        admin_message = (
            f"🆔 إعلان جديد: #{order_number}\n\n"
            f"👤 التاجر: {first_name}\n🔗 الرقم: {user_id}\n"
            f" النوع: {user_data['order_type_display']}\n الكمية: {user_data['amount']}\n"
            f" السعر: {user_data['price']} {user_data['currency_display']}\n"
            f" الدفع: {user_data['payment_method']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        keyboard = []
        if username:
            keyboard.append([InlineKeyboardButton("📞 تواصل مع التاجر", url=f"https://t.me/{username}")])
        else:
            keyboard.append([InlineKeyboardButton("📞 تواصل مع التاجر", url=f"tg://user?id={user_id}")])

        keyboard.append([InlineKeyboardButton("إكمال الطلب ✅", callback_data=f"strike_{order_number}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send to active admin if available, otherwise to Oxedia_Admin
        current_admin = get_current_active_admin()
        if current_admin:
            target_admin_id = current_admin['id']
        else:
            target_admin_id = ADMIN_ID

        await context.bot.send_message(chat_id=target_admin_id, text=admin_message, reply_markup=reply_markup, disable_web_page_preview=True)

    except Exception as e:
        print(f"Failed to send admin notification: {e}")

# Handle admin callback actions
async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ غير مصرح لك بهذا الإجراء")
        return

    if data.startswith("strike_"):
        order_id = int(data.replace("strike_", ""))
        await handle_strike_from_callback(update, context, order_id, query.message.message_id)

# Handle strike from callback
async def handle_strike_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int, message_id: int):
    try:
        if order_id not in active_orders:
            await context.bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="❌ الإعلان غير موجود قد يكون تم إكماله")
            return

        order_data = active_orders[order_id]
        strikethrough_text = create_strikethrough_ad_text(order_data, order_id)

        await context.bot.edit_message_text(chat_id=CHANNEL_ID, message_id=order_data['channel_message_id'], text=strikethrough_text, parse_mode='HTML')
        await context.bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text=f"✅ تم إكمال الطلب #{order_id} بنجاح!\n\n النوع: {order_data['order_type_display']}\n👤 التاجر: @{order_data['trader_username'] if order_data['trader_username'] else order_data['trader_name']}")

        del active_orders[order_id]
        user_id = order_data['trader_id']
        if user_id in user_recent_orders and order_id in user_recent_orders[user_id]:
            user_recent_orders[user_id].remove(order_id)
            cleanup_user_orders(user_id)

        save_data()

    except Exception as e:
        error_message = f"❌ فشل في إكمال الطلب: {e}"
        await context.bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text=error_message)

# Enhanced Info command - admin only
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط")
        return

    keyboard = [[KeyboardButton("🔍 البحث برقم المعلن"), KeyboardButton("📋 البحث برقم الإعلان")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "🔍 **اختر طريقة البحث:**\n\n• **🔍 البحث بررقم المعلن** - إدخال الرقم التعريفي للمستخدم\n• **📋 البحث بررقم الإعلان** - إدخال رقم الإعلان المطلوب\n\nللإلغاء إضغط على /cancel\n\nالرجاء الاختيار:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_SEARCH_TYPE

# Handle search type selection
async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_type = update.message.text

    if search_type == "🔍 البحث برقم المعلن":
        context.user_data['search_type'] = 'user_id'
        await update.message.reply_text("🆔 **البحث برقم المعلن**\n\nالرجاء إدخال الرقم التعريفي (ID) للمستخدم:")
        return WAITING_FOR_SEARCH_INPUT

    elif search_type == "📋 البحث برقم الإعلان":
        context.user_data['search_type'] = 'order_id'
        await update.message.reply_text("📋 **البحث برقم الإعلان**\n\nالرجاء إدخال رقم الإعلان المطلوب:")
        return WAITING_FOR_SEARCH_INPUT

    else:
        await update.message.reply_text("❌ اختر طريقة البحث باستخدام الأزرار")
        return await info_command(update, context)

# Handle search input
async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط")
        return ConversationHandler.END

    search_input = update.message.text.strip()
    search_type = context.user_data.get('search_type')

    try:
        if search_type == 'user_id':
            await get_user_info(update, context, int(search_input))
        elif search_type == 'order_id':
            await get_order_info(update, context, int(search_input))
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
        return WAITING_FOR_SEARCH_INPUT

    context.user_data.pop('search_type', None)
    return ConversationHandler.END

# Get user information by user ID
async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        user_info = None
        try:
            user_info = await context.bot.get_chat(user_id)
        except Exception as e:
            print(f"Could not get user info from Telegram: {e}")

        username = f"@{user_info.username}" if user_info and user_info.username else "غير متوفر"
        first_name = user_info.first_name if user_info else "غير معروف"

        active_ads_count, total_ads_count, user_ads_details = 0, 0, []

        if user_id in user_recent_orders:
            total_ads_count = len(user_recent_orders[user_id])
            active_ads_count = len([order_id for order_id in user_recent_orders[user_id] if order_id in active_orders])

            for order_id in user_recent_orders[user_id]:
                if order_id in active_orders:
                    ad_data = active_orders[order_id]
                    user_ads_details.append({
                        'order_id': order_id, 'type': ad_data['order_type_display'], 'amount': ad_data['amount'],
                        'price': ad_data['price'], 'currency': ad_data['currency_display'], 'payment_method': ad_data['payment_method']
                    })

        user_info_text = (
            f"👤 معلومات المعلن\n\n🆔 الرقم التعريفي: {user_id}\n📛 الاسم: {first_name}\n"
            f"🔗 اليوزر: {username}\n📞 الرقم: غير متوفر\n\n📊 إحصائيات الإعلانات:\n"
            f"• 📈 الإعلانات النشطة: {active_ads_count}\n• 📋 إجمالي الإعلانات: {total_ads_count}\n"
            f"• 📉 الإعلانات المنتهية: {total_ads_count - active_ads_count}\n"
        )

        if user_ads_details:
            user_info_text += f"\n📋 الإعلانات النشطة:\n"
            for ad in user_ads_details:
                user_info_text += f"• 🆔 #{ad['order_id']}: {ad['type']} - {ad['amount']} - {ad['price']} {ad['currency']} - {ad['payment_method']}\n"

        user_info_text += f"\n⏰ آخر فحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        keyboard = []
        contact_button = InlineKeyboardButton("📞 التواصل مع المستخدم", url=f"tg://user?id={user_id}")
        keyboard.append([contact_button])

        if user_info and user_info.username:
            username_button = InlineKeyboardButton("🔗 التواصل عبر اليوزر", url=f"https://t.me/{user_info.username}")
            keyboard.append([username_button])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(user_info_text, reply_markup=reply_markup, disable_web_page_preview=True)

    except Exception as e:
        error_message = f"❌ حدث خطأ أثناء جلب المعلومات:\n\n• قد يكون الرقم التعريفي غير صحيح\n• أو المستخدم لم يتفاعل مع البوت مسبقاً\n• الخطأ: {str(e)}"
        await update.message.reply_text(error_message)

# Get order information by order ID
async def get_order_info(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    try:
        if order_id not in active_orders:
            await update.message.reply_text(f"❌ الإعلان غير موجود!\n\nرقم الإعلان #{order_id} غير موجود أو تم إكماله مسبقاً.")
            return

        order_data = active_orders[order_id]
        user_id = order_data['trader_id']

        user_info = None
        try:
            user_info = await context.bot.get_chat(user_id)
        except Exception as e:
            print(f"Could not get user info from Telegram: {e}")

        username = f"@{user_info.username}" if user_info and user_info.username else "غير متوفر"
        first_name = user_info.first_name if user_info else "غير معروف"

        user_active_ads = len([oid for oid in user_recent_orders.get(user_id, []) if oid in active_orders]) if user_id in user_recent_orders else 0

        order_info_text = (
            f"📋 معلومات الإعلان\n\n🆔 رقم الإعلان: #{order_id}\n👤 المعلن: {first_name}\n"
            f"🔗 اليوزر: {username}\n🆔 رقم المعلن: {user_id}\n\n📊 تفاصيل الإعلان:\n"
            f"• النوع: {order_data['order_type_display']}\n• الكمية: {order_data['amount']}\n"
            f"• السعر: {order_data['price']} {order_data['currency_display']}\n• طريقة الدفع: {order_data['payment_method']}\n"
            f"• العملة: {order_data['currency_display']}\n• وقت الإنشاء: {order_data.get('creation_time', 'غير معروف')}\n"
            f"\n📈 إعلانات المعلن النشطة: {user_active_ads}\n\n⏰ آخر فحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        keyboard = []
        if user_info and user_info.username:
            keyboard.append([InlineKeyboardButton("📞 التواصل مع المعلن", url=f"https://t.me/{user_info.username}")])
        else:
            keyboard.append([InlineKeyboardButton("📞 التواصل مع المعلن", url=f"tg://user?id={user_id}")])

        keyboard.append([InlineKeyboardButton("✅ إكمال هذا الطلب", callback_data=f"strike_{order_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(order_info_text, reply_markup=reply_markup, disable_web_page_preview=True)

    except Exception as e:
        error_message = f"❌ حدث خطأ أثناء جلب معلومات الإعلان:\n\n• قد يكون رقم الإعلان غير صحيح\n• الخطأ: {str(e)}"
        await update.message.reply_text(error_message)

# Create formatted ad text for channel
def create_ad_text(user_data, order_number):
    amount_display = format_amount_display(user_data['amount'], user_data.get('amount_type', 'single'))

    # Get current active admin for contact info
    current_admin = get_current_active_admin()
    if current_admin and current_admin.get('username'):
        contact_info = f"@{current_admin['username']}"
    else:
        contact_info = "@Oxedia_Admin"

    return (
        f"🆔 رقم الإعلان: {order_number}\n\n نوع الإعلان: {user_data['order_type_display']}\n"
        f" الكمية: {amount_display}\n السعر: {user_data['price']} {user_data['currency_display']}\n"
        f" طريقة الدفع: {user_data['payment_method']}\n عمولة الوسيط: 0.5%\n\n"
        f"👤  للطلب تواصل مع : {contact_info}\n\n➕ لإضافة إعلان جديد تواصل مع : @Oxediabot\n"
    )

# Create strikethrough ad text using HTML formatting
def create_strikethrough_ad_text(user_data, order_number):
    amount_display = format_amount_display(user_data['amount'], user_data.get('amount_type', 'single'))

    # Get current active admin for contact info
    current_admin = get_current_active_admin()
    if current_admin and current_admin.get('username'):
        contact_info = f"@{current_admin['username']}"
    else:
        contact_info = "@Oxedia_Admin"

    return (
        f"<s>🆔 رقم الإعلان: {order_number}</s>\n<s></s>\n"
        f"<s> نوع الإعلان: {user_data['order_type_display']}</s>\n<s> الكمية: {amount_display}</s>\n"
        f"<s> السعر: {user_data['price']} {user_data['currency_display']}</s>\n<s> طريقة الدفع: {user_data['payment_method']}</s>\n"
        f"<s> عمولة الوسيط: 0.5%</s>\n\n<s>👤  لحجز الإعلان او الطلب تواصل مع : {contact_info}</s>\n\n"
        f"<s>➕ لإضافة إعلان جديد تواصل مع : @Oxediabot</s>\n<s></s>\n\n✅ <b>تم إكمال الطلب</b>"
    )

# Cancel command
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👈 تم الإلغاء, إضغط على /menu لإنشاء إعلان جديد", reply_markup=None)
    context.user_data.clear()
    return ConversationHandler.END

# Handle invalid messages during conversation
async def handle_invalid_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    await update.message.reply_text(
        "❌ الرجاء استخدام الأزرار المقدمة أو اتباع التعليمات.\n\nإضغط على /cancel للإلغاء\n\nإضغط على /menu للعودة للقائمة الرئيسية"
    )

# Reset counter command (admin only)
async def reset_counter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط")
        return

    global order_counter
    order_counter = 0
    save_data()
    await update.message.reply_text("✅ تم إعادة عداد الإعلانات إلى 0")

# Show current counter
async def show_counter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global order_counter
    await update.message.reply_text(f" عداد الإعلانات الحالي: {order_counter}")

# Admin stats command
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمسؤول فقط")
        return

    global order_counter, active_orders, user_recent_orders
    active_users = len(user_recent_orders)
    total_user_orders = sum(len(orders) for orders in user_recent_orders.values())

    stats_text = (
        f" إحصائيات المسؤول\n\n🆔 عداد الإعلانات الحالي: {order_counter}\n"
        f"📋 الإعلانات النشطة: {len(active_orders)}\n👥 المستخدمون النشطون: {active_users}\n"
        f"📈 إجمالي إعلانات المستخدمين: {total_user_orders}\n👤 رقم المسؤول: {ADMIN_ID}\n"
        f"📢 رقم القناة: {CHANNEL_ID}\n⏰ وقت تشغيل البوت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    await update.message.reply_text(stats_text)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 أوامر البوت:\n\n/start - بدء البوت\n/menu - القائمة الرئيسية (إنشاء إعلان أو البحث)\n"
        "/done - إكمال إعلانك الأخير\n/help - عرض هذه الرسالة\n\n📝 تنسيق الإعلان:\n"
        "• نوع الإعلان: شراء أو بيع\n• الكمية: أرقام فقط أو نطاق (مثال: 50-300 أو 50~300)\n"
        "• العملة: SYP (ليرة سورية), EGP (جنيه مصري), USD ($)\n• طريقة الدفع: تختلف حسب العملة المختارة\n"
        "• السعر: أرقام فقط ضمن النطاق المسموح\n\n حدود الأسعار:\n• الليرة السورية: 9000.00 - 15000.00 ليرة\n"
        "• الجنيه المصري: 30.00 - 50.00 جنيه\n• الدولار الأمريكي: 0.800 - 1.500 دولار\n\n"
        " يمكنك إكمال✅ الطلب بالضغط على /done\nيمكنك إنشاء طلب جديد بالضغط على /menu\n\n"
        "👤 للحجز او الطلب: @SYR_P2P\n➕ لإضافة إعلان جديد: @Oxediabot\n عمولة الوسيط: 0.5%"
    )

# ==================== NEW ADMIN MANAGEMENT FEATURES ====================

# Role command - password protected admin access
async def role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    # Check if user is master admin
    if not is_master_admin(user_id, username):
        await update.message.reply_text("❌ هذا الأمر للمسؤول الرئيسي فقط")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔐 **الوصول إلى لوحة الإدارة**\n\n"
        "الرجاء إدخال كلمة المرور للوصول إلى لوحة الإدارة:\n\n"
        "إضغط على /cancel للإلغاء"
    )
    return ROLE_PASSWORD

# Handle role password input
async def handle_role_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password_input = update.message.text.strip()
    admin_data = load_admin_data()

    if password_input != admin_data['role_password']:
        await update.message.reply_text("❌ كلمة المرور غير صحيحة!\n\nالرجاء المحاولة مرة أخرى أو إضغط /cancel للإلغاء")
        return ROLE_PASSWORD

    # Password correct, show admin menu
    keyboard = [
        [KeyboardButton("تغيير كلمة السر"), KeyboardButton("إضافة أدمن")],
        [KeyboardButton("إزالة أدمن"), KeyboardButton("قائمة الإدارة")],
        [KeyboardButton("وقت عمل الأدمن"), KeyboardButton("تصفير الوقت")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "👨‍💼 **لوحة إدارة Oxedia**\n\n"
        "الرجاء اختيار الإجراء المطلوب:\n\n"
        "تغيير كلمة السر - تغيير كلمة مرور الوصول\n"
        "إضافة أدمن - إضافة مسؤول جديد\n"
        "إزالة أدمن - حذف مسؤول\n"
        "قائمة الإدارة - عرض قائمة المسؤولين\n"
        "وقت عمل الأدمن - عرض أوقات عمل المسؤولين\n"
        "تصفير الوقت - إعادة ضبط وقت عمل مسؤول محدد\n\n"
        "إضغط على /cancel للإلغاء",
        reply_markup=reply_markup
    )
    return ADMIN_MENU

# Handle admin menu selection
async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == "تغيير كلمة السر":
        await update.message.reply_text(
            "🔐 **تغيير كلمة المرور**\n\n"
            "الرجاء إدخال كلمة المرور الجديدة:\n\n"
            "إضغط على /cancel للإلغاء"
        )
        return CHANGE_PASSWORD

    elif choice == "إضافة أدمن":
        await update.message.reply_text(
            "👨‍💼 **إضافة مسؤول جديد**\n\n"
            "الرجاء إرسال المعرف الرقمي (ID) للمستخدم الذي تريد إضافته كمسؤول:\n\n"
            "إضغط على /cancel للإلغاء"
        )
        return ADD_ADMIN

    elif choice == "إزالة أدمن":
        admin_data = load_admin_data()
        if len(admin_data['admins']) <= 1:
            await update.message.reply_text("❌ لا يمكن حذف المسؤول الوحيد المتبقي!")
            return await show_admin_menu(update, context)

        admins_list = "📋 **قائمة المسؤولين الحاليين:**\n\n"
        for i, admin in enumerate(admin_data['admins'], 1):
            admins_list += f"{i}. {admin.get('name', 'غير معروف')} (ID: {admin['id']})\n"

        admins_list += "\nالرجاء إرسال المعرف الرقمي (ID) للمسؤول الذي تريد إزالته:\n\nإضغط على /cancel للإلغاء"
        await update.message.reply_text(admins_list)
        return REMOVE_ADMIN

    elif choice == "قائمة الإدارة":
        await show_admins_list(update, context)
        return await show_admin_menu(update, context)

    elif choice == "وقت عمل الأدمن":
        await show_admin_work_times(update, context)
        return await show_admin_menu(update, context)

    elif choice == "تصفير الوقت":
        admin_data = load_admin_data()

        if not admin_data.get('work_sessions'):
            await update.message.reply_text("❌ لا توجد بيانات وقت عمل للمسؤولين!")
            return await show_admin_menu(update, context)

        admins_list = "🔄 **تصفير وقت عمل المسؤولين**\n\n"
        admins_list += "📋 المسؤولين الذين لديهم بيانات وقت عمل:\n\n"

        for admin_id, sessions in admin_data['work_sessions'].items():
            # Find admin name
            admin_name = "غير معروف"
            for admin in admin_data['admins']:
                if str(admin['id']) == admin_id:
                    admin_name = admin.get('name', 'غير معروف')
                    break
            admins_list += f"• {admin_name} (ID: {admin_id}) - {len(sessions)} جلسة عمل\n"

        admins_list += "\nالرجاء إرسال المعرف الرقمي (ID) للمسؤول الذي تريد تصفير وقت عمله:\n\nإضغط على /cancel للإلغاء"
        await update.message.reply_text(admins_list)
        return RESET_ADMIN_TIME

    else:
        await update.message.reply_text("❌ اختر خياراً صحيحاً من القائمة")
        return ADMIN_MENU

# Show admin menu
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("تغيير كلمة السر"), KeyboardButton("إضافة أدمن")],
        [KeyboardButton("إزالة أدمن"), KeyboardButton("قائمة الإدارة")],
        [KeyboardButton("وقت عمل الأدمن"), KeyboardButton("تصفير الوقت")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("👨‍💼 اختر الإجراء المطلوب:", reply_markup=reply_markup)
    return ADMIN_MENU

# Handle password change
async def handle_change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_password = update.message.text.strip()

    if not new_password:
        await update.message.reply_text("❌ كلمة المرور لا يمكن أن تكون فارغة!")
        return CHANGE_PASSWORD

    admin_data = load_admin_data()
    admin_data['role_password'] = new_password
    save_admin_data(admin_data)

    await update.message.reply_text(f"✅ تم تغيير كلمة المرور بنجاح!\n\nكلمة المرور الجديدة: {new_password}")
    return await show_admin_menu(update, context)

# Handle add admin
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!\n\nإضغط على /cancel للإلغاء")
        return ADD_ADMIN

    admin_data = load_admin_data()

    # Check if admin already exists
    for admin in admin_data['admins']:
        if admin['id'] == new_admin_id:
            await update.message.reply_text("❌ هذا المسؤول موجود بالفعل في القائمة!")
            return await show_admin_menu(update, context)

    # Get user info from Telegram
    try:
        user_info = await context.bot.get_chat(new_admin_id)
        username = user_info.username
        name = user_info.first_name or "غير معروف"
    except Exception as e:
        username = None
        name = "غير معروف"

    # Add new admin
    new_admin = {
        'id': new_admin_id,
        'username': username,
        'name': name,
        'added_time': datetime.now().isoformat(),
        'added_by': update.message.from_user.id
    }

    admin_data['admins'].append(new_admin)
    save_admin_data(admin_data)

    await update.message.reply_text(
        f"✅ تم إضافة المسؤول بنجاح!\n\n"
        f"🆔 الرقم: {new_admin_id}\n"
        f"📛 الاسم: {name}\n"
        f"🔗 اليوزر: @{username if username else 'غير متوفر'}\n"
        f"⏰ وقت الإضافة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return await show_admin_menu(update, context)

# Handle remove admin - UPDATED VERSION with session termination
async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id_to_remove = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!\n\nإضغط على /cancel للإلغاء")
        return REMOVE_ADMIN

    admin_data = load_admin_data()

    # Check if trying to remove master admin
    if admin_id_to_remove == ADMIN_ID:
        await update.message.reply_text("❌ لا يمكن حذف المسؤول الرئيسي!")
        return await show_admin_menu(update, context)

    # Find and remove admin
    for i, admin in enumerate(admin_data['admins']):
        if admin['id'] == admin_id_to_remove:
            removed_admin = admin_data['admins'].pop(i)

            # NEW: Check if this admin is currently active and force stop their session
            if admin_data.get('current_active_admin') == admin_id_to_remove:
                admin_data['current_active_admin'] = None

                # Update work session end time and duration for the removed admin
                if str(admin_id_to_remove) in admin_data['work_sessions']:
                    sessions = admin_data['work_sessions'][str(admin_id_to_remove)]
                    if sessions and not sessions[-1].get('end_time'):
                        start_time = datetime.fromisoformat(sessions[-1]['start_time'])
                        end_time = datetime.now()
                        duration = end_time - start_time

                        # Format duration
                        hours, remainder = divmod(duration.total_seconds(), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        duration_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

                        sessions[-1]['end_time'] = end_time.isoformat()
                        sessions[-1]['duration'] = duration_str

            save_admin_data(admin_data)

            await update.message.reply_text(
                f"✅ تم إزالة المسؤول بنجاح!\n\n"
                f"🆔 الرقم: {removed_admin['id']}\n"
                f"📛 الاسم: {removed_admin.get('name', 'غير معروف')}\n"
                f"⏰ وقت الإزالة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🔴 تم إيقاف جلسة العمل النشطة لهذا المسؤول تلقائياً."
            )
            return await show_admin_menu(update, context)

    await update.message.reply_text("❌ لم يتم العثور على مسؤول بهذا المعرف!")
    return await show_admin_menu(update, context)

# Handle reset admin time
async def handle_reset_admin_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id_to_reset = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!\n\nإضغط على /cancel للإلغاء")
        return RESET_ADMIN_TIME

    admin_data = load_admin_data()

    # Check if admin exists
    admin_exists = False
    admin_name = "غير معروف"
    for admin in admin_data['admins']:
        if admin['id'] == admin_id_to_reset:
            admin_exists = True
            admin_name = admin.get('name', 'غير معروف')
            break

    if not admin_exists:
        await update.message.reply_text("❌ لم يتم العثور على مسؤول بهذا المعرف!")
        return await show_admin_menu(update, context)

    # Reset work sessions for this admin
    if str(admin_id_to_reset) in admin_data['work_sessions']:
        # Clear all work sessions for this admin
        admin_data['work_sessions'][str(admin_id_to_reset)] = []
        save_admin_data(admin_data)

        await update.message.reply_text(
            f"✅ تم تصفير وقت عمل المسؤول بنجاح!\n\n"
            f"👤 المسؤول: {admin_name}\n"
            f"🆔 الرقم: {admin_id_to_reset}\n"
            f"⏰ وقت التصفير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"تم حذف جميع جلسات العمل السابقة لهذا المسؤول."
        )
    else:
        await update.message.reply_text(
            f"ℹ️ لا توجد بيانات وقت عمل للمسؤول المحدد!\n\n"
            f"👤 المسؤول: {admin_name}\n"
            f"🆔 الرقم: {admin_id_to_reset}\n\n"
            f"لم يقم هذا المسؤول بتسجيل أي جلسات عمل سابقة."
        )

    return await show_admin_menu(update, context)

# Show admins list
async def show_admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_data = load_admin_data()

    if not admin_data['admins']:
        await update.message.reply_text("لايوجد بيانات لعرضها")
        return

    admins_text = "👨‍💼 **قائمة مسؤولي Oxedia**\n\n"

    for i, admin in enumerate(admin_data['admins'], 1):
        added_time = datetime.fromisoformat(admin['added_time']).strftime('%Y-%m-%d %H:%M:%S')
        admins_text += f"{i}. **{admin.get('name', 'غير معروف')}**\n"
        admins_text += f"   🆔 الرقم: `{admin['id']}`\n"
        admins_text += f"   🔗 اليوزر: @{admin.get('username', 'غير متوفر')}\n"
        admins_text += f"   ⏰ وقت الإضافة: {added_time}\n"
        if admin['id'] == ADMIN_ID:
            admins_text += f"   👑 **المسؤول الرئيسي**\n"
        admins_text += "\n"

    current_active = get_current_active_admin()
    if current_active:
        username = f"@{current_active.get('username', 'غير معروف')}" if current_active.get('username') else "غير معروف"
        admins_text += f"🟢 **المسؤول النشط حالياً:** {current_active.get('name', 'غير معروف')} ({username})\n"
    else:
        admins_text += "🔴 **لا يوجد مسؤول نشط حالياً**\n"

    admins_text += f"\n📊 **إجمالي المسؤولين:** {len(admin_data['admins'])}"

    await update.message.reply_text(admins_text, parse_mode=None)

# Show admin work times
async def show_admin_work_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_data = load_admin_data()
    work_sessions = admin_data.get('work_sessions', {})

    # Check if there's a current active admin
    current_active = get_current_active_admin()

    # If no work sessions and no active admin, show simple message
    if not work_sessions and not current_active:
        await update.message.reply_text("لايوجد أدمن يعمل الأن")
        return

    # If there are work sessions but no active admin
    if not current_active:
        await update.message.reply_text("لايوجد أدمن يعمل الأن")
        return

    # If we reach here, there's an active admin
    work_times_text = "📊 أوقات عمل مسؤولي Oxedia\n\n"

    username = f"@{current_active.get('username', 'غير معروف')}" if current_active.get('username') else "غير معروف"
    work_times_text += f"🟢 المسؤول النشط حالياً: {current_active.get('name', 'غير معروف')} ({username})\n\n"

    if not work_sessions:
        await update.message.reply_text("لايوجد بيانات لعرضها")
        return

    # Check if there are any actual work sessions with data
    has_work_data = False
    for admin_id, sessions in work_sessions.items():
        if sessions:  # If this admin has sessions
            has_work_data = True
            break

    if not has_work_data:
        await update.message.reply_text("لايوجد بيانات لعرضها")
        return

    for admin_id, sessions in work_sessions.items():
        # Find admin name
        admin_name = "غير معروف"
        admin_username = "غير متوفر"
        for admin in admin_data['admins']:
            if admin['id'] == int(admin_id):
                admin_name = admin.get('name', 'غير معروف')
                admin_username = f"@{admin.get('username')}" if admin.get('username') else "غير متوفر"
                break

        work_times_text += f"👤 {admin_name} ({admin_username})\n"

        if not sessions:
            work_times_text += "   ❌ لا توجد جلسات عمل\n\n"
            continue

        for i, session in enumerate(sessions[-5:], 1):  # Show last 5 sessions
            start_time = datetime.fromisoformat(session['start_time']).strftime('%Y-%m-%d %H:%M:%S')
            if session.get('end_time'):
                end_time = datetime.fromisoformat(session['end_time']).strftime('%Y-%m-%d %H:%M:%S')
                duration = session.get('duration', 'غير محسوب')
                work_times_text += f"   {i}. ⏰ {start_time} → {end_time} ({duration})\n"
            else:
                work_times_text += f"   {i}. ⏰ {start_time} → 🟢 مستمر\n"

        work_times_text += "\n"

    # Remove parse_mode to avoid Markdown errors
    await update.message.reply_text(work_times_text)

# P2P command - start admin work session
async def p2p_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    # Check if user is admin
    if not is_admin(user_id, username):
        await update.message.reply_text("❌ هذا الأمر للمسؤولين فقط")
        return

    admin_data = load_admin_data()

    # Check if there's already an active admin
    current_active_admin = admin_data.get('current_active_admin')
    if current_active_admin:
        if current_active_admin == user_id:
            await update.message.reply_text("🟢 **أنت المسؤول النشط حالياً!**\n\nيمكنك الآن استخدام جميع صلاحيات المسؤول.")
        else:
            # Find the active admin's name
            active_admin_name = "غير معروف"
            active_admin_username = "غير متوفر"
            for admin in admin_data['admins']:
                if admin['id'] == current_active_admin:
                    active_admin_name = admin.get('name', 'غير معروف')
                    active_admin_username = f"@{admin.get('username')}" if admin.get('username') else "غير متوفر"
                    break

            await update.message.reply_text(f"🔴 **يوجد أدمن أخر يعمل الأن!**\n\nالمسؤول النشط حالياً: {active_admin_name} ({active_admin_username})\n\nالرجاء الانتظار حتى ينتهي من عمله.")
        return

    # Start new work session
    admin_data['current_active_admin'] = user_id

    # Record work session start
    if str(user_id) not in admin_data['work_sessions']:
        admin_data['work_sessions'][str(user_id)] = []

    admin_data['work_sessions'][str(user_id)].append({
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'duration': None
    })

    save_admin_data(admin_data)

    # Find admin name
    admin_name = "غير معروف"
    admin_username = "غير متوفر"
    for admin in admin_data['admins']:
        if admin['id'] == user_id:
            admin_name = admin.get('name', 'غير معروف')
            admin_username = f"@{admin.get('username')}" if admin.get('username') else "غير متوفر"
            break

    await update.message.reply_text(
        f"🟢 **بدء جلسة العمل**\n\n"
        f"✅ تم تفعيل وضع المسؤول بنجاح!\n\n"
        f"👤 المسؤول: {admin_name} ({admin_username})\n"
        f"⏰ وقت البدء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"يمكنك الآن استخدام جميع صلاحيات المسؤول.\n\n"
        f"لإنهاء الجلسة، استخدم الأمر /stop_p2p"
    )

# Stop P2P command - end admin work session
async def stop_p2p_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    admin_data = load_admin_data()

    # Check if user is the current active admin
    if admin_data.get('current_active_admin') != user_id:
        await update.message.reply_text("❌ أنت لست المسؤول النشط حالياً!")
        return

    # End work session
    admin_data['current_active_admin'] = None

    # Update work session end time and duration
    if str(user_id) in admin_data['work_sessions']:
        sessions = admin_data['work_sessions'][str(user_id)]
        if sessions and not sessions[-1].get('end_time'):
            start_time = datetime.fromisoformat(sessions[-1]['start_time'])
            end_time = datetime.now()
            duration = end_time - start_time

            # Format duration
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

            sessions[-1]['end_time'] = end_time.isoformat()
            sessions[-1]['duration'] = duration_str

    save_admin_data(admin_data)

    await update.message.reply_text(
        f"🔴 **إنهاء جلسة العمل**\n\n"
        f"✅ تم إنهاء وضع المسؤول بنجاح!\n\n"
        f"⏰ وقت الانتهاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"⏱️ مدة الجلسة: {duration_str if 'duration_str' in locals() else 'غير محسوبة'}\n\n"
        f"لبدء جلسة جديدة، استخدم الأمر /p2p"
    )

# Cancel admin conversation
async def cancel_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👈 تم إلغاء العملية", reply_markup=None)
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for creating ads and search
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('menu', menu_command)
        ],
        states={
            SELECTING_ORDER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_type)],
            ENTERING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            SELECTING_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency)],
            SELECTING_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_method)],
            ENTERING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price)],
            SEARCH_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_payment)],
            SEARCH_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_results)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )

    # Conversation handler for info command (admin only)
    info_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('info', info_command)],
        states={
            WAITING_FOR_SEARCH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_type)],
            WAITING_FOR_SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )

    # Conversation handler for role command (admin management)
    role_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('role', role_command)],
        states={
            ROLE_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role_password)],
            ADMIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_menu)],
            CHANGE_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_password)],
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_admin)],
            REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin)],
            RESET_ADMIN_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reset_admin_time)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_command)]
    )

    # Add handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('done', done_command))
    app.add_handler(CommandHandler('reset_counter', reset_counter_command))
    app.add_handler(CommandHandler('counter', show_counter_command))
    app.add_handler(CommandHandler('admin_stats', admin_stats_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('p2p', p2p_command))
    app.add_handler(CommandHandler('stop_p2p', stop_p2p_command))
    app.add_handler(conv_handler)
    app.add_handler(info_conv_handler)
    app.add_handler(role_conv_handler)

    # Add handler for specific ad completion commands
    app.add_handler(MessageHandler(filters.Regex(r'^/done_\d+$'), handle_specific_done))

    # Add handler for admin callback actions
    app.add_handler(CallbackQueryHandler(handle_admin_actions, pattern=r"^strike_"))

    # Add handler for invalid messages during conversation
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_message))

    print("🤖 P2P Crypto Fiat Bot is running...")
    print(f"📢 Target Channel: {CHANNEL_ID}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"📞 Contact: @SYR_P2P")
    app.run_polling()

if __name__ == "__main__":
    # Initialize data
    load_data()
    main()