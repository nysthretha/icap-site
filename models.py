import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    """Get a database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def query(conn, sql, params=None):
    """Execute a query and return rows as list of dicts."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params or ())
    try:
        rows = cur.fetchall()
    except psycopg2.ProgrammingError:
        rows = []
    cur.close()
    return rows


def query_one(conn, sql, params=None):
    """Execute a query and return one row as dict or None."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params or ())
    try:
        row = cur.fetchone()
    except psycopg2.ProgrammingError:
        row = None
    cur.close()
    return dict(row) if row else None


def execute(conn, sql, params=None):
    """Execute a statement and return rowcount."""
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rowcount = cur.rowcount
    cur.close()
    return rowcount


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS selections (
            id SERIAL PRIMARY KEY,
            doctor_id INTEGER NOT NULL REFERENCES doctors(id),
            date TEXT NOT NULL,
            duty_hours INTEGER NOT NULL,
            is_finalized INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(doctor_id, date)
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule_status (
            month TEXT PRIMARY KEY,
            is_finalized INTEGER DEFAULT 0,
            finalized_at TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def seed_doctors():
    """Insert sample doctors if the table is empty."""
    conn = get_db()
    row = query_one(conn, "SELECT COUNT(*) as count FROM doctors")
    if row["count"] == 0:
        doctors = [
            ("kkurt", "nobet2026", "Kemal Kurt", "Dahiliye"),
            ("aaltintas", "icap2026", "Ayfer Altintas", "Dahiliye"),
            ("mgakkaya", "ortopedi26", "Mahmut Gokhan Akkaya", "Ortopedi"),
            ("kyagmuroglu", "kadir2026", "Kadir Yagmuroglu", "Ortopedi"),
            ("bgatacer", "gogus2026", "Basak Gonen Atacer", "Gogus"),
            ("moatacer", "uroloji26", "Mustafa Ozan Atacer", "Uroloji"),
            ("meyesilnacar", "anestezi26", "Merve Ezgi Yesilnacar", "Anestezi"),
            ("mosuner", "cerrahi26", "Mert Orhan Suner", "G.Cerrahi"),
            ("myorulmaz", "psikiyatri26", "Mehmet Yorulmaz", "Psikiyatri"),
            ("aatsiz", "acil2026", "Ahmet Atsiz", "Acil"),
        ]
        for username, password, full_name, specialty in doctors:
            execute(conn,
                "INSERT INTO doctors (username, password_hash, full_name, specialty) VALUES (%s, %s, %s, %s)",
                (username, generate_password_hash(password), full_name, specialty),
            )
        conn.commit()
    conn.close()


def authenticate(username, password):
    """Return doctor row if credentials are valid, else None."""
    conn = get_db()
    doctor = query_one(conn, "SELECT * FROM doctors WHERE username = %s", (username,))
    conn.close()
    if doctor and check_password_hash(doctor["password_hash"], password):
        return doctor
    return None


def get_doctor_by_id(doctor_id):
    conn = get_db()
    doctor = query_one(conn, "SELECT * FROM doctors WHERE id = %s", (doctor_id,))
    conn.close()
    return doctor


def get_all_doctors():
    conn = get_db()
    rows = query(conn, "SELECT id, username, full_name, specialty FROM doctors")
    conn.close()
    return rows


def get_selections_for_month(year, month):
    """Return all selections for a given month with doctor info."""
    month_prefix = f"{year}-{month:02d}%"
    conn = get_db()
    rows = query(conn, """
        SELECT s.id, s.date, s.duty_hours, s.is_finalized,
               d.id as doctor_id, d.full_name, d.specialty
        FROM selections s
        JOIN doctors d ON s.doctor_id = d.id
        WHERE s.date LIKE %s
        ORDER BY s.date
    """, (month_prefix,))
    conn.close()
    return rows


def add_selection(doctor_id, date_str, duty_hours):
    """Add a selection. Returns (success, message)."""
    conn = get_db()
    try:
        # Get doctor's specialty
        doctor = query_one(conn, "SELECT specialty FROM doctors WHERE id = %s", (doctor_id,))
        if not doctor:
            conn.close()
            return False, "Doktor bulunamadi."

        # Check if month is finalized
        month_str = date_str[:7]
        status = query_one(conn,
            "SELECT is_finalized FROM schedule_status WHERE month = %s", (month_str,))
        if status and status["is_finalized"]:
            conn.close()
            return False, "Bu ay icin nobet cizelgesi kesinlestirilmis."

        # Check specialty conflict
        conflict = query_one(conn, """
            SELECT d.full_name FROM selections s
            JOIN doctors d ON s.doctor_id = d.id
            WHERE s.date = %s AND d.specialty = %s AND s.doctor_id != %s
        """, (date_str, doctor["specialty"], doctor_id))

        if conflict:
            conn.close()
            return False, f"{conflict['full_name']} ({doctor['specialty']}) bu tarihte zaten nobetci."

        # Upsert: insert or update on conflict
        execute(conn, """
            INSERT INTO selections (doctor_id, date, duty_hours)
            VALUES (%s, %s, %s)
            ON CONFLICT (doctor_id, date) DO UPDATE SET duty_hours = EXCLUDED.duty_hours
        """, (doctor_id, date_str, duty_hours))
        conn.commit()
        conn.close()
        return True, "Nobet secimi kaydedildi."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)


def remove_selection(doctor_id, date_str):
    """Remove a doctor's selection for a date. Returns (success, message)."""
    conn = get_db()

    # Check if month is finalized
    month_str = date_str[:7]
    status = query_one(conn,
        "SELECT is_finalized FROM schedule_status WHERE month = %s", (month_str,))
    if status and status["is_finalized"]:
        conn.close()
        return False, "Bu ay icin nobet cizelgesi kesinlestirilmis."

    rowcount = execute(conn,
        "DELETE FROM selections WHERE doctor_id = %s AND date = %s",
        (doctor_id, date_str),
    )
    conn.commit()
    conn.close()
    if rowcount > 0:
        return True, "Nobet secimi kaldirildi."
    return False, "Secim bulunamadi."


def finalize_month(year, month, doctor_id):
    """Finalize a doctor's selections for a month."""
    month_str = f"{year}-{month:02d}%"
    conn = get_db()
    execute(conn, """
        UPDATE selections SET is_finalized = 1
        WHERE doctor_id = %s AND date LIKE %s
    """, (doctor_id, month_str))
    conn.commit()
    conn.close()
    return True, "Nobet cizelgeniz kesinlestirildi."


def is_doctor_finalized(doctor_id, year, month):
    """Check if a doctor has finalized their selections for a month."""
    month_str = f"{year}-{month:02d}%"
    conn = get_db()
    row = query_one(conn, """
        SELECT COUNT(*) as cnt FROM selections
        WHERE doctor_id = %s AND date LIKE %s AND is_finalized = 1
    """, (doctor_id, month_str))
    conn.close()
    return row["cnt"] > 0
