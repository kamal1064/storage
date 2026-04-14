"""
Employee Management System - Flask Backend
==========================================
Run with: python app.py
"""


from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import hashlib
import os
import csv
import io
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'emp_mgmt_secret_key_2024'  # Change in production

DB_PATH = 'database.db'

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────


def get_db():
    """Connect to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    # Users table (owners/admins)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Employees table
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            age INTEGER,
            gender TEXT,
            salary REAL,
            leaves INTEGER DEFAULT 0,
            working_hours REAL DEFAULT 40,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(emp_id, date),
            FOREIGN KEY (emp_id) REFERENCES employees(id)
        )
    ''')

    # Salary records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS salary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            present_days INTEGER DEFAULT 0,
            total_salary REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Unpaid',
            paid_at TEXT,
            FOREIGN KEY (emp_id) REFERENCES employees(id)
        )
    ''')

    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────


def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(f):
    """Decorator to protect routes that need login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_current_user_id():
    return session.get('user_id')

# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            return render_template('signup.html', error='All fields are required.')

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hash_password(password))
            )
            conn.commit()
            return redirect(url_for('login', success='Account created! Please login.'))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error='Username or email already exists.')
        finally:
            conn.close()

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    success = request.args.get('success')
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials.')

    return render_template('login.html', success=success)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────


@app.route('/dashboard')
@login_required
def dashboard():
    uid = get_current_user_id()
    conn = get_db()

    # Summary stats
    employees = conn.execute(
        'SELECT * FROM employees WHERE user_id = ?', (uid,)).fetchall()
    total_emp = len(employees)
    avg_salary = round(sum(e['salary']
                       for e in employees) / total_emp, 2) if total_emp else 0
    avg_age = round(sum(e['age'] for e in employees) /
                    total_emp, 1) if total_emp else 0
    total_hrs = sum(e['working_hours'] for e in employees)

    # Attendance chart data (last 30 days across all employees)
    today = date.today().isoformat()
    att_data = conn.execute('''
        SELECT status, COUNT(*) as cnt FROM attendance
        WHERE emp_id IN (SELECT id FROM employees WHERE user_id = ?)
        GROUP BY status
    ''', (uid,)).fetchall()
    present_count = next((r['cnt']
                         for r in att_data if r['status'] == 'Present'), 0)
    absent_count = next((r['cnt']
                        for r in att_data if r['status'] == 'Absent'), 0)

    # Salary distribution for chart
    salary_data = [{'name': e['name'], 'salary': e['salary']}
                   for e in employees]

    # Recent attendance
    recent_att = conn.execute('''
        SELECT e.name, a.date, a.status FROM attendance a
        JOIN employees e ON e.id = a.emp_id
        WHERE e.user_id = ?
        ORDER BY a.date DESC LIMIT 10
    ''', (uid,)).fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_emp=total_emp,
                           avg_salary=avg_salary,
                           avg_age=avg_age,
                           total_hrs=total_hrs,
                           present_count=present_count,
                           absent_count=absent_count,
                           salary_data=salary_data,
                           recent_att=recent_att,
                           today=today
                           )

# ─────────────────────────────────────────
# EMPLOYEES
# ─────────────────────────────────────────


@app.route('/employees')
@login_required
def employees():
    uid = get_current_user_id()
    search = request.args.get('q', '').strip()
    conn = get_db()

    if search:
        emps = conn.execute(
            "SELECT * FROM employees WHERE user_id = ? AND name LIKE ? ORDER BY name",
            (uid, f'%{search}%')
        ).fetchall()
    else:
        emps = conn.execute(
            "SELECT * FROM employees WHERE user_id = ? ORDER BY name",
            (uid,)
        ).fetchall()

    conn.close()
    return render_template('employees.html', employees=emps, search=search)


@app.route('/employees/add', methods=['POST'])
@login_required
def add_employee():
    uid = get_current_user_id()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    age = int(request.form.get('age', 0))
    gender = request.form.get('gender', '')
    salary = float(request.form.get('salary', 0))
    leaves = int(request.form.get('leaves', 0))
    hours = float(request.form.get('working_hours', 40))

    if not name:
        return redirect(url_for('employees'))

    conn = get_db()
    conn.execute(
        'INSERT INTO employees (name, phone, age, gender, salary, leaves, working_hours, user_id) VALUES (?,?,?,?,?,?,?,?)',
        (name, phone, age, gender, salary, leaves, hours, uid)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('employees'))


