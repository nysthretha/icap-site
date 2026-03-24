import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "oncall.db")


def get_db():
    """Get a database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            duty_hours INTEGER NOT NULL,
            is_finalized INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            UNIQUE(doctor_id, date)
        );

        CREATE TABLE IF NOT EXISTS schedule_status (
            month TEXT PRIMARY KEY,
            is_finalized INTEGER DEFAULT 0,
            finalized_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def seed_doctors():
    """Insert sample doctors if the table is empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if count == 0:
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
            conn.execute(
                "INSERT INTO doctors (username, password_hash, full_name, specialty) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), full_name, specialty),
            )
        conn.commit()
    conn.close()


def authenticate(username, password):
    """Return doctor row if credentials are valid, else None."""
    conn = get_db()
    doctor = conn.execute(
        "SELECT * FROM doctors WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if doctor and check_password_hash(doctor["password_hash"], password):
        return dict(doctor)
    return None


def get_doctor_by_id(doctor_id):
    conn = get_db()
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    conn.close()
    return dict(doctor) if doctor else None


def get_all_doctors():
    conn = get_db()
    rows = conn.execute("SELECT id, username, full_name, specialty FROM doctors").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_selections_for_month(year, month):
    """Return all selections for a given month with doctor info."""
    month_prefix = f"{year}-{month:02d}"
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.date, s.duty_hours, s.is_finalized,
               d.id as doctor_id, d.full_name, d.specialty
        FROM selections s
        JOIN doctors d ON s.doctor_id = d.id
        WHERE s.date LIKE ?
        ORDER BY s.date
    """, (month_prefix + "%",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_selection(doctor_id, date_str, duty_hours):
    """Add a selection. Returns (success, message)."""
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")

        # Get doctor's specialty
        doctor = conn.execute(
            "SELECT specialty FROM doctors WHERE id = ?", (doctor_id,)
        ).fetchone()
        if not doctor:
            conn.rollback()
            conn.close()
            return False, "Doktor bulunamadi."

        # Check if month is finalized
        month_str = date_str[:7]
        status = conn.execute(
            "SELECT is_finalized FROM schedule_status WHERE month = ?", (month_str,)
        ).fetchone()
        if status and status["is_finalized"]:
            conn.rollback()
            conn.close()
            return False, "Bu ay icin nobet cizelgesi kesinlestirilmis."

        # Check specialty conflict
        conflict = conn.execute("""
            SELECT d.full_name FROM selections s
            JOIN doctors d ON s.doctor_id = d.id
            WHERE s.date = ? AND d.specialty = ? AND s.doctor_id != ?
        """, (date_str, doctor["specialty"], doctor_id)).fetchone()

        if conflict:
            conn.rollback()
            conn.close()
            return False, f"{conflict['full_name']} ({doctor['specialty']}) bu tarihte zaten nobetci."

        # Insert or replace (if same doctor re-selects same date)
        conn.execute(
            "INSERT OR REPLACE INTO selections (doctor_id, date, duty_hours) VALUES (?, ?, ?)",
            (doctor_id, date_str, duty_hours),
        )
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
    status = conn.execute(
        "SELECT is_finalized FROM schedule_status WHERE month = ?", (month_str,)
    ).fetchone()
    if status and status["is_finalized"]:
        conn.close()
        return False, "Bu ay icin nobet cizelgesi kesinlestirilmis."

    result = conn.execute(
        "DELETE FROM selections WHERE doctor_id = ? AND date = ?",
        (doctor_id, date_str),
    )
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    if deleted:
        return True, "Nobet secimi kaldirildi."
    return False, "Secim bulunamadi."


def finalize_month(year, month, doctor_id):
    """Finalize a doctor's selections for a month."""
    month_str = f"{year}-{month:02d}"
    conn = get_db()

    # Mark doctor's selections as finalized
    conn.execute("""
        UPDATE selections SET is_finalized = 1
        WHERE doctor_id = ? AND date LIKE ?
    """, (doctor_id, month_str + "%"))

    conn.commit()
    conn.close()
    return True, "Nobet cizelgeniz kesinlestirildi."


def is_doctor_finalized(doctor_id, year, month):
    """Check if a doctor has finalized their selections for a month."""
    month_str = f"{year}-{month:02d}"
    conn = get_db()
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM selections
        WHERE doctor_id = ? AND date LIKE ? AND is_finalized = 1
    """, (doctor_id, month_str + "%")).fetchone()
    conn.close()
    return row["cnt"] > 0
