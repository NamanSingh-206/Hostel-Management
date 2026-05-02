# app.py — Complete Final Version

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
import datetime

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

# ── Auth Decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'warden_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def student_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_id' not in session:
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated

# ── Index ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'warden_id' in session:
        return redirect(url_for('dashboard'))
    if 'student_id' in session:
        return redirect(url_for('student_dashboard'))
    return render_template('login.html')

# ── Warden Login / Logout ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'warden_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM wardens WHERE username = %s", (username,))
        warden = cur.fetchone()
        cur.close()
        if warden and check_password_hash(warden['password'], password):
            session['warden_id']   = warden['id']
            session['warden_name'] = warden['name']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Student Login / Logout ────────────────────────────────────────────────────
@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if 'student_id' in session:
        return redirect(url_for('student_dashboard'))
    if request.method == 'POST':
        usn      = request.form['usn'].strip().lower()
        password = request.form['password'].strip()
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT * FROM students
            WHERE LOWER(usn) = %s AND status = 'active'
        """, (usn,))
        student = cur.fetchone()
        cur.close()
        if student:
            stored_pw = student['password']
            if stored_pw is None:
                if password == student['phone']:
                    session['student_id']   = student['id']
                    session['student_name'] = student['name']
                    session['student_usn']  = student['usn']
                    return redirect(url_for('student_dashboard'))
                else:
                    flash('Default password is your registered phone number.', 'info')
            elif check_password_hash(stored_pw, password):
                session['student_id']   = student['id']
                session['student_name'] = student['name']
                session['student_usn']  = student['usn']
                return redirect(url_for('student_dashboard'))
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('USN not found or account inactive.', 'danger')
    return render_template('student_login.html')

@app.route('/student/logout')
def student_logout():
    session.clear()
    return redirect(url_for('student_login'))

# ── Student Dashboard ─────────────────────────────────────────────────────────
@app.route('/student/dashboard')
@student_login_required
def student_dashboard():
    sid = session['student_id']
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT s.*, r.room_number, r.room_type, r.floor
        FROM students s
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE s.id = %s
    """, (sid,))
    student = cur.fetchone()

    cur.execute("""
        SELECT * FROM fees
        WHERE student_id = %s
        ORDER BY due_date DESC
    """, (sid,))
    fees = cur.fetchall()

    cur.execute("""
        SELECT * FROM complaints
        WHERE student_id = %s
        ORDER BY filed_on DESC
    """, (sid,))
    complaints = cur.fetchall()

    paid_count      = sum(1 for f in fees if f['status'] == 'paid')
    pending_count   = sum(1 for f in fees if f['status'] == 'pending')
    overdue_count   = sum(1 for f in fees if f['status'] == 'overdue')
    open_complaints = sum(1 for c in complaints if c['status'] == 'open')

    cur.close()
    return render_template('student_dashboard.html',
        student=student,
        fees=fees,
        complaints=complaints,
        paid_count=paid_count,
        pending_count=pending_count,
        overdue_count=overdue_count,
        open_complaints=open_complaints
    )

