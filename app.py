import os
from datetime import date
from flask import Flask, request, jsonify, session, render_template, send_file
from models import (
    init_db, seed_doctors, authenticate, get_doctor_by_id,
    get_all_doctors, get_selections_for_month, add_selection,
    remove_selection, finalize_month, unfinalize_month, is_doctor_finalized,
)
from holidays import get_holidays_for_month
from export import generate_excel

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Initialize database on startup
with app.app_context():
    init_db()
    seed_doctors()


def get_next_month():
    """Return (year, month) for next month."""
    today = date.today()
    if today.month == 12:
        return today.year + 1, 1
    return today.year, today.month + 1


def login_required(f):
    """Decorator to require login."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "doctor_id" not in session:
            return jsonify({"error": "Giris yapmaniz gerekiyor."}), 401
        return f(*args, **kwargs)

    return decorated


# --- Pages ---

@app.route("/")
def index():
    year, month = get_next_month()
    return render_template("index.html", target_year=year, target_month=month)


# --- Auth API ---

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    doctor = authenticate(username, password)
    if not doctor:
        return jsonify({"error": "Gecersiz kullanici adi veya sifre."}), 401

    session["doctor_id"] = doctor["id"]
    return jsonify({
        "id": doctor["id"],
        "full_name": doctor["full_name"],
        "specialty": doctor["specialty"],
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Cikis yapildi."})


@app.route("/api/me")
def api_me():
    if "doctor_id" not in session:
        return jsonify({"logged_in": False}), 200

    doctor = get_doctor_by_id(session["doctor_id"])
    if not doctor:
        session.clear()
        return jsonify({"logged_in": False}), 200

    year, month = get_next_month()
    finalized = is_doctor_finalized(doctor["id"], year, month)

    return jsonify({
        "logged_in": True,
        "id": doctor["id"],
        "full_name": doctor["full_name"],
        "specialty": doctor["specialty"],
        "is_finalized": finalized,
    })


# --- Calendar API ---

@app.route("/api/calendar/<int:year>/<int:month>")
def api_calendar(year, month):
    days = get_holidays_for_month(year, month)
    turkish_months = [
        "", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
        "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"
    ]
    return jsonify({
        "year": year,
        "month": month,
        "month_name": turkish_months[month],
        "days": days,
    })


# --- Selections API ---

@app.route("/api/selections/<int:year>/<int:month>")
def api_selections(year, month):
    selections = get_selections_for_month(year, month)
    return jsonify(selections)


@app.route("/api/selections", methods=["POST"])
@login_required
def api_add_selection():
    data = request.get_json()
    date_str = data.get("date")
    duty_hours = data.get("duty_hours", 16)

    if not date_str:
        return jsonify({"error": "Tarih gerekli."}), 400

    success, message = add_selection(session["doctor_id"], date_str, duty_hours)
    if success:
        return jsonify({"message": message})
    return jsonify({"error": message}), 409


@app.route("/api/selections/<date_str>", methods=["DELETE"])
@login_required
def api_remove_selection(date_str):
    success, message = remove_selection(session["doctor_id"], date_str)
    if success:
        return jsonify({"message": message})
    return jsonify({"error": message}), 400


# --- Doctors API ---

@app.route("/api/doctors")
def api_doctors():
    doctors = get_all_doctors()
    return jsonify(doctors)


# --- Finalize API ---

@app.route("/api/finalize/<int:year>/<int:month>", methods=["POST"])
@login_required
def api_finalize(year, month):
    success, message = finalize_month(year, month, session["doctor_id"])
    if success:
        return jsonify({"message": message})
    return jsonify({"error": message}), 400


@app.route("/api/unfinalize/<int:year>/<int:month>", methods=["POST"])
@login_required
def api_unfinalize(year, month):
    success, message = unfinalize_month(year, month, session["doctor_id"])
    if success:
        return jsonify({"message": message})
    return jsonify({"error": message}), 400


# --- Export API ---

@app.route("/api/export/<int:year>/<int:month>")
def api_export(year, month):
    turkish_months = [
        "", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
        "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"
    ]
    output = generate_excel(year, month)
    filename = f"Nobet_{turkish_months[month]}_{year}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
