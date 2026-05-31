import sqlite3

DB_NAME = "nova.db"

def create_tables():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_name TEXT,
        phone TEXT,

        service TEXT,
        car_type TEXT,

        extras TEXT,

        booking_date TEXT,
        booking_time TEXT,

        payment_method TEXT,

        total_price REAL
    )
    """)

    conn.commit()
    conn.close()


def add_booking(data):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO bookings (

        customer_name,
        phone,
        service,
        car_type,
        extras,
        booking_date,
        booking_time,
        payment_method,
        total_price

    )

    VALUES (?,?,?,?,?,?,?,?,?)
    """, data)

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return booking_id


def get_booking(booking_id):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM bookings WHERE id=?",
        (booking_id,)
    )

    result = cursor.fetchone()

    conn.close()

    return result


def count_bookings(date, time):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM bookings
        WHERE booking_date=?
        AND booking_time=?
        """,
        (date, time)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count
