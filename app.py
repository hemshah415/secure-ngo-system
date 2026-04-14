from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from rsa_utils import generate_keys, encrypt_message, decrypt_message

app = Flask(__name__)
app.secret_key = "secret123"


# ✅ FIXED DATABASE PATH
def get_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "database.db")
    return sqlite3.connect(db_path)


# =========================
# 📝 REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        public_key, private_key = generate_keys()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password, public_key, private_key) VALUES (?, ?, ?, ?, ?)",
            (name, email, password, public_key, private_key)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# =========================
# 🔐 LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session.clear()  # ✅ IMPORTANT FIX
            session['user_id'] = user[0]
            return redirect('/dashboard')
        else:
            return "Invalid credentials"

    return render_template('login.html')


# =========================
# 🏠 DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('dashboard.html')



# =========================
# 📤 SEND MESSAGE
# =========================
@app.route('/send', methods=['GET', 'POST'])
def send():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    # Show all users except current user
    cursor.execute("SELECT id, name FROM users WHERE id != ?", (session['user_id'],))
    users = cursor.fetchall()

    if request.method == 'POST':
        receiver_id = request.form['receiver']
        message = request.form['message']

        cursor.execute("SELECT public_key FROM users WHERE id=?", (receiver_id,))
        public_key = cursor.fetchone()[0]

        encrypted_msg = encrypt_message(public_key, message)

        cursor.execute(
            "INSERT INTO messages (sender_id, receiver_id, encrypted_message) VALUES (?, ?, ?)",
            (session['user_id'], receiver_id, encrypted_msg)
        )

        conn.commit()  # ✅ IMPORTANT
        conn.close()

        return redirect('/send')

    conn.close()
    return render_template('send.html', users=users)


# =========================
# 📥 VIEW MESSAGES
# =========================
@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, sender_id, encrypted_message FROM messages WHERE receiver_id=?",
        (session['user_id'],)
    )

    msgs = cursor.fetchall()
    print("MESSAGES:", msgs)
    conn.close()

    return render_template('messages.html', messages=msgs)


# =========================
# 🔓 DECRYPT MESSAGE
# =========================
@app.route('/decrypt/<int:msg_id>')
def decrypt(msg_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT encrypted_message FROM messages WHERE id=?", (msg_id,))
    encrypted_msg = cursor.fetchone()[0]

    cursor.execute("SELECT private_key FROM users WHERE id=?", (session['user_id'],))
    private_key = cursor.fetchone()[0]

    conn.close()

    decrypted = decrypt_message(private_key, encrypted_msg)

    return f"<h2>Decrypted Message:</h2><p>{decrypted}</p>"


# =========================
# 🚪 LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# =========================
# 🚀 RUN APP
# =========================
if __name__ == '__main__':
    app.run(debug=True)
    