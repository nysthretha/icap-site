import calendar
from datetime import date, timedelta
from hijridate import Hijri, Gregorian

# Fixed Turkish public holidays (month, day, name)
FIXED_HOLIDAYS = [
    (1, 1, "Yilbasi"),
    (4, 23, "Ulusal Egemenlik ve Cocuk Bayrami"),
    (5, 1, "Emek ve Dayanisma Gunu"),
    (5, 19, "Ataturk'u Anma, Genclik ve Spor Bayrami"),
    (7, 15, "Demokrasi ve Milli Birlik Gunu"),
    (8, 30, "Zafer Bayrami"),
    (10, 28, "Cumhuriyet Bayrami Arifesi"),
    (10, 29, "Cumhuriyet Bayrami"),
]


def get_islamic_holidays(year):
    """Compute Islamic holiday Gregorian dates for a given Gregorian year."""
    holidays = {}
    hijri_start = Gregorian(year, 1, 1).to_hijri()

    for hijri_year in [hijri_start.year, hijri_start.year + 1]:
        # Ramazan Bayrami Arife: last day of Ramadan (month 9)
        for day in [29, 30]:
            try:
                g = Hijri(hijri_year, 9, day).to_gregorian()
                if g.year == year:
                    holidays[g] = "Ramazan Bayrami Arifesi"
            except (ValueError, OverflowError):
                pass

        # Ramazan Bayrami: 1, 2, 3 Shawwal (month 10)
        for day in [1, 2, 3]:
            try:
                g = Hijri(hijri_year, 10, day).to_gregorian()
                if g.year == year:
                    holidays[g] = "Ramazan Bayrami"
            except (ValueError, OverflowError):
                pass

        # Kurban Bayrami Arife: 9 Dhu al-Hijjah (month 12)
        try:
            g = Hijri(hijri_year, 12, 9).to_gregorian()
            if g.year == year:
                holidays[g] = "Kurban Bayrami Arifesi"
        except (ValueError, OverflowError):
            pass

        # Kurban Bayrami: 10, 11, 12, 13 Dhu al-Hijjah (month 12)
        for day in [10, 11, 12, 13]:
            try:
                g = Hijri(hijri_year, 12, day).to_gregorian()
                if g.year == year:
                    holidays[g] = "Kurban Bayrami"
            except (ValueError, OverflowError):
                pass

    return holidays


def get_holidays_for_month(year, month):
    """Return a dict mapping each date in the month to its info.

    Each entry: {
        "date": "YYYY-MM-DD",
        "day": int,
        "day_name": str (Turkish),
        "type": "workday" | "weekend" | "holiday",
        "duty_hours": 16 | 24,
        "holiday_name": str | None
    }
    """
    turkish_days = [
        "Pazartesi", "Sali", "Carsamba", "Persembe",
        "Cuma", "Cumartesi", "Pazar"
    ]

    # Build fixed holiday lookup for this month
    fixed = {}
    for m, d, name in FIXED_HOLIDAYS:
        if m == month:
            fixed[date(year, m, d)] = name

    # Islamic holidays for this year
    islamic = get_islamic_holidays(year)

    num_days = calendar.monthrange(year, month)[1]
    days = []

    for day in range(1, num_days + 1):
        d = date(year, month, day)
        weekday = d.weekday()  # 0=Monday, 6=Sunday
        day_name = turkish_days[weekday]
        is_weekend = weekday >= 5  # Saturday=5, Sunday=6

        holiday_name = fixed.get(d) or islamic.get(d)
        is_holiday = holiday_name is not None

        if is_holiday:
            day_type = "holiday"
        elif is_weekend:
            day_type = "weekend"
        else:
            day_type = "workday"

        duty_hours = 24 if day_type in ("holiday", "weekend") else 16

        days.append({
            "date": d.isoformat(),
            "day": day,
            "day_name": day_name,
            "type": day_type,
            "duty_hours": duty_hours,
            "holiday_name": holiday_name,
        })

    return days
