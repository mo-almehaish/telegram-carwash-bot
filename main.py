import sqlite3
from datetime import datetime, timedelta

from services import services, extras, WORKING_HOURS, CONTACT, LOCATION

DB_NAME = "nova.db"

DAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CAR_SIZES = {
    "1": {"ar": "صغيرة", "en": "Small"},
    "2": {"ar": "وسط", "en": "Medium"},
    "3": {"ar": "كبيرة", "en": "Large"},
}

PAYMENT_METHODS = {
    "1": {"ar": "الدفع عند الوصول", "en": "Pay on Arrival"},
    "2": {"ar": "التحويل البنكي", "en": "Bank Transfer"},
}

BOOKING_STAGES = ["name", "phone", "service", "car", "extras", "date", "time", "payment", "confirm"]

BOOKING_CLEAR_KEYS = {
    "name": ["customer_name", "customer_phone", "service_id", "service_name", "car_size_id", "car_size_ar", "car_size_name",
             "extras", "available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
             "total", "booking_number"],
    "phone": ["customer_phone", "service_id", "service_name", "car_size_id", "car_size_ar", "car_size_name",
              "extras", "available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
              "total", "booking_number"],
    "service": ["service_id", "service_name", "car_size_id", "car_size_ar", "car_size_name",
                "extras", "available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
                "total", "booking_number"],
    "car": ["car_size_id", "car_size_ar", "car_size_name",
            "extras", "available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
            "total", "booking_number"],
    "extras": ["extras", "available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
               "total", "booking_number"],
    "date": ["available_dates", "date", "date_display", "available_slots", "time", "payment_id", "payment_name",
             "total", "booking_number"],
    "time": ["available_slots", "time", "payment_id", "payment_name", "total", "booking_number"],
    "payment": ["payment_id", "payment_name", "total", "booking_number"],
    "confirm": [],
}

def clear():
    print("\n" * 2)

def pause_return(lang):
    input("\n0 - رجوع للقائمة الرئيسية" if lang == "1" else "\n0 - Back to main menu")

def normalize_phone(phone):
    return phone.replace(" ", "").replace("-", "").strip()

def create_tables():
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

def next_booking_number():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM bookings")
    next_id = cur.fetchone()[0]
    conn.close()
    return f"NOVA-{1000 + next_id}"

def add_booking(data):
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

def get_booking_by_phone(phone):
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

def count_bookings(date, time):
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

def get_day_name(weekday, lang):
    return DAYS_AR[weekday] if lang == "1" else DAYS_EN[weekday]

def get_available_dates(lang):
    dates = []
    today = datetime.now()
    for i in range(7):
        d = today + timedelta(days=i)
        dates.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "display": f"{get_day_name(d.weekday(), lang)} | {d.strftime('%d-%m-%Y')}",
            }
        )
    return dates

def get_available_slots(date_str):
    slots = []
    start = datetime.strptime(f"{date_str} 09:00", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date_str} 03:00", "%Y-%m-%d %H:%M") + timedelta(days=1)
    now = datetime.now()
    current = start

    while current < end:
        if current.date() == now.date() and current <= now:
            current += timedelta(minutes=30)
            continue

        time_str = current.strftime("%I:%M %p")
        if count_bookings(date_str, time_str) < 3:
            slots.append(time_str)

        current += timedelta(minutes=30)

    return slots

def get_service_price(service, size_id):
    if "prices" in service and isinstance(service["prices"], dict):
        size_ar = CAR_SIZES[size_id]["ar"]
        return service["prices"].get(size_ar, 0)

    if size_id == "1":
        return service.get("small", 0)
    elif size_id == "2":
        return service.get("medium", 0)
    else:
        return service.get("large", 0)

def get_service_name(service_id, lang):
    service = services.get(service_id)
    if not service:
        return ""
    return service["name_ar"] if lang == "1" else service["name_en"]

def get_extra_name(extra_id, lang):
    extra = extras.get(extra_id)
    if not extra:
        return ""
    return extra["name_ar"] if lang == "1" else extra["name_en"]

