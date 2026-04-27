# app.py  ← COPY THIS FILE to project root

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
import datetime

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

# ── Auth decorator ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'warden_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ─────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM wardens WHERE username = %s", (username,))
        warden = cur.fetchone()
        cur.close()
        if warden and check_password_hash(warden['password'], password):
            session['warden_id'] = warden['id']
            session['warden_name'] = warden['name']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) as total FROM students WHERE status='active'")
    total_students = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM rooms WHERE status='available'")
    available_rooms = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM fees WHERE status='pending' OR status='overdue'")
    pending_fees = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM complaints WHERE status='open'")
    open_complaints = cur.fetchone()['total']

    # Monthly fee collection for chart (last 6 months)
    cur.execute("""
        SELECT DATE_FORMAT(paid_date, '%b') as month,
               CAST(SUM(amount) AS DECIMAL(10,2)) as total
        FROM fees
        WHERE status = 'paid'
          AND paid_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY MONTH(paid_date), DATE_FORMAT(paid_date, '%b')
        ORDER BY MONTH(paid_date)
    """)
    fee_rows = cur.fetchall()

    # Convert Decimal to float so tojson works without errors
    fee_data = [
        {'month': row['month'], 'total': float(row['total'])}
        for row in fee_rows
    ]

    # Recent students
    cur.execute("""
        SELECT s.*, r.room_number
        FROM students s
        LEFT JOIN rooms r ON s.room_id = r.id
        ORDER BY s.id DESC
        LIMIT 5
    """)
    recent_students = cur.fetchall()
    cur.close()

    return render_template('dashboard.html',
        total_students=total_students,
        available_rooms=available_rooms,
        pending_fees=pending_fees,
        open_complaints=open_complaints,
        fee_data=fee_data,
        recent_students=recent_students)

# ── Students ─────────────────────────────────────────────────────────────────
@app.route('/students')
@login_required
def students():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.*, r.room_number
        FROM students s
        LEFT JOIN rooms r ON s.room_id = r.id
        ORDER BY s.id DESC
    """)
    all_students = cur.fetchall()
    cur.execute("SELECT * FROM rooms WHERE status = 'available' OR status = 'full'")
    rooms = cur.fetchall()
    cur.close()
    return render_template('students.html', students=all_students, rooms=rooms)

@app.route('/students/add', methods=['POST'])
@login_required
def add_student():
    data = request.form
    room_id = data['room_id'] if data['room_id'] else None
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO students (name, roll_number, email, phone, course, year, room_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (data['name'], data['roll_number'], data['email'],
          data['phone'], data['course'], data['year'], room_id))

    student_id = cur.lastrowid

    if room_id:
        cur.execute("UPDATE rooms SET occupied = occupied + 1 WHERE id = %s", (room_id,))
        cur.execute("""
            UPDATE rooms
            SET status = CASE WHEN occupied >= capacity THEN 'full' ELSE 'available' END
            WHERE id = %s
        """, (room_id,))
        cur.execute("""
            INSERT INTO allocations (student_id, room_id)
            VALUES (%s, %s)
        """, (student_id, room_id))

    mysql.connection.commit()
    cur.close()
    flash('Student added successfully!', 'success')
    return redirect(url_for('students'))

@app.route('/students/delete/<int:id>')
@login_required
def delete_student(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT room_id FROM students WHERE id = %s", (id,))
    student = cur.fetchone()
    if student and student['room_id']:
        cur.execute("UPDATE rooms SET occupied = occupied - 1 WHERE id = %s", (student['room_id'],))
        cur.execute("""
            UPDATE rooms
            SET status = CASE WHEN occupied >= capacity THEN 'full' ELSE 'available' END
            WHERE id = %s
        """, (student['room_id'],))
    cur.execute("DELETE FROM students WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Student removed.', 'info')
    return redirect(url_for('students'))

# ── Rooms ─────────────────────────────────────────────────────────────────────
@app.route('/rooms')
@login_required
def rooms():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM rooms ORDER BY floor, room_number")
    all_rooms = cur.fetchall()
    cur.close()
    return render_template('rooms.html', rooms=all_rooms)

@app.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    data = request.form
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO rooms (room_number, floor, capacity, room_type)
        VALUES (%s, %s, %s, %s)
    """, (data['room_number'], data['floor'], data['capacity'], data['room_type']))
    mysql.connection.commit()
    cur.close()
    flash('Room added successfully!', 'success')
    return redirect(url_for('rooms'))

@app.route('/rooms/delete/<int:id>')
@login_required
def delete_room(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM rooms WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Room deleted.', 'info')
    return redirect(url_for('rooms'))

# ── Fees ──────────────────────────────────────────────────────────────────────
@app.route('/fees')
@login_required
def fees():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.*, s.name as student_name, s.roll_number
        FROM fees f
        JOIN students s ON f.student_id = s.id
        ORDER BY f.due_date DESC
    """)
    all_fees = cur.fetchall()
    cur.execute("SELECT id, name, roll_number FROM students WHERE status = 'active'")
    students = cur.fetchall()
    cur.close()
    return render_template('fees.html', fees=all_fees, students=students)

@app.route('/fees/add', methods=['POST'])
@login_required
def add_fee():
    data = request.form
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO fees (student_id, amount, fee_type, due_date, status)
        VALUES (%s, %s, %s, %s, 'pending')
    """, (data['student_id'], data['amount'], data['fee_type'], data['due_date']))
    mysql.connection.commit()
    cur.close()
    flash('Fee record added!', 'success')
    return redirect(url_for('fees'))

@app.route('/fees/mark_paid/<int:id>')
@login_required
def mark_paid(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fees SET status = 'paid', paid_date = %s WHERE id = %s
    """, (datetime.date.today(), id))
    mysql.connection.commit()
    cur.close()
    flash('Fee marked as paid.', 'success')
    return redirect(url_for('fees'))

# ── Complaints ────────────────────────────────────────────────────────────────
@app.route('/complaints')
@login_required
def complaints():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.*, s.name as student_name
        FROM complaints c
        JOIN students s ON c.student_id = s.id
        ORDER BY c.filed_on DESC
    """)
    all_complaints = cur.fetchall()
    cur.close()
    return render_template('complaints.html', complaints=all_complaints)

@app.route('/complaints/resolve/<int:id>')
@login_required
def resolve_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE complaints SET status = 'resolved' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Complaint resolved.', 'success')
    return redirect(url_for('complaints'))

# ── API for charts ─────────────────────────────────────────────────────────────
@app.route('/api/room_stats')
@login_required
def room_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT status, COUNT(*) as count FROM rooms GROUP BY status")
    data = cur.fetchall()
    cur.close()
    # Convert to plain dict list so jsonify works cleanly
    result = [{'status': row['status'], 'count': int(row['count'])} for row in data]
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
    