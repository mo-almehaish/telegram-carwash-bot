import re
import sqlite3
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from services import services, extras, WORKING_HOURS, CONTACT, LOCATION

TOKEN = "8497565387:AAFwiZtDyHr9hl6jWlEs4txIK62X8VX0Qc0"
OWNER_ID = 660478993

DB_NAME = "nova.db"
MAX_CARS_PER_SLOT = 3
BOOKING_DAYS_AHEAD = 7

DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
CHOICE_RE = re.compile(r"^\s*(\d+)")

DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

LANG_MENU = ReplyKeyboardMarkup(
    [["العربية"], ["English"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

AR_MAIN_MENU = ReplyKeyboardMarkup(
    [["1", "2", "3"], ["4", "5", "6"], ["7", "0"]],
    resize_keyboard=True,
)

EN_MAIN_MENU = ReplyKeyboardMarkup(
    [["1", "2", "3"], ["4", "5", "6"], ["7", "0"]],
    resize_keyboard=True,
)

CAR_SIZES = {
    "1": {"ar": "صغيرة", "en": "Small"},
    "2": {"ar": "وسط", "en": "Medium"},
    "3": {"ar": "كبيرة", "en": "Large"},
}

PAYMENT_METHODS = {
    "1": {"ar": "الدفع عند الوصول", "en": "Pay on arrival"},
    "2": {"ar": "التحويل البنكي", "en": "Bank transfer"},
}

BOOKING_ORDER = ["name", "phone", "service", "car", "extras", "date", "time", "payment", "confirm"]

CLEAR_MAP = {
    "name": [
        "customer_name", "customer_phone", "service_id", "service_name",
        "car_size_id", "car_size_ar", "car_size_name", "extras",
        "available_dates", "date", "date_display", "available_slots",
        "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "phone": [
        "customer_phone", "service_id", "service_name",
        "car_size_id", "car_size_ar", "car_size_name", "extras",
        "available_dates", "date", "date_display", "available_slots",
        "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "service": [
        "service_id", "service_name", "car_size_id", "car_size_ar",
        "car_size_name", "extras", "available_dates", "date",
        "date_display", "available_slots", "time", "payment_id",
        "payment_name", "total", "booking_number"
    ],
    "car": [
        "car_size_id", "car_size_ar", "car_size_name", "extras",
        "available_dates", "date", "date_display", "available_slots",
        "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "extras": [
        "extras", "available_dates", "date", "date_display", "available_slots",
        "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "date": [
        "available_dates", "date", "date_display", "available_slots",
        "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "time": [
        "available_slots", "time", "payment_id", "payment_name", "total", "booking_number"
    ],
    "payment": [
        "payment_id", "payment_name", "total", "booking_number"
    ],
    "confirm": [],
}


def normalize_text(text: str) -> str:
    return text.translate(DIGIT_TRANSLATION).strip()


def extract_choice(text: str) -> str:
    text = normalize_text(text)
    match = CHOICE_RE.match(text)
    if match:
        return match.group(1)
    return text


def normalize_phone(phone: str) -> str:
    phone = normalize_text(phone)
    return "".join(ch for ch in phone if ch.isdigit())


def create_tables() -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_number TEXT UNIQUE,
            customer_name TEXT,
            customer_phone TEXT,
            service_id TEXT,
            service_name TEXT,
            car_size_id TEXT,
            car_size_ar TEXT,
            car_size_name TEXT,
            extras TEXT,
            date TEXT,
            date_display TEXT,
            time TEXT,
            payment_id TEXT,
            payment_name TEXT,
            total REAL,
            status TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def next_booking_number() -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM bookings")
    next_id = cur.fetchone()[0]
    conn.close()
    return f"NOVA-{1000 + next_id}"


def add_booking(data: dict) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO bookings (
            booking_number,
            customer_name,
            customer_phone,
            service_id,
            service_name,
            car_size_id,
            car_size_ar,
            car_size_name,
            extras,
            date,
            date_display,
            time,
            payment_id,
            payment_name,
            total,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["booking_number"],
            data["customer_name"],
            data["customer_phone"],
            data["service_id"],
            data["service_name"],
            data["car_size_id"],
            data["car_size_ar"],
            data["car_size_name"],
            data["extras"],
            data["date"],
            data["date_display"],
            data["time"],
            data["payment_id"],
            data["payment_name"],
            data["total"],
            data["status"],
            data["created_at"],
        ),
    )
    conn.commit()
    conn.close()


def count_bookings(date: str, time: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM bookings
        WHERE date = ?
          AND time = ?
          AND status = 'confirmed'
        """,
        (date, time),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_booking_by_phone(phone: str):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM bookings
        WHERE customer_phone = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (phone,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "ar")


def set_lang(context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    context.user_data["lang"] = lang
    context.user_data["lang_selected"] = True


def clear_booking_keys(data: dict, stage: str) -> None:
    for key in CLEAR_MAP.get(stage, []):
        data.pop(key, None)


def get_day_name(weekday: int, lang: str) -> str:
    return DAYS_AR[weekday] if lang == "ar" else DAYS_EN[weekday]


def get_service_price(service: dict, size_id: str) -> int:
    if "prices" in service and isinstance(service["prices"], dict):
        size_ar = CAR_SIZES[size_id]["ar"]
        return int(service["prices"].get(size_ar, 0))

    if size_id == "1":
        return int(service.get("small", 0))
    if size_id == "2":
        return int(service.get("medium", 0))
    return int(service.get("large", 0))


def get_service_name(service_id: str, lang: str) -> str:
    service = services.get(service_id)
    if not service:
        return ""
    return service["name_ar"] if lang == "ar" else service["name_en"]


def get_extra_name(extra_id: str, lang: str) -> str:
    extra = extras.get(extra_id)
    if not extra:
        return ""
    return extra["name_ar"] if lang == "ar" else extra["name_en"]


def get_car_name(size_id: str, lang: str) -> str:
    size = CAR_SIZES.get(size_id, {})
    return size.get("ar", "") if lang == "ar" else size.get("en", "")


def get_payment_name(payment_id: str, lang: str) -> str:
    pay = PAYMENT_METHODS.get(payment_id, {})
    return pay.get("ar", "") if lang == "ar" else pay.get("en", "")


def parse_clock(date_str: str, clock_str: str) -> datetime:
    clock_str = clock_str.strip().upper()
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
        try:
            t = datetime.strptime(clock_str, fmt).time()
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            return datetime.combine(d, t)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {clock_str}")


def get_available_dates(lang: str):
    dates = []
    today = datetime.now()
    for i in range(BOOKING_DAYS_AHEAD):
        d = today + timedelta(days=i)
        dates.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "display": f"{get_day_name(d.weekday(), lang)} | {d.strftime('%d-%m-%Y')}",
            }
        )
    return dates


def get_available_slots(date_str: str):
    slots = []
    start = parse_clock(date_str, WORKING_HOURS["open"])
    end = parse_clock(date_str, WORKING_HOURS["close"])
    if end <= start:
        end += timedelta(days=1)

    now = datetime.now()
    min_allowed = now + timedelta(minutes=10)
    current = start

    while current < end:
        if current.date() == now.date() and current < min_allowed:
            current += timedelta(minutes=30)
            continue

        time_str = current.strftime("%I:%M %p")
        if count_bookings(date_str, time_str) < MAX_CARS_PER_SLOT:
            slots.append(time_str)

        current += timedelta(minutes=30)

    return slots


def main_menu_keyboard(lang: str):
    return AR_MAIN_MENU if lang == "ar" else EN_MAIN_MENU


def ask_name_text(lang: str) -> str:
    return "📝 أدخل اسم العميل:" if lang == "ar" else "📝 Enter customer name:"


def ask_phone_text(lang: str) -> str:
    return "📱 أدخل رقم الجوال:" if lang == "ar" else "📱 Enter phone number:"


def ask_service_text(lang: str) -> str:
    return "🧼 اختر الخدمة:" if lang == "ar" else "🧼 Choose service:"


def ask_car_text(lang: str) -> str:
    return "🚗 اختر نوع السيارة:" if lang == "ar" else "🚗 Choose car size:"


def ask_extras_text(lang: str) -> str:
    return "➕ اختر الخدمات الإضافية:" if lang == "ar" else "➕ Choose extra services:"


def ask_date_text(lang: str) -> str:
    return "📅 اختر التاريخ:" if lang == "ar" else "📅 Choose date:"


def ask_time_text(lang: str) -> str:
    return "⏰ اختر الموعد:" if lang == "ar" else "⏰ Choose time:"


def ask_payment_text(lang: str) -> str:
    return "💳 اختر طريقة الدفع:" if lang == "ar" else "💳 Choose payment method:"


def format_services_list(lang: str) -> str:
    lines = []
    for key, s in services.items():
        name = s["name_ar"] if lang == "ar" else s["name_en"]
        p1 = get_service_price(s, "1")
        p2 = get_service_price(s, "2")
        p3 = get_service_price(s, "3")
        currency = "ريال" if lang == "ar" else "SAR"
        lines.append(f"{key}- {name}")
        lines.append(f"   صغيرة: {p1} {currency}")
        lines.append(f"   وسط: {p2} {currency}")
        lines.append(f"   كبيرة: {p3} {currency}")
        lines.append("")
    return "\n".join(lines).strip()


def format_car_list(lang: str) -> str:
    return "\n".join([f"{key}- {size['ar'] if lang == 'ar' else size['en']}" for key, size in CAR_SIZES.items()])


def format_extras_list(lang: str) -> str:
    lines = []
    for key, ex in extras.items():
        name = ex["name_ar"] if lang == "ar" else ex["name_en"]
        currency = "ريال" if lang == "ar" else "SAR"
        lines.append(f"{key}- {name} ({ex['price']} {currency})")
    return "\n".join(lines)


def format_dates_list(lang: str, dates) -> str:
    return "\n".join([f"{i}- {d['display']}" for i, d in enumerate(dates, 1)])


def format_slots_list(lang: str, slots) -> str:
    return "\n".join([f"{i}- {slot}" for i, slot in enumerate(slots, 1)])


def format_payment_list(lang: str) -> str:
    return "1- الدفع عند الوصول\n2- التحويل البنكي" if lang == "ar" else "1- Pay on arrival\n2- Bank transfer"


def format_summary(lang: str, data: dict) -> str:
    extras_ids = data.get("extras", [])
    extras_text = ", ".join([get_extra_name(e, lang) for e in extras_ids]) if extras_ids else ("لا يوجد" if lang == "ar" else "None")

    if lang == "ar":
        return f"""
📋 ملخص الحجز
━━━━━━━━━━━━━━━━━━━━━━

رقم الطلب: {data['booking_number']}
العميل: {data['customer_name']}
الجوال: {data['customer_phone']}
الخدمة: {data['service_name']}
نوع السيارة: {data['car_size_name']}
الإضافات: {extras_text}
التاريخ: {data['date_display']}
الوقت: {data['time']}
طريقة الدفع: {data['payment_name']}
الإجمالي: {data['total']} ريال

━━━━━━━━━━━━━━━━━━━━━━
✅ أرسل 1 للتأكيد
❌ أرسل 2 للإلغاء
↩️ أرسل 9 للرجوع خطوة
🏠 أرسل 0 للقائمة الرئيسية
"""
    return f"""
📋 Booking Summary
━━━━━━━━━━━━━━━━━━━━━━

Order Number: {data['booking_number']}
Customer: {data['customer_name']}
Phone: {data['customer_phone']}
Service: {data['service_name']}
Car Size: {data['car_size_name']}
Extras: {extras_text}
Date: {data['date_display']}
Time: {data['time']}
Payment: {data['payment_name']}
Total: {data['total']} SAR

━━━━━━━━━━━━━━━━━━━━━━
✅ Send 1 to confirm
❌ Send 2 to cancel
↩️ Send 9 to go back one step
🏠 Send 0 to main menu
"""


def format_invoice(lang: str, booking: dict) -> str:
    extras_ids = booking.get("extras", "").split(",") if booking.get("extras") else []
    extras_text = ", ".join([get_extra_name(e, lang) for e in extras_ids if e]) if extras_ids else ("لا يوجد" if lang == "ar" else "None")

    if lang == "ar":
        return f"""
✅ تم تأكيد الحجز
━━━━━━━━━━━━━━━━━━━━━━

رقم الطلب: {booking['booking_number']}
العميل: {booking['customer_name']}
الجوال: {booking['customer_phone']}
الخدمة: {booking['service_name']}
نوع السيارة: {booking['car_size_name']}
الإضافات: {extras_text}
التاريخ: {booking['date_display']}
الوقت: {booking['time']}
طريقة الدفع: {booking['payment_name']}
المبلغ الإجمالي: {booking['total']} ريال

📍 الموقع: {LOCATION}
📞 التواصل: {CONTACT['phone']}

⚠️ شروط الحجز:
• الوصول قبل الموعد بـ 10 دقائق
• التأخير أكثر من 30 دقيقة:
  - بدون دفع ← الحجز ملغي
  - مع دفع ← إعادة جدولة حسب الزحام
• الحد الأقصى 3 سيارات لكل موعد

0 - القائمة الرئيسية
"""
    return f"""
✅ Booking Confirmed
━━━━━━━━━━━━━━━━━━━━━━

Order Number: {booking['booking_number']}
Customer: {booking['customer_name']}
Phone: {booking['customer_phone']}
Service: {booking['service_name']}
Car Size: {booking['car_size_name']}
Extras: {extras_text}
Date: {booking['date_display']}
Time: {booking['time']}
Payment: {booking['payment_name']}
Total: {booking['total']} SAR

📍 Location: {LOCATION}
📞 Contact: {CONTACT['phone']}

⚠️ Booking Terms:
• Arrive 10 minutes early
• Late more than 30 minutes:
  - No payment → Booking cancelled
  - With payment → Reschedule based on availability
• Maximum 3 cars per slot

0 - Main menu
"""


def reset_to_main(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["booking_step"] = None
    context.user_data["booking_data"] = {}
    context.user_data["search_step"] = None


def get_previous_step(step: str):
    try:
        idx = BOOKING_ORDER.index(step)
    except ValueError:
        return None
    if idx == 0:
        return None
    return BOOKING_ORDER[idx - 1]


async def show_language_menu(update: Update):
    await update.message.reply_text(
        "🚗 Nova Car Wash Smart Booking System\n\nاختر اللغة | Choose Language",
        reply_markup=LANG_MENU,
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    if lang == "ar":
        text = (
            "🏠 القائمة الرئيسية\n\n"
            "1- الخدمات والأسعار\n"
            "2- حجز موعد\n"
            "3- الاستعلام عن حجز\n"
            "4- الموقع\n"
            "5- ساعات العمل\n"
            "6- التواصل\n"
            "7- تغيير اللغة\n"
            "0- القائمة الرئيسية\n"
        )
    else:
        text = (
            "🏠 Main Menu\n\n"
            "1- Services & Prices\n"
            "2- Book Appointment\n"
            "3- Check Booking\n"
            "4- Location\n"
            "5- Working Hours\n"
            "6- Contact\n"
            "7- Change language\n"
            "0- Main menu\n"
        )

    await update.message.reply_text(text, reply_markup=main_menu_keyboard(lang))


async def send_location(update: Update, lang: str):
    if lang == "ar":
        text = f"📍 الموقع\n{LOCATION}\n\n0 - القائمة الرئيسية"
    else:
        text = f"📍 Location\n{LOCATION}\n\n0 - Main menu"
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(lang))


async def send_hours(update: Update, lang: str):
    if lang == "ar":
        text = f"⏰ ساعات العمل\n{WORKING_HOURS['open']} - {WORKING_HOURS['close']}\n\n0 - القائمة الرئيسية"
    else:
        text = f"⏰ Working Hours\n{WORKING_HOURS['open']} - {WORKING_HOURS['close']}\n\n0 - Main menu"
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(lang))


async def send_contact(update: Update, lang: str):
    if lang == "ar":
        text = f"📞 التواصل\nPhone: {CONTACT['phone']}\nWhatsApp: {CONTACT['whatsapp']}\n\n0 - القائمة الرئيسية"
    else:
        text = f"📞 Contact\nPhone: {CONTACT['phone']}\nWhatsApp: {CONTACT['whatsapp']}\n\n0 - Main menu"
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(lang))


async def send_services(update: Update, lang: str):
    lines = []
    lines.append("🧼 الخدمات والأسعار" if lang == "ar" else "🧼 Services & Prices")
    lines.append("")
    lines.append(format_services_list(lang))
    lines.append("")
    lines.append("0 - القائمة الرئيسية" if lang == "ar" else "0 - Main menu")
    await update.message.reply_text("\n".join(lines), reply_markup=main_menu_keyboard(lang))


async def send_booking_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, step: str):
    lang = get_lang(context)
    data = context.user_data.get("booking_data", {})

    if step == "name":
        text = ask_name_text(lang) + "\n0 - " + ("القائمة الرئيسية" if lang == "ar" else "Main menu") + "\n9 - " + ("رجوع" if lang == "ar" else "Back")
        await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True))

    elif step == "phone":
        text = ask_phone_text(lang) + "\n0 - " + ("القائمة الرئيسية" if lang == "ar" else "Main menu") + "\n9 - " + ("رجوع" if lang == "ar" else "Back")
        await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True))

    elif step == "service":
        text = ask_service_text(lang) + "\n\n" + format_services_list(lang) + "\n\n0 - القائمة الرئيسية\n9 - رجوع"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["0", "9"]], resize_keyboard=True),
        )

    elif step == "car":
        text = ask_car_text(lang) + "\n\n" + format_car_list(lang) + "\n\n0 - القائمة الرئيسية\n9 - رجوع"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["0", "9"]], resize_keyboard=True),
        )

    elif step == "extras":
        text = ask_extras_text(lang) + "\n\n" + format_extras_list(lang)
        if lang == "ar":
            text += "\n\nأرسل الأرقام مفصولة بفاصلة، أو 8 للتخطي"
            text += "\n0 - القائمة الرئيسية\n9 - رجوع"
        else:
            text += "\n\nSend numbers separated by comma, or 8 to skip"
            text += "\n0 - Main menu\n9 - Back"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup([["1", "2", "3"], ["4", "5", "6"], ["8", "9", "0"]], resize_keyboard=True),
        )

    elif step == "date":
        dates = data.get("available_dates") or get_available_dates(lang)
        data["available_dates"] = dates
        text = ask_date_text(lang) + "\n\n" + format_dates_list(lang, dates)
        text += "\n\n0 - القائمة الرئيسية\n9 - رجوع" if lang == "ar" else "\n\n0 - Main menu\n9 - Back"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["0", "9"]], resize_keyboard=True),
        )

    elif step == "time":
        slots = data.get("available_slots", [])
        text = ask_time_text(lang) + "\n\n" + format_slots_list(lang, slots)
        text += "\n\n0 - القائمة الرئيسية\n9 - رجوع" if lang == "ar" else "\n\n0 - Main menu\n9 - Back"
        await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True))

    elif step == "payment":
        text = ask_payment_text(lang) + "\n\n" + format_payment_list(lang)
        text += "\n\n0 - القائمة الرئيسية\n9 - رجوع" if lang == "ar" else "\n\n0 - Main menu\n9 - Back"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["0", "9"]], resize_keyboard=True),
        )

    elif step == "confirm":
        await update.message.reply_text(
            format_summary(lang, data),
            reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["0", "9"]], resize_keyboard=True),
        )


async def notify_owner(context: ContextTypes.DEFAULT_TYPE, booking: dict, lang: str):
    extras_ids = booking.get("extras", "").split(",") if booking.get("extras") else []
    extras_text = ", ".join([get_extra_name(e, lang) for e in extras_ids if e]) if extras_ids else ("لا يوجد" if lang == "ar" else "None")

    owner_msg = (
        f"🚗 حجز جديد\n\n"
        f"رقم الحجز: {booking['booking_number']}\n"
        f"الاسم: {booking['customer_name']}\n"
        f"الجوال: {booking['customer_phone']}\n"
        f"الخدمة: {booking['service_name']}\n"
        f"نوع السيارة: {booking['car_size_name']}\n"
        f"الإضافات: {extras_text}\n"
        f"التاريخ: {booking['date_display']}\n"
        f"الوقت: {booking['time']}\n"
        f"الإجمالي: {booking['total']} ريال\n"
    )

    try:
        print("TRYING TO SEND")

        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_msg
        )

        print("MESSAGE SENT")

    except Exception as exc:
        print(f"Owner notification failed: {exc}")


async def booking_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    step = context.user_data.get("booking_step")
    data = context.user_data.get("booking_data", {})
    prev = get_previous_step(step)

    if prev is None:
        reset_to_main(context)
        await show_main_menu(update, context, lang)
        return

    clear_booking_keys(data, step)
    context.user_data["booking_step"] = prev
    await send_booking_prompt(update, context, prev)


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_to_main(context)
    context.user_data["booking_step"] = "name"
    context.user_data["booking_data"] = {}
    await send_booking_prompt(update, context, "name")


async def process_booking_step(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    lang = get_lang(context)
    step = context.user_data.get("booking_step")
    data = context.user_data.get("booking_data", {})

    if text == "0":
        reset_to_main(context)
        await show_main_menu(update, context, lang)
        return

    if text == "9":
        await booking_back(update, context)
        return

    if step == "name":
        if len(text) < 2:
            await update.message.reply_text(
                "⚠️ اسم غير صحيح" if lang == "ar" else "⚠️ Invalid name",
                reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
            )
            return

        data["customer_name"] = text
        context.user_data["booking_step"] = "phone"
        await send_booking_prompt(update, context, "phone")
        return

    if step == "phone":
        phone = normalize_phone(text)
        if not phone.isdigit() or len(phone) < 9:
            await update.message.reply_text(
                "⚠️ رقم جوال غير صحيح" if lang == "ar" else "⚠️ Invalid phone number",
                reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
            )
            return

        data["customer_phone"] = phone
        context.user_data["booking_step"] = "service"
        await send_booking_prompt(update, context, "service")
        return

    if step == "service":
        choice = extract_choice(text)
        if choice not in services:
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["0", "9"]], resize_keyboard=True),
            )
            return

        data["service_id"] = choice
        data["service_name"] = get_service_name(choice, lang)
        context.user_data["booking_step"] = "car"
        await send_booking_prompt(update, context, "car")
        return

    if step == "car":
        choice = extract_choice(text)
        if choice not in CAR_SIZES:
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["0", "9"]], resize_keyboard=True),
            )
            return

        data["car_size_id"] = choice
        data["car_size_ar"] = CAR_SIZES[choice]["ar"]
        data["car_size_name"] = get_car_name(choice, lang)
        context.user_data["booking_step"] = "extras"
        await send_booking_prompt(update, context, "extras")
        return

    if step == "extras":
        normalized = normalize_text(text)
        selected = []

        if normalized != "8":
            parts = [part.strip() for part in normalized.split(",")]
            for part in parts:
                if part in extras:
                    selected.append(part)

        data["extras"] = selected
        context.user_data["booking_step"] = "date"
        await send_booking_prompt(update, context, "date")
        return

    if step == "date":
        dates = data.get("available_dates") or get_available_dates(lang)
        choice = extract_choice(text)
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(dates):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["0", "9"]], resize_keyboard=True),
            )
            return

        selected_date = dates[idx]["date"]
        selected_display = dates[idx]["display"]
        slots = get_available_slots(selected_date)

        if not slots:
            await update.message.reply_text(
                "⚠️ لا توجد مواعيد متاحة" if lang == "ar" else "⚠️ No available slots",
                reply_markup=ReplyKeyboardRemove(),
            )
            context.user_data["booking_step"] = "date"
            await send_booking_prompt(update, context, "date")
            return

        data["date"] = selected_date
        data["date_display"] = selected_display
        data["available_slots"] = slots
        context.user_data["booking_step"] = "time"
        await send_booking_prompt(update, context, "time")
        return

    if step == "time":
        slots = data.get("available_slots", [])
        choice = extract_choice(text)
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(slots):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
            )
            return

        data["time"] = slots[idx]
        context.user_data["booking_step"] = "payment"
        await send_booking_prompt(update, context, "payment")
        return

    if step == "payment":
        choice = extract_choice(text)
        if choice not in PAYMENT_METHODS:
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["0", "9"]], resize_keyboard=True),
            )
            return

        data["payment_id"] = choice
        data["payment_name"] = get_payment_name(choice, lang)

        service = services[data["service_id"]]
        base_price = get_service_price(service, data["car_size_id"])
        extra_total = sum(extras[e]["price"] for e in data.get("extras", []))
        data["total"] = base_price + extra_total
        data["booking_number"] = next_booking_number()

        context.user_data["booking_step"] = "confirm"
        await send_booking_prompt(update, context, "confirm")
        return

    if step == "confirm":
        choice = extract_choice(text)

        if choice == "2":
            await update.message.reply_text(
                "❌ تم إلغاء الحجز" if lang == "ar" else "❌ Booking cancelled",
                reply_markup=main_menu_keyboard(lang),
            )
            reset_to_main(context)
            return

        if choice != "1":
            await update.message.reply_text(
                "⚠️ خيار غير صحيح" if lang == "ar" else "⚠️ Invalid option",
                reply_markup=ReplyKeyboardMarkup([["1"], ["2"], ["0", "9"]], resize_keyboard=True),
            )
            return

        booking = {
            "booking_number": data["booking_number"],
            "customer_name": data["customer_name"],
            "customer_phone": data["customer_phone"],
            "service_id": data["service_id"],
            "service_name": data["service_name"],
            "car_size_id": data["car_size_id"],
            "car_size_ar": data["car_size_ar"],
            "car_size_name": data["car_size_name"],
            "extras": ",".join(data.get("extras", [])),
            "date": data["date"],
            "date_display": data["date_display"],
            "time": data["time"],
            "payment_id": data["payment_id"],
            "payment_name": data["payment_name"],
            "total": data["total"],
            "status": "confirmed",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        add_booking(booking)
        await notify_owner(context, booking, lang)

        await update.message.reply_text(
            format_invoice(lang, booking),
            reply_markup=main_menu_keyboard(lang),
        )
        reset_to_main(context)
        return


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data["search_step"] = "phone"
    if lang == "ar":
        await update.message.reply_text(
            "🔍 الاستعلام عن حجز\n\nأدخل رقم الجوال:\n0 - القائمة الرئيسية\n9 - رجوع",
            reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
        )
    else:
        await update.message.reply_text(
            "🔍 Check booking\n\nEnter phone number:\n0 - Main menu\n9 - Back",
            reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
        )


async def process_search_step(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    lang = get_lang(context)

    if text in ("0", "9"):
        context.user_data["search_step"] = None
        await show_main_menu(update, context, lang)
        return

    phone = normalize_phone(text)
    if not phone.isdigit() or len(phone) < 9:
        await update.message.reply_text(
            "⚠️ رقم جوال غير صحيح" if lang == "ar" else "⚠️ Invalid phone number",
            reply_markup=ReplyKeyboardMarkup([["0", "9"]], resize_keyboard=True),
        )
        return

    booking = get_booking_by_phone(phone)
    if not booking:
        await update.message.reply_text(
            "⚠️ الحجز غير موجود" if lang == "ar" else "⚠️ Booking not found",
            reply_markup=main_menu_keyboard(lang),
        )
        context.user_data["search_step"] = None
        return

    await update.message.reply_text(
        format_invoice(lang, booking),
        reply_markup=main_menu_keyboard(lang),
    )
    context.user_data["search_step"] = None


async def handle_main_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, lang: str):
    if text == "0":
        await show_main_menu(update, context, lang)
        return

    if text == "1":
        await send_services(update, lang)
        return

    if text == "2":
        await start_booking(update, context)
        return

    if text == "3":
        await handle_search(update, context)
        return

    if text == "4":
        await send_location(update, lang)
        return

    if text == "5":
        await send_hours(update, lang)
        return

    if text == "6":
        await send_contact(update, lang)
        return

    if text == "7":
        context.user_data.clear()
        context.user_data["lang_selected"] = False
        await show_language_menu(update)
        return

    await update.message.reply_text(
        "اختر من القائمة." if lang == "ar" else "Choose from the menu.",
        reply_markup=main_menu_keyboard(lang),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["lang_selected"] = False
    await show_language_menu(update)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("lang_selected", False):
        await show_language_menu(update)
        return

    lang = get_lang(context)
    if lang == "ar":
        text = (
            "استخدم القائمة لاختيار الخدمة.\n"
            "0 = القائمة الرئيسية\n"
            "9 = رجوع خطوة\n"
            "في الاستعلام أدخل رقم الجوال."
        )
    else:
        text = (
            "Use the menu to choose a service.\n"
            "0 = main menu\n"
            "9 = back one step\n"
            "For search, enter the phone number."
        )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(lang))


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("lang_selected", False):
        await show_language_menu(update)
        return

    lang = get_lang(context)
    reset_to_main(context)
    await show_main_menu(update, context, lang)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("lang_selected", False):
        await show_language_menu(update)
        return

    lang = get_lang(context)
    reset_to_main(context)
    await update.message.reply_text(
        "تم الإلغاء" if lang == "ar" else "Cancelled",
        reply_markup=main_menu_keyboard(lang),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    raw_text = update.message.text.strip()
    text = normalize_text(raw_text)
    choice = extract_choice(text)

    if text in ("العربية", "English"):
        context.user_data.clear()
        set_lang(context, "ar" if text == "العربية" else "en")
        await show_main_menu(update, context, get_lang(context))
        return

    if not context.user_data.get("lang_selected", False):
        await show_language_menu(update)
        return

    lang = get_lang(context)

    if context.user_data.get("search_step") == "phone":
        await process_search_step(update, context, text)
        return

    if context.user_data.get("booking_step"):
        await process_booking_step(update, context, text)
        return

    await handle_main_menu_choice(update, context, choice, lang)


def main():
    create_tables()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
