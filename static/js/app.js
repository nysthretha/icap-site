// State
let currentUser = null;
let calendarData = null;
let selectionsData = [];
let allDoctors = [];

// --- API helpers ---

async function api(url, options = {}) {
    const defaults = {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
    };
    const res = await fetch(url, { ...defaults, ...options });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Bir hata olustu.");
    }
    return data;
}

function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = "toast " + type;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
}

function setStatus(message, type) {
    const bar = document.getElementById("statusBar");
    bar.textContent = message;
    bar.className = "status-bar " + type;
}

function clearStatus() {
    const bar = document.getElementById("statusBar");
    bar.className = "status-bar";
    bar.style.display = "none";
}

// --- Auth ---

async function checkSession() {
    try {
        const data = await api("/api/me");
        if (data.logged_in) {
            currentUser = data;
            showApp();
        }
    } catch (e) {
        // Not logged in
    }
}

async function login(event) {
    event.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const errorDiv = document.getElementById("loginError");
    errorDiv.textContent = "";

    try {
        const data = await api("/api/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        currentUser = { ...data, logged_in: true, is_finalized: false };
        // Re-check finalization status
        const me = await api("/api/me");
        currentUser = me;
        showApp();
    } catch (e) {
        errorDiv.textContent = e.message;
    }
}

async function logout() {
    await api("/api/logout", { method: "POST" });
    currentUser = null;
    document.getElementById("loginScreen").style.display = "flex";
    document.getElementById("appScreen").style.display = "none";
    document.getElementById("headerRight").style.display = "none";
    document.getElementById("previewSection").style.display = "none";
}

function showApp() {
    document.getElementById("loginScreen").style.display = "none";
    document.getElementById("appScreen").style.display = "block";
    document.getElementById("headerRight").style.display = "flex";
    document.getElementById("userName").textContent = currentUser.full_name;
    document.getElementById("userSpecialty").textContent = currentUser.specialty;

    if (currentUser.is_finalized) {
        document.getElementById("finalizedBanner").style.display = "block";
        document.getElementById("finalizeBtn").disabled = true;
        document.getElementById("finalizeBtn").textContent = "Kesinlestirildi";
    } else {
        document.getElementById("finalizedBanner").style.display = "none";
        document.getElementById("finalizeBtn").disabled = false;
        document.getElementById("finalizeBtn").textContent = "Kesinlestir";
    }

    loadCalendar();
}

// --- Calendar ---

async function loadCalendar() {
    try {
        const [cal, sels, docs] = await Promise.all([
            api(`/api/calendar/${TARGET_YEAR}/${TARGET_MONTH}`),
            api(`/api/selections/${TARGET_YEAR}/${TARGET_MONTH}`),
            api("/api/doctors"),
        ]);
        calendarData = cal;
        selectionsData = sels;
        allDoctors = docs;
        document.getElementById("monthTitle").textContent =
            `${cal.month_name} ${cal.year} - Nobet Cizelgesi`;
        renderCalendar();
    } catch (e) {
        showToast(e.message, "error");
    }
}

function renderCalendar() {
    const grid = document.getElementById("calendarGrid");
    grid.innerHTML = "";

    // Day headers (Monday-Sunday)
    const dayNames = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"];
    dayNames.forEach((name) => {
        const header = document.createElement("div");
        header.className = "calendar-header";
        header.textContent = name;
        grid.appendChild(header);
    });

    // Build selection lookup: { date: [{ doctor_id, full_name, specialty, is_finalized }] }
    const selByDate = {};
    selectionsData.forEach((s) => {
        if (!selByDate[s.date]) selByDate[s.date] = [];
        selByDate[s.date].push(s);
    });

    // Find first day of month's weekday (0=Monday in our grid)
    const firstDay = calendarData.days[0];
    const firstDate = new Date(firstDay.date + "T00:00:00");
    let startDay = firstDate.getDay(); // 0=Sunday
    // Convert to Monday-based: Mon=0, Tue=1, ... Sun=6
    startDay = startDay === 0 ? 6 : startDay - 1;

    // Empty cells before first day
    for (let i = 0; i < startDay; i++) {
        const empty = document.createElement("div");
        empty.className = "calendar-cell empty";
        grid.appendChild(empty);
    }

    // Day cells
    calendarData.days.forEach((day) => {
        const cell = document.createElement("div");
        cell.className = `calendar-cell ${day.type}`;

        const assignments = selByDate[day.date] || [];
        const myAssignment = assignments.find(
            (a) => currentUser && a.doctor_id === currentUser.id
        );
        const sameSpecAssignment = assignments.find(
            (a) =>
                currentUser &&
                a.specialty === currentUser.specialty &&
                a.doctor_id !== currentUser.id
        );

        if (myAssignment) {
            cell.classList.add("selected-mine");
        }
        if (sameSpecAssignment) {
            cell.classList.add("conflict");
        }

        // Clickable if not finalized and no same-specialty conflict (or is own selection)
        const canSelect =
            currentUser &&
            !currentUser.is_finalized &&
            (!sameSpecAssignment || myAssignment);
        if (canSelect) {
            cell.classList.add("selectable");
            cell.onclick = () => toggleSelection(day, myAssignment);
        }

        // Day number
        const dayNum = document.createElement("div");
        dayNum.className = "day-number";
        dayNum.textContent = day.day;
        cell.appendChild(dayNum);

        // Duty badge
        const badge = document.createElement("span");
        badge.className = `duty-badge duty-${day.duty_hours}`;
        badge.textContent = `${day.duty_hours}s`;
        cell.appendChild(badge);

        // Holiday name
        if (day.holiday_name) {
            const hname = document.createElement("div");
            hname.className = "holiday-name";
            hname.textContent = day.holiday_name;
            cell.appendChild(hname);
        }

        // Assigned doctors
        if (assignments.length > 0) {
            const container = document.createElement("div");
            container.className = "assigned-doctors";
            assignments.forEach((a) => {
                const tag = document.createElement("span");
                tag.className = "assigned-doctor";
                if (currentUser && a.doctor_id === currentUser.id) {
                    tag.classList.add("mine");
                } else if (
                    currentUser &&
                    a.specialty === currentUser.specialty
                ) {
                    tag.classList.add("same-specialty");
                } else {
                    tag.classList.add("other");
                }
                // Shorten name: "Dr. Ayse Kara" -> "Dr. A. Kara"
                const shortName = a.full_name;
                tag.textContent = `${shortName} (${a.specialty})`;
                container.appendChild(tag);
            });
            cell.appendChild(container);
        }

        grid.appendChild(cell);
    });

    renderTotals();
}

function renderTotals() {
    const bar = document.getElementById("totalsBar");
    bar.innerHTML = "";

    // Sum hours per doctor
    const doctorTotals = {};
    selectionsData.forEach((s) => {
        const key = s.doctor_id;
        if (!doctorTotals[key]) {
            doctorTotals[key] = { full_name: s.full_name, specialty: s.specialty, hours: 0 };
        }
        doctorTotals[key].hours += s.duty_hours;
    });

    // Sort by specialty then name
    const sorted = Object.values(doctorTotals).sort((a, b) =>
        a.specialty.localeCompare(b.specialty) || a.full_name.localeCompare(b.full_name)
    );

    // Also show doctors with 0 hours
    allDoctors.forEach((d) => {
        if (!selectionsData.some((s) => s.doctor_id === d.id)) {
            sorted.push({ full_name: d.full_name, specialty: d.specialty, hours: 0 });
        }
    });
    sorted.sort((a, b) =>
        a.specialty.localeCompare(b.specialty) || a.full_name.localeCompare(b.full_name)
    );

    sorted.forEach((d) => {
        const card = document.createElement("div");
        card.className = "total-card" + (d.hours > 0 ? " has-hours" : "");

        card.innerHTML = `
            <span class="spec-name">${d.specialty}</span>
            <span class="doc-name">${d.full_name}</span>
            <span class="total-hours">${d.hours}s</span>
        `;
        bar.appendChild(card);
    });
}

// --- Selection toggle ---

async function toggleSelection(day, existing) {
    if (currentUser.is_finalized) return;

    try {
        if (existing) {
            await api(`/api/selections/${day.date}`, { method: "DELETE" });
            showToast("Nobet secimi kaldirildi.", "info");
        } else {
            await api("/api/selections", {
                method: "POST",
                body: JSON.stringify({
                    date: day.date,
                    duty_hours: day.duty_hours,
                }),
            });
            showToast("Nobet secimi kaydedildi.", "success");
        }
        // Refresh selections
        selectionsData = await api(
            `/api/selections/${TARGET_YEAR}/${TARGET_MONTH}`
        );
        renderCalendar();
    } catch (e) {
        showToast(e.message, "error");
    }
}

// --- Preview ---

function showPreview() {
    const section = document.getElementById("previewSection");
    const content = document.getElementById("previewContent");

    if (section.style.display === "block") {
        section.style.display = "none";
        return;
    }

    // Build selection lookup
    const selByDate = {};
    selectionsData.forEach((s) => {
        if (!selByDate[s.date]) selByDate[s.date] = [];
        selByDate[s.date].push(s);
    });

    // Get unique specialties
    const specialties = [...new Set(allDoctors.map((d) => d.specialty))].sort();

    // Build table
    let html = '<table class="preview-table">';
    html += "<thead><tr><th>Tarih</th><th>Gun</th><th>Saat</th>";
    specialties.forEach((s) => {
        html += `<th>${s}</th>`;
    });
    html += "</tr></thead><tbody>";

    calendarData.days.forEach((day) => {
        const rowClass =
            day.type === "workday" ? "workday-row" :
            day.type === "weekend" ? "weekend-row" : "holiday-row";
        html += `<tr class="${rowClass}">`;
        html += `<td>${day.date}</td>`;
        html += `<td>${day.day_name}</td>`;
        html += `<td>${day.duty_hours}s</td>`;

        const dayAssignments = selByDate[day.date] || [];
        specialties.forEach((spec) => {
            const assigned = dayAssignments.find((a) => a.specialty === spec);
            if (assigned) {
                html += `<td class="has-assignment">${assigned.full_name}</td>`;
            } else {
                html += "<td>-</td>";
            }
        });

        html += "</tr>";
    });

    // Total hours row
    const totalsBySpec = {};
    specialties.forEach((spec) => { totalsBySpec[spec] = 0; });
    selectionsData.forEach((s) => {
        totalsBySpec[s.specialty] = (totalsBySpec[s.specialty] || 0) + s.duty_hours;
    });

    html += '<tr class="workday-row" style="font-weight:700; border-top:2px solid #1a5276;">';
    html += '<td colspan="3" style="text-align:right;">Toplam Saat</td>';
    specialties.forEach((spec) => {
        const total = totalsBySpec[spec] || 0;
        html += `<td class="has-assignment">${total > 0 ? total + "s" : "-"}</td>`;
    });
    html += "</tr>";

    html += "</tbody></table>";
    content.innerHTML = html;
    section.style.display = "block";
    section.scrollIntoView({ behavior: "smooth" });
}

// --- Finalize ---

async function finalizeSelections() {
    // Check if doctor has any selections
    const mySelections = selectionsData.filter(
        (s) => s.doctor_id === currentUser.id
    );
    if (mySelections.length === 0) {
        showToast("Kesinlestirilecek nobet seciminiz yok.", "error");
        return;
    }

    if (
        !confirm(
            `${mySelections.length} nobet seciminizi kesinlestirmek istediginize emin misiniz?\n\nKesinlestirme sonrasi degisiklik yapamazsiniz.`
        )
    ) {
        return;
    }

    try {
        await api(`/api/finalize/${TARGET_YEAR}/${TARGET_MONTH}`, {
            method: "POST",
        });
        showToast("Nobet cizelgeniz kesinlestirildi!", "success");
        currentUser.is_finalized = true;
        document.getElementById("finalizedBanner").style.display = "block";
        document.getElementById("finalizeBtn").disabled = true;
        document.getElementById("finalizeBtn").textContent = "Kesinlestirildi";
        // Refresh
        selectionsData = await api(
            `/api/selections/${TARGET_YEAR}/${TARGET_MONTH}`
        );
        renderCalendar();
    } catch (e) {
        showToast(e.message, "error");
    }
}

// --- Export ---

function exportExcel() {
    window.location.href = `/api/export/${TARGET_YEAR}/${TARGET_MONTH}`;
}

// --- Init ---
checkSession();