# ── Student File Complaint ────────────────────────────────────────────────────
@app.route('/student/complaint/add', methods=['POST'])
@student_login_required
def student_add_complaint():
    sid         = session['student_id']
    category    = request.form['category']
    description = request.form['description'].strip()
    if not description:
        flash('Please enter a description.', 'danger')
        return redirect(url_for('student_dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO complaints (student_id, category, description, status)
        VALUES (%s, %s, %s, 'open')
    """, (sid, category, description))
    mysql.connection.commit()
    cur.close()
    flash('Complaint filed successfully!', 'success')
    return redirect(url_for('student_dashboard'))

# ── USN Duplicate Check API ───────────────────────────────────────────────────
@app.route('/check_usn')
@login_required
def check_usn():
    usn = request.args.get('usn', '').strip().lower()
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM students WHERE LOWER(usn) = %s", (usn,))
    exists = cur.fetchone() is not None
    cur.close()
    return jsonify({'exists': exists})

# ── Phone Duplicate Check API ─────────────────────────────────────────────────
@app.route('/check_phone')
@login_required
def check_phone():
    phone = request.args.get('phone', '').strip()
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM students WHERE phone = %s", (phone,))
    exists = cur.fetchone() is not None
    cur.close()
    return jsonify({'exists': exists})

# ── Email Duplicate Check API ─────────────────────────────────────────────────
@app.route('/check_email')
@login_required
def check_email():
    email = request.args.get('email', '').strip()
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM students WHERE email = %s", (email,))
    exists = cur.fetchone() is not None
    cur.close()
    return jsonify({'exists': exists})

# ── Room Number Duplicate Check API ──────────────────────────────────────────
@app.route('/check_room')
@login_required
def check_room():
    room_number = request.args.get('room_number', '').strip()
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM rooms WHERE room_number = %s", (room_number,))
    exists = cur.fetchone() is not None
    cur.close()
    return jsonify({'exists': exists})

# ── Warden Dashboard ──────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) as total FROM students WHERE status = 'active'")
    total_students = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM rooms WHERE status = 'available'")
    available_rooms = cur.fetchone()['total']

    cur.execute("""
        SELECT COUNT(*) as total FROM fees
        WHERE status = 'pending' OR status = 'overdue'
    """)
    pending_fees = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM complaints WHERE status = 'open'")
    open_complaints = cur.fetchone()['total']

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
    fee_data = [
        {'month': row['month'], 'total': float(row['total'])}
        for row in fee_rows
    ]

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
        recent_students=recent_students
    )

# ── Students ──────────────────────────────────────────────────────────────────
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
    cur.execute("""
        SELECT * FROM rooms
        WHERE status = 'available' OR status = 'full'
        ORDER BY floor, room_number
    """)
    rooms = cur.fetchall()
    cur.close()
    return render_template('students.html', students=all_students, rooms=rooms)

@app.route('/students/add', methods=['POST'])
@login_required
def add_student():
    data    = request.form
    usn     = data['usn'].strip().lower()
    phone   = data['phone'].strip()
    email   = data['email'].strip()
    room_id = data['room_id'] if data['room_id'] else None

    if not phone.isdigit() or len(phone) != 10:
        flash('Phone number must be exactly 10 digits.', 'warning')
        return redirect(url_for('students'))

    cur = mysql.connection.cursor()

    cur.execute("SELECT id FROM students WHERE LOWER(usn) = %s", (usn,))
    if cur.fetchone():
        flash(f'USN {usn.upper()} is already taken. Please use a different number.', 'warning')
        cur.close()
        return redirect(url_for('students'))

    cur.execute("SELECT id FROM students WHERE phone = %s", (phone,))
    if cur.fetchone():
        flash(f'Phone number {phone} is already registered with another student.', 'warning')
        cur.close()
        return redirect(url_for('students'))

    if email:
        cur.execute("SELECT id FROM students WHERE email = %s", (email,))
        if cur.fetchone():
            flash(f'Email {email} is already registered with another student.', 'warning')
            cur.close()
            return redirect(url_for('students'))

    if room_id:
        cur.execute("SELECT capacity, occupied FROM rooms WHERE id = %s", (room_id,))
        room = cur.fetchone()
        if room and room['occupied'] >= room['capacity']:
            flash(f'This room is already full ({room["occupied"]}/{room["capacity"]} occupied). Please choose another room.', 'warning')
            cur.close()
            return redirect(url_for('students'))

    cur.execute("""
        INSERT INTO students (name, usn, email, phone, course, year, room_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (data['name'], usn,
          email if email else None,
          phone, data['course'],
          data['year'], room_id))

    student_id = cur.lastrowid

    if room_id:
        cur.execute("UPDATE rooms SET occupied = occupied + 1 WHERE id = %s", (room_id,))
        cur.execute("""
            UPDATE rooms
            SET status = CASE
                WHEN occupied >= capacity THEN 'full'
                ELSE 'available'
            END
            WHERE id = %s
        """, (room_id,))
        cur.execute("""
            INSERT INTO allocations (student_id, room_id)
            VALUES (%s, %s)
        """, (student_id, room_id))

    mysql.connection.commit()
    cur.close()
    flash(f'Student {data["name"]} added successfully with USN {usn.upper()}!', 'success')
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
            SET status = CASE
                WHEN occupied >= capacity THEN 'full'
                ELSE 'available'
            END
            WHERE id = %s
        """, (student['room_id'],))

    cur.execute("DELETE FROM complaints  WHERE student_id = %s", (id,))
    cur.execute("DELETE FROM fees        WHERE student_id = %s", (id,))
    cur.execute("DELETE FROM allocations WHERE student_id = %s", (id,))
    cur.execute("DELETE FROM students    WHERE id = %s", (id,))

    mysql.connection.commit()
    cur.close()
    flash('Student removed successfully.', 'info')
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
    cur  = mysql.connection.cursor()

    cur.execute("SELECT id FROM rooms WHERE room_number = %s", (data['room_number'],))
    if cur.fetchone():
        flash(f'Room number {data["room_number"]} already exists. Please use a different number.', 'warning')
        cur.close()
        return redirect(url_for('rooms'))

    cur.execute("""
        INSERT INTO rooms (room_number, floor, capacity, room_type)
        VALUES (%s, %s, %s, %s)
    """, (data['room_number'], data['floor'],
          data['capacity'],   data['room_type']))
    mysql.connection.commit()
    cur.close()
    flash(f'Room {data["room_number"]} added successfully!', 'success')
    return redirect(url_for('rooms'))

@app.route('/rooms/delete/<int:id>')
@login_required
def delete_room(id):
    cur = mysql.connection.cursor()

    # Check if any students are currently in this room
    cur.execute("SELECT COUNT(*) as total FROM students WHERE room_id = %s", (id,))
    student_count = cur.fetchone()['total']

    if student_count > 0:
        flash(f'Cannot delete this room — {student_count} student(s) are currently assigned to it. Please reassign or remove them first.', 'warning')
        cur.close()
        return redirect(url_for('rooms'))

    # Check if room has any allocation history
    cur.execute("SELECT COUNT(*) as total FROM allocations WHERE room_id = %s", (id,))
    alloc_count = cur.fetchone()['total']

    if alloc_count > 0:
        flash('Cannot delete this room — it has allocation history. Please clear allocations first.', 'warning')
        cur.close()
        return redirect(url_for('rooms'))

    cur.execute("DELETE FROM rooms WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Room deleted successfully.', 'info')
    return redirect(url_for('rooms'))
# ── Fees ──────────────────────────────────────────────────────────────────────
@app.route('/fees')
@login_required
def fees():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.*, s.name as student_name, s.usn
        FROM fees f
        JOIN students s ON f.student_id = s.id
        ORDER BY f.due_date DESC
    """)
    all_fees = cur.fetchall()
    cur.execute("""
        SELECT id, name, usn FROM students
        WHERE status = 'active'
        ORDER BY name
    """)
    students = cur.fetchall()
    cur.close()
    return render_template('fees.html', fees=all_fees, students=students)

@app.route('/fees/add', methods=['POST'])
@login_required
def add_fee():
    data = request.form
    cur  = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO fees (student_id, amount, fee_type, due_date, status)
        VALUES (%s, %s, %s, %s, 'pending')
    """, (data['student_id'], data['amount'],
          data['fee_type'],   data['due_date']))
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

@app.route('/fees/delete/<int:id>')
@login_required
def delete_fee(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM fees WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Fee record deleted.', 'info')
    return redirect(url_for('fees'))

# ── Complaints ────────────────────────────────────────────────────────────────
@app.route('/complaints')
@login_required
def complaints():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.*, s.name as student_name, s.usn
        FROM complaints c
        JOIN students s ON c.student_id = s.id
        ORDER BY c.filed_on DESC
    """)
    all_complaints = cur.fetchall()
    cur.execute("""
        SELECT id, name, usn FROM students
        WHERE status = 'active'
        ORDER BY name
    """)
    students = cur.fetchall()
    cur.close()
    return render_template('complaints.html',
        complaints=all_complaints,
        students=students
    )

