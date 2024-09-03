from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')  # Use environment variable for secret key

# Database connection configuration
db_config = {
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'sohel7866'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'cube_stock_application')
}

# Function to get a database connection
def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        flash(f"Database connection error: {err}")
        return None

# User authentication logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            db.close()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials!')
        return redirect(url_for('login'))
    return render_template('login.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['name']
        username = request.form['username']
        email_address = request.form['email']
        phone_number = request.form['phone']
        country = request.form['country']
        password = generate_password_hash(request.form['password'])

        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO users (full_name, username, email_address, phone_number, country, password_hash) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (full_name, username, email_address, phone_number, country, password))
            db.commit()
            db.close()
            
            flash('Registration successful!')
            return redirect(url_for('login'))
        flash('Registration failed!')
    return render_template('register.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', username=session['username'], user_id=session['user_id'])
    return redirect(url_for('login'))

# Stock data page
@app.route('/')
def stock_data():
    if 'user_id' in session:
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute('''
                SELECT 
                    stock_info.Security_ID, 
                    stock_info.Y_Ticker,
                    stock_info.G_Ticker,
                    stock_info.Description, 
                    stock_info.SRC, 
                    stock_data.Local_Price,
                    stock_data.Previous_Price,
                    stock_data.Differences_Percentage,
                    stock_data.Differences,
                    stock_data.Local_Price_Date,
                    stock_data.Vendor,
                    stock_data.User_ID
                FROM 
                    stock_data
                INNER JOIN 
                    stock_info
                ON 
                    stock_data.Security_ID = stock_info.Security_ID;
            ''')
            records = cursor.fetchall()
            db.close()
            return render_template('stock_data.html', records=records, user_id=session['user_id'])
        flash('Error fetching stock data.')
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Update stock data
@app.route('/update', methods=['POST'])
def update_stock():
    if 'user_id' in session:
        security_id = request.form['Security_ID']
        local_price = request.form['Local_Price']
        local_price_date = request.form['Local_Price_Date']

        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute('''
                UPDATE stock_data 
                SET Local_Price = %s, Local_Price_Date = %s 
                WHERE Security_ID = %s
            ''', (local_price, local_price_date, security_id))
            db.commit()
            db.close()
            
            flash('Stock data updated!')
            return redirect(url_for('stock_data'))
        flash('Error updating stock data.')
    return redirect(url_for('stock_data'))

# Export stock data
@app.route('/export')
def export_data():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = '''
            SELECT 
                stock_info.Security_ID, 
                stock_info.Y_Ticker,
                stock_info.G_Ticker,
                stock_info.Description, 
                stock_info.SRC, 
                stock_data.Local_Price,
                stock_data.Previous_Price,
                stock_data.Differences_Percentage,
                stock_data.Differences,
                stock_data.Local_Price_Date,
                stock_data.Vendor,
                stock_data.User_ID
            FROM 
                stock_data
            INNER JOIN 
                stock_info
            ON 
                stock_data.Security_ID = stock_info.Security_ID;
        '''
        cursor.execute(query)
        records = cursor.fetchall()
        conn.close()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='stock_data.csv'
        )
    flash('Error exporting data.')
    return redirect(url_for('stock_data'))


    

# Profile page
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            full_name = request.form['full_name']
            email_address = request.form['email_address']
            phone_number = request.form['phone_number']
            country = request.form['country']
            
            db = get_db_connection()
            if db:
                cursor = db.cursor()
                cursor.execute('''
                    UPDATE users
                    SET full_name = %s, email_address = %s, phone_number = %s, country = %s
                    WHERE id = %s
                ''', (full_name, email_address, phone_number, country, user_id))
                db.commit()
                db.close()
                flash('Profile updated successfully!')
                return redirect(url_for('profile'))
            flash('Error updating profile.')
        
        db = get_db_connection()
        if db:
            cursor = db.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            db.close()
            return render_template('profile.html', user=user)
        flash('Error fetching user profile.')
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Support page
@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        user_id = session.get('user_id')
        subject = request.form['subject']
        message = request.form['message']
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO support_tickets (user_id, subject, message)
                VALUES (%s, %s, %s)
            ''', (user_id, subject, message))
            db.commit()
            db.close()
            flash('Your message has been sent to support!')
            return redirect(url_for('support'))
        
    return render_template('support.html')

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# Profile update API endpoint
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        full_name = request.form.get('full_name')
        email_address = request.form.get('email_address')
        phone_number = request.form.get('phone_number')
        country = request.form.get('country')

        db = get_db_connection()
        if db:
            cursor = db.cursor()
            cursor.execute('''
                UPDATE users
                SET full_name = %s, email_address = %s, phone_number = %s, country = %s
                WHERE id = %s
            ''', (full_name, email_address, phone_number, country, user_id))
            db.commit()
            db.close()
            return jsonify({'status': 'success'}), 200
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

if __name__ == '__main__':
    app.run(debug=True)