def get_car_size_name(size_id, lang):
    size = CAR_SIZES.get(size_id, {})
    return size.get("ar", "") if lang == "1" else size.get("en", "")

def get_payment_name(payment_id, lang):
    payment = PAYMENT_METHODS.get(payment_id, {})
    return payment.get("ar", "") if lang == "1" else payment.get("en", "")

def show_language_menu():
    return """🚗 Nova Car Wash Smart Booking System

اختر اللغة | Choose Language

1 - العربية
2 - English"""

def show_main_menu(lang):
    if lang == "1":
        lines = [
            "🏠 القائمة الرئيسية",
            "",
            "1- الخدمات والأسعار",
            "2- حجز موعد",
            "3- الاستعلام عن حجز",
            "4- الموقع",
            "5- ساعات العمل",
            "6- التواصل",
            "7- خروج",
            "",
            "اختر رقم الخدمة:",
        ]
    else:
        lines = [
            "🏠 Main Menu",
            "",
            "1- Services & Prices",
            "2- Book Appointment",
            "3- Check Booking",
            "4- Location",
            "5- Working Hours",
            "6- Contact",
            "7- Exit",
            "",
            "Choose option:",
        ]
    return "\n".join(lines)

def show_services_text(lang):
    if lang == "1":
        out = ["🧼 الخدمات والأسعار", ""]
    else:
        out = ["🧼 Services & Prices", ""]

    for s in services.values():
        out.append("=" * 35)
        out.append(s["name_ar"] if lang == "1" else s["name_en"])
        for size_key in ("1", "2", "3"):
            size_ar = CAR_SIZES[size_key]["ar"]
            size_en = CAR_SIZES[size_key]["en"]
            price = get_service_price(s, size_key)
            if lang == "1":
                out.append(f"• {size_ar}: {price} ريال")
            else:
                out.append(f"• {size_en}: {price} SAR")

    out.append("")
    out.append("📌 الخدمات الإضافية" if lang == "1" else "📌 Extra Services")
    for e in extras.values():
        if lang == "1":
            out.append(f"• {e['name_ar']}: {e['price']} ريال")
        else:
            out.append(f"• {e['name_en']}: {e['price']} SAR")

    return "\n".join(out)

def show_location_text(lang):
    return f"{'📍 الموقع' if lang == '1' else '📍 Location'}\n{LOCATION}"

def show_hours_text(lang):
    if lang == "1":
        return f"⏰ ساعات العمل\n{WORKING_HOURS['open']} - {WORKING_HOURS['close']}"
    return f"⏰ Working Hours\n{WORKING_HOURS['open']} - {WORKING_HOURS['close']}"

def show_contact_text(lang):
    if lang == "1":
        return f"📞 التواصل\nPhone: {CONTACT['phone']}\nWhatsApp: {CONTACT['whatsapp']}"
    return f"📞 Contact\nPhone: {CONTACT['phone']}\nWhatsApp: {CONTACT['whatsapp']}"

def format_summary(lang, data):
    extras_ids = data.get("extras", [])
    extras_text = ", ".join([get_extra_name(e, lang) for e in extras_ids]) if extras_ids else ("لا يوجد" if lang == "1" else "None")

    if lang == "1":
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