@app.route('/complaints/add', methods=['POST'])
@login_required
def add_complaint():
    data = request.form
    cur  = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO complaints (student_id, category, description, status)
        VALUES (%s, %s, %s, 'open')
    """, (data['student_id'], data['category'], data['description']))
    mysql.connection.commit()
    cur.close()
    flash('Complaint filed!', 'success')
    return redirect(url_for('complaints'))

@app.route('/complaints/progress/<int:id>')
@login_required
def progress_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE complaints SET status = 'in-progress' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Complaint marked as in-progress.', 'info')
    return redirect(url_for('complaints'))

@app.route('/complaints/resolve/<int:id>')
@login_required
def resolve_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE complaints SET status = 'resolved' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Complaint resolved.', 'success')
    return redirect(url_for('complaints'))

@app.route('/complaints/delete/<int:id>')
@login_required
def delete_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM complaints WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Complaint deleted.', 'info')
    return redirect(url_for('complaints'))

# ── Room Stats API ────────────────────────────────────────────────────────────
@app.route('/api/room_stats')
@login_required
def room_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT status, COUNT(*) as count FROM rooms GROUP BY status")
    data = cur.fetchall()
    cur.close()
    return jsonify([
        {'status': r['status'], 'count': int(r['count'])}
        for r in data
    ])
# ── Edit Student Details ──────────────────────────────────────────────────────
@app.route('/students/edit/<int:id>', methods=['POST'])
@login_required
def edit_student(id):
    data    = request.form
    phone   = data['phone'].strip()
    email   = data['email'].strip()
    room_id = data['room_id'] if data['room_id'] else None

    # Validate phone
    if not phone.isdigit() or len(phone) != 10:
        flash('Phone number must be exactly 10 digits.', 'warning')
        return redirect(url_for('students'))

    cur = mysql.connection.cursor()

    # Check phone unique — exclude current student
    cur.execute("SELECT id FROM students WHERE phone = %s AND id != %s", (phone, id))
    if cur.fetchone():
        flash(f'Phone number {phone} is already registered with another student.', 'warning')
        cur.close()
        return redirect(url_for('students'))

    # Check email unique — exclude current student
    if email:
        cur.execute("SELECT id FROM students WHERE email = %s AND id != %s", (email, id))
        if cur.fetchone():
            flash(f'Email {email} is already registered with another student.', 'warning')
            cur.close()
            return redirect(url_for('students'))

    # Get current room_id
    cur.execute("SELECT room_id FROM students WHERE id = %s", (id,))
    current = cur.fetchone()
    old_room_id = current['room_id'] if current else None

    # If room changed handle occupancy
    if str(old_room_id) != str(room_id or ''):

        # Check new room capacity
        if room_id:
            cur.execute("SELECT capacity, occupied, room_number FROM rooms WHERE id = %s", (room_id,))
            new_room = cur.fetchone()
            if new_room and new_room['occupied'] >= new_room['capacity']:
                flash(f'Room {new_room["room_number"]} is already full. Please choose another room.', 'warning')
                cur.close()
                return redirect(url_for('students'))

        # Free old room
        if old_room_id:
            cur.execute("UPDATE rooms SET occupied = occupied - 1 WHERE id = %s", (old_room_id,))
            cur.execute("""
                UPDATE rooms SET status = CASE
                    WHEN occupied >= capacity THEN 'full' ELSE 'available'
                END WHERE id = %s
            """, (old_room_id,))

        # Occupy new room
        if room_id:
            cur.execute("UPDATE rooms SET occupied = occupied + 1 WHERE id = %s", (room_id,))
            cur.execute("""
                UPDATE rooms SET status = CASE
                    WHEN occupied >= capacity THEN 'full' ELSE 'available'
                END WHERE id = %s
            """, (room_id,))
            cur.execute("""
                INSERT INTO allocations (student_id, room_id) VALUES (%s, %s)
            """, (id, room_id))

    # Update student details
    cur.execute("""
        UPDATE students
        SET name = %s, email = %s, phone = %s,
            course = %s, year = %s, room_id = %s
        WHERE id = %s
    """, (data['name'], email if email else None,
          phone, data['course'], data['year'],
          room_id, id))

    mysql.connection.commit()
    cur.close()
    flash(f'Student details updated successfully!', 'success')
    return redirect(url_for('students'))
if __name__ == '__main__':
    app.run(debug=True)
