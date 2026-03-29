# ICAP On-Call Schedule

Monthly on-call duty planning and tracking system for hospital doctors.

## Features

### Calendar View
- Automatically displays next month's calendar
- Workdays, weekends, and public holidays are color-coded
- Duty duration shown for each day: workdays **16 hours**, weekends and holidays **24 hours**

### Turkish Public Holidays
- Fixed public holidays are calculated automatically (Republic Day, April 23, May 19, May 1, July 15, August 30, New Year's Day)
- Religious holidays (Eid al-Fitr and Eid al-Adha) are computed automatically from the Hijri calendar
- Holiday eves are also treated as holidays

### Duty Selection
- Doctors log in and select their on-call days
- Two doctors of the same specialty cannot be on call on the same day (e.g. 2 Orthopaedic doctors must pick different days)
- Selections are displayed on the calendar in real time
- Other doctors' selections are also visible on the calendar

### Total Hours Tracking
- Each doctor's total duty hours are displayed below the calendar and update live
- Totals change instantly as selections are added or removed

### Preview and Finalization
- Doctors can preview their selections in table format (dates as rows, specialties as columns)
- Total hours per specialty are shown at the bottom of the preview table
- After finalization, doctors can unlock their selections via the "Unlock" button to make changes if needed

### Excel Export
- The on-call schedule can be downloaded as an Excel file
- Specialties as columns, dates as rows
- Workdays have a white background, holidays and weekends have a light grey background
- Total duty hours per specialty are included in the last row

## Setup

### Requirements
- Python 3.10+
- Flask, hijridate, openpyxl, gunicorn

### Running Locally
```bash
pip install -r requirements.txt
python3 app.py
```
Open `http://127.0.0.1:5000` in your browser.

### Deploying on Railway
The project is Railway-ready. Connect the GitHub repo to Railway, set the `SECRET_KEY` environment variable, and generate a domain.

## Doctor Management

The doctor list is defined in the `seed_doctors()` function in `models.py`. To add or remove doctors:

**To recreate the database from scratch:**
```bash
rm instance/oncall.db
python3 app.py
```

**To add a doctor while preserving existing data:**
```bash
python3 -c "
from models import get_db
from werkzeug.security import generate_password_hash
conn = get_db()
conn.execute('INSERT INTO doctors (username, password_hash, full_name, specialty) VALUES (?, ?, ?, ?)',
    ('newuser', generate_password_hash('password123'), 'New Doctor', 'Specialty'))
conn.commit()
conn.close()
"
```