def format_invoice(lang, booking):
    extras_ids = booking.get("extras", "").split(",") if booking.get("extras") else []
    extras_text = ", ".join([get_extra_name(e, lang) for e in extras_ids if e]) if extras_ids else ("لا يوجد" if lang == "1" else "None")

    if lang == "1":
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
"""

def clear_from_step(data, stage):
    if stage not in BOOKING_CLEAR_KEYS:
        return
    for key in BOOKING_CLEAR_KEYS[stage]:
        data.pop(key, None)

def back_stage(history, current_stage, data):
    if not history:
        return None
    clear_from_step(data, current_stage)
    return history.pop()

def input_with_back(prompt, lang, allow_skip=False):
    while True:
        value = input(prompt).strip()
        if value == "0":
            return "MAIN_MENU"
        if value == "9":
            return "BACK"
        if allow_skip and value == "8":
            return "SKIP"
        if value:
            return value

def wait_return(lang):
    input("\n0 - رجوع للقائمة الرئيسية")

def show_services_screen(lang):
    clear()
    print(show_services_text(lang))
    wait_return(lang)

def show_location_screen(lang):
    clear()
    print(show_location_text(lang))
    wait_return(lang)

def show_hours_screen(lang):
    clear()
    print(show_hours_text(lang))
    wait_return(lang)

def show_contact_screen(lang):
    clear()
    print(show_contact_text(lang))
    wait_return(lang)

def search_flow(lang):
    clear()
    if lang == "1":
        phone = input("أدخل رقم الجوال: ").strip()
    else:
        phone = input("Enter phone number: ").strip()

    phone = normalize_phone(phone)
    if phone in ("0", "9", ""):
        return

    booking = get_booking_by_phone(phone)

    if not booking:
        print("⚠️ الحجز غير موجود" if lang == "1" else "⚠️ Booking not found")
        wait_return(lang)
        return

    clear()
    print(format_invoice(lang, booking))
    wait_return(lang)

def booking_flow(lang):
    data = {}
    history = []
    stage = "name"

    while True:
        clear()

        if stage == "name":
            if lang == "1":
                print("📅 حجز موعد جديد")
                print("أدخل اسم العميل")
                print("0 - القائمة الرئيسية")
                print("9 - رجوع")
            else:
                print("📅 New Booking")
                print("Enter customer name")
                print("0 - Main menu")
                print("9 - Back")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                return
            if len(value) < 2:
                print("⚠️ اسم غير صحيح" if lang == "1" else "⚠️ Invalid name")
                input("\nEnter")
                continue

            data["customer_name"] = value
            history.append(stage)
            stage = "phone"
            continue

        if stage == "phone":
            if lang == "1":
                print("📱 أدخل رقم الجوال")
                print("0 - القائمة الرئيسية")
                print("9 - رجوع")
            else:
                print("📱 Enter phone number")
                print("0 - Main menu")
                print("9 - Back")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "name"
                continue

            value = normalize_phone(value)
            if not value.isdigit() or len(value) < 9:
                print("⚠️ رقم جوال غير صحيح" if lang == "1" else "⚠️ Invalid phone")
                input("\nEnter")
                continue

            data["customer_phone"] = value
            history.append(stage)
            stage = "service"
            continue

        if stage == "service":
            clear()
            if lang == "1":
                print("🧼 اختر الخدمة")
            else:
                print("🧼 Choose service")
            for key, s in services.items():
                print(f"{key}- {s['name_ar'] if lang == '1' else s['name_en']}")
            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "phone"
                continue
            if value not in services:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

            data["service_id"] = value
            data["service_name"] = get_service_name(value, lang)
            history.append(stage)
            stage = "car"
            continue

        if stage == "car":
            clear()
            if lang == "1":
                print("🚗 اختر نوع السيارة")
            else:
                print("🚗 Choose car size")
            for key, size in CAR_SIZES.items():
                print(f"{key}- {size['ar'] if lang == '1' else size['en']}")
            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "service"
                continue
            if value not in CAR_SIZES:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

            data["car_size_id"] = value
            data["car_size_ar"] = CAR_SIZES[value]["ar"]
            data["car_size_name"] = get_car_size_name(value, lang)
            history.append(stage)
            stage = "extras"
            continue

        if stage == "extras":
            clear()
            if lang == "1":
                print("✨ اختر الخدمات الإضافية")
                print("1,2,3 لاختيار إضافات")
                print("8 للتخطي")
            else:
                print("✨ Choose extra services")
                print("1,2,3 to select extras")
                print("8 to skip")

            for key, e in extras.items():
                print(f"{key}- {e['name_ar'] if lang == '1' else e['name_en']} ({e['price']} {'ريال' if lang == '1' else 'SAR'})")

            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "car"
                continue
            if value == "8" or value == "":
                data["extras"] = []
            else:
                selected_extras = []
                for part in value.replace(" ", "").split(","):
                    if part in extras:
                        selected_extras.append(part)
                data["extras"] = selected_extras

            history.append(stage)
            stage = "date"
            continue

        if stage == "date":
            clear()
            if lang == "1":
                print("📅 اختر التاريخ")
            else:
                print("📅 Choose date")

            dates = get_available_dates(lang)
            data["available_dates"] = dates

            for i, d in enumerate(dates, 1):
                print(f"{i}- {d['display']}")
            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "extras"
                continue

            try:
                idx = int(value) - 1
                if idx < 0 or idx >= len(dates):
                    raise ValueError
            except ValueError:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

            selected_date = dates[idx]["date"]
            selected_display = dates[idx]["display"]
            slots = get_available_slots(selected_date)

            if not slots:
                print("⚠️ لا توجد مواعيد متاحة" if lang == "1" else "⚠️ No available slots")
                input("\nEnter")
                continue

            data["date"] = selected_date
            data["date_display"] = selected_display
            data["available_slots"] = slots
            history.append(stage)
            stage = "time"
            continue

        if stage == "time":
            clear()
            if lang == "1":
                print("⏰ المواعيد المتاحة")
            else:
                print("⏰ Available slots")
            for i, slot in enumerate(data.get("available_slots", []), 1):
                print(f"{i}- {slot}")
            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "date"
                continue

            try:
                idx = int(value) - 1
                slots = data.get("available_slots", [])
                if idx < 0 or idx >= len(slots):
                    raise ValueError
            except ValueError:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

            data["time"] = data["available_slots"][idx]
            history.append(stage)
            stage = "payment"
            continue

        if stage == "payment":
            clear()
            if lang == "1":
                print("💳 اختر طريقة الدفع")
                print("1- الدفع عند الوصول")
                print("2- التحويل البنكي")
            else:
                print("💳 Choose payment method")
                print("1- Pay on arrival")
                print("2- Bank transfer")

            print("\n0 - القائمة الرئيسية")
            print("9 - رجوع")

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "time"
                continue

            if value not in PAYMENT_METHODS:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

            data["payment_id"] = value
            data["payment_name"] = get_payment_name(value, lang)

            base_price = get_service_price(services[data["service_id"]], data["car_size_id"])
            extra_total = 0
            for extra_id in data.get("extras", []):
                extra_total += extras[extra_id]["price"]
            data["total"] = base_price + extra_total

            data["booking_number"] = next_booking_number()
            history.append(stage)
            stage = "confirm"
            continue

        if stage == "confirm":
            clear()
            print(format_summary(lang, data))

            value = input("\n> ").strip()
            if value == "0":
                return
            if value == "9":
                stage = back_stage(history, stage, data) or "payment"
                continue
            if value == "2":
                if lang == "1":
                    print("❌ تم إلغاء الحجز")
                else:
                    print("❌ Booking cancelled")
                input("\nEnter")
                return
            if value != "1":
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")
                continue

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

            clear()
            print(format_invoice(lang, booking))
            input("\n0 - رجوع للقائمة الرئيسية")
            return

def main():
    create_tables()

    while True:
        clear()
        print(show_language_menu())
        lang = input("\nاختر اللغة / Choose Language: ").strip()

        if lang not in ("1", "2"):
            continue

        while True:
            clear()
            print(show_main_menu(lang))
            choice = input("\n> ").strip()

            if choice == "0":
                continue
            elif choice == "1":
                show_services_screen(lang)
            elif choice == "2":
                booking_flow(lang)
            elif choice == "3":
                search_flow(lang)
            elif choice == "4":
                show_location_screen(lang)
            elif choice == "5":
                show_hours_screen(lang)
            elif choice == "6":
                show_contact_screen(lang)
            elif choice == "7":
                if lang == "1":
                    print("\nشكراً لاستخدامك Nova Car Wash")
                else:
                    print("\nThank you for using Nova Car Wash")
                return
            else:
                print("⚠️ خيار غير صحيح" if lang == "1" else "⚠️ Invalid option")
                input("\nEnter")

if __name__ == "__main__":
    main()
