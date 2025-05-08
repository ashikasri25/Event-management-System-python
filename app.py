from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# ✅ MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="event_data"
    )

# ✅ Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['user_name']
        email = request.form['user_email']
        password = request.form['user_password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Email already registered", "error")
            db.close()
            return redirect(url_for('signup'))

        cursor.execute("""
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
        """, (username, email, hashed_password))
        db.commit()
        db.close()
        flash("Signup successful, please login", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')


# ✅ Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        db.close()

        if user and check_password_hash(user[3], password):  # user[3] contains the hashed password
            session['user_id'] = user[0]  # Store user_id in session
            session['username'] = user[1]  # Store username in session
            return redirect(url_for('home'))

        flash("Invalid credentials", "error")
        return redirect(url_for('login'))

    return render_template('login.html')

# ✅ Logout route (only one definition)
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session (log out the user)
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login'))  # Redirect to login page after logout




# ✅ Home Route (Create + Filter + List)
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db_connection()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        event_type = request.form['type']

        cursor.execute("""
            INSERT INTO events (name, description, date, location, type)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, description, date, location, event_type))
        db.commit()
        db.close()
        return redirect(url_for('home'))

    # Filters (GET)
    type_filter = request.args.get('type')
    location_filter = request.args.get('location')
    month_filter = request.args.get('month')

    query = "SELECT * FROM events WHERE 1=1"
    values = []

    if type_filter:
        query += " AND type = %s"
        values.append(type_filter)
    if location_filter:
        query += " AND location = %s"
        values.append(location_filter)
    if month_filter:
        query += " AND MONTH(date) = %s"
        values.append(month_filter)

    cursor.execute(query, values)
    events = cursor.fetchall()
    db.close()

    return render_template('home.html', events=events)




# ✅ Register Route (Event Registration)
@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    db = get_db_connection()
    cursor = db.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        cursor.execute("INSERT INTO attendees (name, email, phone) VALUES (%s, %s, %s)",
                       (name, email, phone))
        db.commit()
        attendee_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO registrations (event_id, attendee_id, registration_date)
            VALUES (%s, %s, %s)
        """, (event_id, attendee_id, datetime.now().date()))
        db.commit()
        db.close()
        return redirect(url_for('home'))

    db.close()
    return render_template('register.html', event_id=event_id)


# ✅ Report View Route
@app.route('/report')
def report():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT a.name, e.name, r.registration_date, r.status, r.id
        FROM registrations r
        JOIN attendees a ON r.attendee_id = a.id
        JOIN events e ON r.event_id = e.id
        ORDER BY r.registration_date DESC
    """)
    registrations = cursor.fetchall()
    db.close()
    return render_template('report.html', registrations=registrations)


# ✅ Manage Registrations Route
@app.route('/manage_report')
def manage_report():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT a.name, e.name, r.registration_date, r.status, r.id
        FROM registrations r
        JOIN attendees a ON r.attendee_id = a.id
        JOIN events e ON r.event_id = e.id
        ORDER BY r.registration_date DESC
    """)
    registrations = cursor.fetchall()
    db.close()
    return render_template('manage_report.html', registrations=registrations)


# ✅ Update Status Route
@app.route('/update_status/<int:registration_id>', methods=['POST'])
def update_status(registration_id):
    status = request.form['status']
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE registrations SET status = %s WHERE id = %s
    """, (status, registration_id))
    db.commit()
    db.close()
    return redirect(url_for('manage_report'))


# ✅ Run the app
if __name__ == '__main__':
    app.run(debug=True)
