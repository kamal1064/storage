# 🏢 Employee Management System (EMS)

A full-featured web application to manage employees, attendance, and salaries.

---

## ⚡ Quick Start

### 1. Install Python
Make sure Python 3.8+ is installed: https://python.org

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the App
```bash
python app.py
```

### 4. Open in Browser
```
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```
employee_mgmt/
├── app.py                    # Flask backend (all routes + logic)
├── database.db               # SQLite database (auto-created on first run)
├── requirements.txt          # Python dependencies
├── templates/
│   ├── base.html             # Base layout (sidebar, topbar, dark mode)
│   ├── login.html            # Login page
│   ├── signup.html           # Owner signup page
│   ├── dashboard.html        # Dashboard with charts & stats
│   ├── employees.html        # Employee list + add modal
│   ├── edit_employee.html    # Edit employee form
│   ├── attendance.html       # Daily attendance marking
│   ├── attendance_summary.html # Monthly attendance summary
│   └── salary.html           # Salary calculation & payment
└── static/
    ├── css/style.css         # Complete design system
    └── js/main.js            # Dark mode, sidebar, animations
```

---

## 🔐 Authentication
- Go to `/signup` to create your owner account
- Login at `/login`
- All employee data is **scoped to your account**

---

## ✨ Features

| Feature | Description |
|---|---|
| **Dashboard** | Summary cards (employees, avg salary, avg age, working hours) + Chart.js graphs |
| **Employees** | Add / Edit / Delete / Search employees |
| **Attendance** | Mark Present/Absent per day with instant AJAX save, prevent duplicates |
| **Att. Summary** | Monthly present/absent breakdown with progress bars |
| **Salary** | Attendance-based salary calc, Mark as Paid, payment history |
| **Export** | Download all data as CSV |
| **Dark Mode** | Toggle persisted in localStorage |

---

## 💡 Salary Formula
```
salary_per_day = monthly_salary / 30
final_salary   = salary_per_day × present_days_in_month
```

---

## 🗄️ Database Tables

| Table | Description |
|---|---|
| `users` | Owner accounts with hashed passwords |
| `employees` | Employee records linked to owner |
| `attendance` | Per-employee per-day attendance status |
| `salary_records` | Monthly salary calculations and payment status |

---

## 🌐 Tech Stack
- **Backend:** Python 3 + Flask
- **Frontend:** HTML5, CSS3, Bootstrap 5
- **Charts:** Chart.js 4
- **Database:** SQLite (no setup needed)
- **Icons:** Bootstrap Icons

---

## 🔧 Troubleshooting

**Port already in use?**
```bash
python app.py  # runs on port 5000 by default
# or change port:
# app.run(debug=True, port=8080)
```

**Database issues?**
Delete `database.db` and restart — it will be recreated automatically.
