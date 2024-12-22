from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'food_ordering'

mysql = MySQL(app)

# Daftar makanan
menu_items = [
    {"name": "Pizza Margherita", "price": 50, "image": "/static/images/pizza.jpg"},
    {"name": "Cheese Burger", "price": 30, "image": "/static/images/burger.jpg"},
    {"name": "Pasta Carbonara", "price": 40, "image": "/static/images/pasta.jpg"},
    {"name": "Salad", "price": 20, "image": "/static/images/salad.jpg"},
    {"name": "Fried Chicken", "price": 25, "image": "/static/images/pasta.jpg"},
    {"name": "Sushi Roll", "price": 45, "image": "/static/images/sushi.jpg"},
    {"name": "French Fries", "price": 15, "image": "/static/images/french_fries.jpg"},
    {"name": "Steak", "price": 60, "image": "/static/images/steak.jpg"},
    {"name": "Ice Cream Sundae", "price": 18, "image": "/static/images/ice_cream.jpg"},
    {"name": "Tacos", "price": 35, "image": "/static/images/tacos.jpg"}
]

# Daftar rekening bank dummy
# Daftar rekening bank dummy dengan logo
bank_accounts = [
    {"bank": "Bank Syariah Indonesia", "account_number": "27819911", "logo": "/static/images/bsi.png"},
    {"bank": "Bank Aceh", "account_number": "286868329", "logo": "/static/images/aceh.jpg"},
    {"bank": "Bank Mandiri", "account_number": "118291293", "logo": "/static/images/mandiri.png"},
    {"bank": "Bank BCA", "account_number": "329812983", "logo": "/static/images/bca.png"},
    {"bank": "Bank BNI", "account_number": "893123919", "logo": "/static/images/bni.png"},
    {"bank": "Bank BRI", "account_number": "991823982", "logo": "/static/images/bri.png"}
]


@app.route('/')
def landing():
    return render_template('landing.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cur.fetchone()
        cur.close()

        if user and sha256_crypt.verify(password, user[2]):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('member_dashboard') if user[3] == 'member' else url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = sha256_crypt.encrypt(request.form['password'])
        role = request.form['role']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

# Dashboard Admin
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        cur = mysql.connection.cursor()

        if request.method == 'POST':
            order_id = request.form['order_id']
            action = request.form['action']

            # Validasi nilai action
            valid_actions = ['accepted', 'pending', 'cancelled']
            if action in valid_actions:
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", (action, order_id))
                mysql.connection.commit()
            else:
                flash('Invalid action!')

        cur.execute("SELECT orders.id, users.username, orders.food_name, orders.status, orders.quantity FROM orders JOIN users ON orders.user_id = users.id")
        orders = cur.fetchall()
        cur.close()
        return render_template('admin_dashboard.html', orders=orders)
    else:
        return redirect(url_for('login'))
    
@app.route('/admin/delete', methods=['POST'])
def delete_order():
    if 'role' in session and session['role'] == 'admin':
        order_id = request.form['order_id']
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM orders WHERE id = %s", [order_id])
        mysql.connection.commit()
        cur.close()
        flash(f"Order {order_id} has been deleted!")
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))



# Dashboard Member (Menu Makanan)
@app.route('/member', methods=['GET', 'POST'])
def member_dashboard():
    if 'role' in session and session['role'] == 'member':
        user_id = session['user_id']
        cur = mysql.connection.cursor()

        if request.method == 'POST':
            food_name = request.form['food_name']
            quantity = int(request.form['quantity'])
            cur.execute("INSERT INTO orders (user_id, food_name, quantity) VALUES (%s, %s, %s)", (user_id, food_name, quantity))
            mysql.connection.commit()
            flash('Pesanan berhasil dibuat!')

        cur.close()
        return render_template('member_dashboard.html', section='menu', menu_items=menu_items)
    else:
        return redirect(url_for('login'))

# Status Pesanan
@app.route('/status')
def status():
    if 'role' in session and session['role'] == 'member':
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, food_name, quantity, status FROM orders WHERE user_id = %s", [user_id])
        orders = cur.fetchall()
        cur.close()
        return render_template('member_dashboard.html', section='status', orders=orders)
    else:
        return redirect(url_for('login'))

# Pembayaran
@app.route('/payment')
def payment():
    if 'role' in session and session['role'] == 'member':
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT food_name, quantity FROM orders WHERE user_id = %s AND status = 'accepted'", [user_id])
        orders = cur.fetchall()

        payments = []
        total_amount = 0
        for order in orders:
            food_name = order[0]
            quantity = order[1]
            price = next((item['price'] for item in menu_items if item['name'] == food_name), 0)
            total = price * quantity
            total_amount += total
            payments.append({"food_name": food_name, "quantity": quantity, "price": price, "total": total})

        cur.close()
        return render_template('payment.html', payments=payments, total_amount=total_amount, bank_accounts=bank_accounts)
    else:
        return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