@app.route('/employees/edit/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
    uid = get_current_user_id()
    conn = get_db()

    if request.method == 'POST':
        conn.execute('''
            UPDATE employees SET name=?, phone=?, age=?, gender=?, salary=?, leaves=?, working_hours=?
            WHERE id=? AND user_id=?
        ''', (
            request.form.get('name'),
            request.form.get('phone'),
            int(request.form.get('age', 0)),
            request.form.get('gender'),
            float(request.form.get('salary', 0)),
            int(request.form.get('leaves', 0)),
            float(request.form.get('working_hours', 40)),
            emp_id, uid
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('employees'))

    emp = conn.execute(
        'SELECT * FROM employees WHERE id=? AND user_id=?', (emp_id, uid)).fetchone()
    conn.close()
    if not emp:
        return redirect(url_for('employees'))
    return render_template('edit_employee.html', emp=emp)


@app.route('/employees/delete/<int:emp_id>', methods=['POST'])
@login_required
def delete_employee(emp_id):
    uid = get_current_user_id()
    conn = get_db()
    # Delete related records first
    conn.execute('DELETE FROM attendance WHERE emp_id=?', (emp_id,))
    conn.execute('DELETE FROM salary_records WHERE emp_id=?', (emp_id,))
    conn.execute(
        'DELETE FROM employees WHERE id=? AND user_id=?', (emp_id, uid))
    conn.commit()
    conn.close()
    return redirect(url_for('employees'))

# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────


@app.route('/attendance')
@login_required
def attendance():
    uid = get_current_user_id()
    selected_date = request.args.get('date', date.today().isoformat())
    conn = get_db()

    emps = conn.execute(
        'SELECT * FROM employees WHERE user_id=? ORDER BY name', (uid,)).fetchall()

    # Get attendance status for selected date
    att_map = {}
    records = conn.execute(
        'SELECT emp_id, status FROM attendance WHERE date=?', (selected_date,)
    ).fetchall()
    for r in records:
        att_map[r['emp_id']] = r['status']

    conn.close()
    return render_template('attendance.html',
                           employees=emps,
                           att_map=att_map,
                           selected_date=selected_date
                           )


@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
    """AJAX endpoint to mark attendance."""
    data = request.get_json()
    emp_id = data.get('emp_id')
    att_date = data.get('date')
    status = data.get('status')  # 'Present' or 'Absent'

    if not all([emp_id, att_date, status]):
        return jsonify({'success': False, 'message': 'Missing data'})

    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO attendance (emp_id, date, status) VALUES (?, ?, ?)
            ON CONFLICT(emp_id, date) DO UPDATE SET status=excluded.status
        ''', (emp_id, att_date, status))
        conn.commit()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


@app.route('/attendance/summary')
@login_required
def attendance_summary():
    uid = get_current_user_id()
    month_filter = request.args.get('month', datetime.now().strftime('%Y-%m'))
    conn = get_db()

    emps = conn.execute(
        'SELECT * FROM employees WHERE user_id=? ORDER BY name', (uid,)).fetchall()

    summary = []
    for e in emps:
        # Filter by month if provided
        if month_filter:
            records = conn.execute('''
                SELECT status, COUNT(*) as cnt FROM attendance
                WHERE emp_id=? AND date LIKE ?
                GROUP BY status
            ''', (e['id'], f'{month_filter}%')).fetchall()
        else:
            records = conn.execute('''
                SELECT status, COUNT(*) as cnt FROM attendance
                WHERE emp_id=?
                GROUP BY status
            ''', (e['id'],)).fetchall()

        present = next((r['cnt']
                       for r in records if r['status'] == 'Present'), 0)
        absent = next((r['cnt']
                      for r in records if r['status'] == 'Absent'), 0)
        summary.append({
            'id': e['id'],
            'name': e['name'],
            'present': present,
            'absent': absent,
            'total': present + absent
        })

    conn.close()
    return render_template('attendance_summary.html',
                           summary=summary,
                           month_filter=month_filter
                           )

# ─────────────────────────────────────────
# SALARY
# ─────────────────────────────────────────


@app.route('/salary')
@login_required
def salary():
    uid = get_current_user_id()
    month_filter = request.args.get('month', datetime.now().strftime('%Y-%m'))
    conn = get_db()

    emps = conn.execute(
        'SELECT * FROM employees WHERE user_id=? ORDER BY name', (uid,)).fetchall()

    salary_details = []
    for e in emps:
        # Count present days in the selected month
        present_days = conn.execute('''
            SELECT COUNT(*) as cnt FROM attendance
            WHERE emp_id=? AND date LIKE ? AND status='Present'
        ''', (e['id'], f'{month_filter}%')).fetchone()['cnt']

        salary_per_day = e['salary'] / 30
        final_salary = round(salary_per_day * present_days, 2)

        # Check if salary record exists
        rec = conn.execute('''
            SELECT * FROM salary_records WHERE emp_id=? AND month=?
        ''', (e['id'], month_filter)).fetchone()

        # Upsert salary record
        if not rec:
            conn.execute('''
                INSERT OR IGNORE INTO salary_records (emp_id, month, present_days, total_salary, payment_status)
                VALUES (?, ?, ?, ?, 'Unpaid')
            ''', (e['id'], month_filter, present_days, final_salary))
            conn.commit()
            payment_status = 'Unpaid'
            paid_at = None
        else:
            # Update the record with latest calculation
            conn.execute('''
                UPDATE salary_records SET present_days=?, total_salary=?
                WHERE emp_id=? AND month=? AND payment_status='Unpaid'
            ''', (present_days, final_salary, e['id'], month_filter))
            conn.commit()
            payment_status = rec['payment_status']
            paid_at = rec['paid_at']

        salary_details.append({
            'id': e['id'],
            'name': e['name'],
            'monthly_salary': e['salary'],
            'present_days': present_days,
            'salary_per_day': round(salary_per_day, 2),
            'final_salary': final_salary,
            'payment_status': payment_status,
            'paid_at': paid_at
        })

    conn.close()
    return render_template('salary.html',
                           salary_details=salary_details,
                           month_filter=month_filter
                           )


@app.route('/salary/mark_paid', methods=['POST'])
@login_required
def mark_paid():
    data = request.get_json()
    emp_id = data.get('emp_id')
    month = data.get('month')
    paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    conn.execute('''
        UPDATE salary_records SET payment_status='Paid', paid_at=?
        WHERE emp_id=? AND month=?
    ''', (paid_at, emp_id, month))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'paid_at': paid_at})

# ─────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────


@app.route('/export')
@login_required
def export_data():
    uid = get_current_user_id()
    conn = get_db()

    output = io.StringIO()
    writer = csv.writer(output)

    # === EMPLOYEES ===
    writer.writerow(['=== EMPLOYEES ==='])
    writer.writerow(['ID', 'Name', 'Phone', 'Age', 'Gender',
                    'Monthly Salary', 'Leaves', 'Working Hours/Week'])
    emps = conn.execute(
        'SELECT * FROM employees WHERE user_id=?', (uid,)).fetchall()
    for e in emps:
        writer.writerow([e['id'], e['name'], e['phone'], e['age'],
                        e['gender'], e['salary'], e['leaves'], e['working_hours']])

    writer.writerow([])

    # === ATTENDANCE ===
    writer.writerow(['=== ATTENDANCE ==='])
    writer.writerow(['Employee ID', 'Employee Name', 'Date', 'Status'])
    att = conn.execute('''
        SELECT a.emp_id, e.name, a.date, a.status FROM attendance a
        JOIN employees e ON e.id = a.emp_id
        WHERE e.user_id=?
        ORDER BY a.date DESC
    ''', (uid,)).fetchall()
    for a in att:
        writer.writerow([a['emp_id'], a['name'], a['date'], a['status']])

    writer.writerow([])

    # === SALARY ===
    writer.writerow(['=== SALARY RECORDS ==='])
    writer.writerow(['Employee ID', 'Employee Name', 'Month',
                    'Present Days', 'Total Salary', 'Payment Status', 'Paid At'])
    sal = conn.execute('''
        SELECT s.emp_id, e.name, s.month, s.present_days, s.total_salary, s.payment_status, s.paid_at
        FROM salary_records s
        JOIN employees e ON e.id = s.emp_id
        WHERE e.user_id=?
        ORDER BY s.month DESC
    ''', (uid,)).fetchall()
    for s in sal:
        writer.writerow([s['emp_id'], s['name'], s['month'], s['present_days'],
                        s['total_salary'], s['payment_status'], s['paid_at']])

    conn.close()

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'employee_data_{date.today().isoformat()}.csv'
    )

# ─────────────────────────────────────────
# API - CHART DATA
# ─────────────────────────────────────────


@app.route('/api/chart/attendance')
@login_required
def chart_attendance():
    uid = get_current_user_id()
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    conn = get_db()

    emps = conn.execute(
        'SELECT id, name FROM employees WHERE user_id=?', (uid,)).fetchall()
    labels, present_data, absent_data = [], [], []

    for e in emps:
        p = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE emp_id=? AND date LIKE ? AND status='Present'",
            (e['id'], f'{month}%')
        ).fetchone()['c']
        a = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE emp_id=? AND date LIKE ? AND status='Absent'",
            (e['id'], f'{month}%')
        ).fetchone()['c']
        labels.append(e['name'])
        present_data.append(p)
        absent_data.append(a)

    conn.close()
    return jsonify({'labels': labels, 'present': present_data, 'absent': absent_data})

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────


if __name__ == '__main__':
    init_db
    print("Database initialized")
    print("Starting Employee Management System...")
    print("Open: http://127.0.0.1:5000")
    app.run(debug=True)
