from mysql.connector import Error
from sql_connection import get_sql_connection
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import traceback
import sys
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# --- Configuration ---
ALERT_EMAILS = ["shahratnesh1298@gmail.com", "mahimavageriya09@gmail.com", "himanshujain8619@gmail.com", "suchivageriya@gmail.com"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "jainhimanshu469@gmail.com"  # Your Gmail address
SMTP_PASSWORD = "zpzg weyw ciil jtmi"        # Use Gmail App Password (not your regular password)

def send_email_alert(subject, message_body, html_body=None):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        for recipient in ALERT_EMAILS:
            msg = MIMEMultipart("alternative")
            msg['From'] = SMTP_USERNAME
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(message_body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            server.sendmail(SMTP_USERNAME, recipient, msg.as_string())
        server.quit()
        print("Email alert sent successfully to all recipients.")
    except Exception as e:
        print(f"Email alert error: {e}")
        
        
def send_stock_alert(product_name, quantity, unit_name, price_per_unit):
    subject = "Stock Alert From Sunilam Alert"
    text_body = (
        f"Stock Alert from Sunilam Traders\n"
        f"Product: {product_name}\n"
        f"Quantity Left: {quantity} {unit_name}\n"
        f"Price per unit: ₹{price_per_unit}\n\n"
        f"Please update the stock as soon as possible.\n"
        f"Thanks,\nSunilam Traders"
    )
    html_body = f"""
    <div style="border:1px solid #eee; border-radius:10px; padding:20px; max-width:400px; font-family:Arial, sans-serif; background:#fafafa;">
      <h2 style="color:#d35400; text-align:center;">Stock Alert from Sunilam Traders</h2>
      <table style="width:100%; border-collapse:collapse; margin-bottom:16px;">
        <tr>
          <td style="font-weight:bold; padding:8px;">Product Name:</td>
          <td style="padding:8px;">{product_name}</td>
        </tr>
        <tr>
          <td style="font-weight:bold; padding:8px;">Quantity Left:</td>
          <td style="padding:8px;">{quantity} {unit_name}</td>
        </tr>
        <tr>
          <td style="font-weight:bold; padding:8px;">Price per unit:</td>
          <td style="padding:8px;">₹{price_per_unit}</td>
        </tr>
      </table>
      <div style="color:#34495e; font-size:15px; margin-bottom:10px;">
        Please update the stock as soon as possible.
      </div>
      <div style="text-align:right; color:#888; font-size:14px;">
        Thanks,<br>Sunilam Traders
      </div>
    </div>
    """
    send_email_alert(subject, text_body, html_body)

app = Flask(__name__, static_folder='../ui', template_folder='../ui')
CORS(app)

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, product_name, quantity, unit_id, price_per_unit FROM stock_data"
        cursor.execute(query)
        stocks = cursor.fetchall()
        fetch_unit_name = "SELECT unit_name FROM unit_of_measure WHERE id = %s"
        for stock in stocks:
            cursor.execute(fetch_unit_name, (stock['unit_id'],))
            unit_name_result = cursor.fetchone()
            stock['unit_name'] = unit_name_result['unit_name'] if unit_name_result else None
        return jsonify(stocks)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()

@app.route('/api/stocks', methods=['POST'])
def add_stock_route():
    conn = get_sql_connection()
    cursor = conn.cursor()
    try:
        data = request.json
        query = """
            INSERT INTO stock_data (product_name, quantity, unit_id, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """
        values = (data['product_name'], data['quantity'], data['unit_id'], data['price_per_unit'])
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'message': 'Stock added successfully!'}), 201
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()

@app.route('/api/stocks/<int:id>', methods=['PUT'])
def update_stock(id):
    conn = get_sql_connection()
    cursor = conn.cursor()
    try:
        data = request.json
        query = """
            UPDATE stock_data 
            SET product_name=%s, quantity=%s, unit_id=%s, price_per_unit=%s
            WHERE id=%s
        """
        values = (
            data['product_name'],
            data['quantity'],
            data['unit_id'],
            data['price_per_unit'],
            id
        )
        cursor.execute(query, values)

        # --- AUTOMATIC EMAIL ALERT IF LOW STOCK ---
        if float(data['quantity']) < 5:
            cursor.execute("SELECT unit_name FROM unit_of_measure WHERE id = %s", (data['unit_id'],))
            unit_name_result = cursor.fetchone()
            unit_name_val = unit_name_result[0] if unit_name_result else ""
            try:
                send_stock_alert(data['product_name'], data['quantity'], unit_name_val, data['price_per_unit'])
            except Exception as e:
                print(f"Email alert error: {e}")

        conn.commit()
        return jsonify({'message': 'Stock updated successfully'}), 200
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()

@app.route('/api/stocks/<int:id>', methods=['DELETE'])
def delete_stock(id):
    conn = get_sql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM stock_data WHERE id = %s", (id,))
        stock = cursor.fetchone()
        if stock and stock[0] > 0:
            return jsonify({"error": "Cannot delete stock with quantity > 0"}), 400
        query = "DELETE FROM stock_data WHERE id=%s"
        cursor.execute(query, (id,))
        conn.commit()
        return jsonify({'message': 'Stock deleted successfully'}), 200
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()

@app.route('/api/stocks/very_low_stock', methods=['GET'])
def get_very_low_stock():
    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT id, product_name, quantity, unit_id, price_per_unit 
            FROM stock_data 
            WHERE quantity < 5
        """
        cursor.execute(query)
        very_low_stock_items = cursor.fetchall()
        fetch_unit_name = "SELECT unit_name FROM unit_of_measure WHERE id = %s"
        for item in very_low_stock_items:
            cursor.execute(fetch_unit_name, (item['unit_id'],))
            unit_name_result = cursor.fetchone()
            item['unit_name'] = unit_name_result['unit_name'] if unit_name_result else None
        return jsonify(very_low_stock_items)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()

@app.route('/api/send_email_alert', methods=['POST'])
def send_email_alert_route():
    try:
        data = request.get_json()
        low_stock_items = data.get('low_stock_items')

        if not low_stock_items:
            return jsonify({"error": "No Stock alert."}), 400

        message = "Sunilam Traders - Low Stock Alert\n\n"
        for item in low_stock_items:
            product_name = item.get('product_name', 'N/A')
            quantity = item.get('quantity', 'N/A')
            unit_name = item.get('unit_name', '')
            message += f"- {product_name}: {quantity} {unit_name}\n"
        message += "\nPlease update the stock as soon as possible."
    
        send_stock_alert(message)

        return jsonify({"message": "Stock alert sent successfully."}), 200

    except Exception as e:
        print("An error occurred while sending bulk email alert:")
        traceback.print_exc()
        return jsonify({"error": f"Email alert send error: {str(e)}"}), 500

@app.route('/api/stock/add_user', methods=['POST'])
def add_user():
    try:
        data = request.json
        username = data['username']
        password = data['password']
        hashed_pw = generate_password_hash(password)

        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
        conn.commit()
        cursor.close()
        return jsonify({'message': 'User added successfully!'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/login', methods=['POST'])
def login_stock():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            return jsonify({'message': 'Login successful!'}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/signup', methods=['POST'])
def signup_stock():
    try:
        data = request.json
        name = data.get('name')
        username = data.get('username')
        password = data.get('password')

        if not name or not username or not password:
            return jsonify({'error': 'All fields are required'}), 400

        conn = get_sql_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already exists'}), 409
        hashed_password = generate_password_hash(password)    
        query = "INSERT INTO users (name, username, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (name, username, hashed_password))
        conn.commit()
        cursor.close()

        return jsonify({'message': 'User created successfully!'}), 201
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/business', methods=['POST'])
def business_stock():
    try:
        data = request.json
        required_fields = ['product_name', 'quantity', 'unit_name', 'price_per_unit', 'amount', 'transaction_type', 'entry_date']
        for field in required_fields:
            if field not in data or data[field] == "":
                return jsonify({"error": f"Missing field: {field}"}), 400

        product_name = data['product_name']
        quantity = float(data['quantity'])
        unit_name = data['unit_name']
        price_per_unit = float(data['price_per_unit'])
        customer_name = data.get('customer_name')
        amount = float(data['amount'])
        transaction_type = data['transaction_type']
        entry_date = data['entry_date']
        entry_by = data.get('entry_by') or 'SystemUser'

        conn = get_sql_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM unit_of_measure WHERE unit_name = %s", (unit_name,))
        unit_id_result = cursor.fetchone()
        if not unit_id_result:
            print(f"Unit not found: {unit_name}")
            cursor.close()
            return jsonify({"error": f"Unit not found: {unit_name}"}), 400
        unit_id = unit_id_result[0]

        insert_query = """
            INSERT INTO business (product_name, quantity, unit_id, price_per_unit,
                                  customer_name, amount, transaction_type, entry_datetime, entry_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            product_name, quantity, unit_id, price_per_unit,
            customer_name, amount, transaction_type,
            entry_date +  " 00:00:00", entry_by
        ))

        cursor.execute("SELECT id, quantity FROM stock_data WHERE product_name = %s", (product_name,))
        stock = cursor.fetchone()
        if stock:
            stock_id, existing_qty = stock
            if transaction_type == 'Buy':
                new_qty = existing_qty + quantity
            else:
                new_qty = existing_qty - quantity

            cursor.execute("UPDATE stock_data SET quantity = %s, price_per_unit = %s WHERE id = %s", (new_qty, price_per_unit, stock_id))

            # --- AUTOMATIC EMAIL ALERT IF LOW STOCK ---
            if new_qty < 5:
                cursor.execute("SELECT unit_name FROM unit_of_measure WHERE id = %s", (unit_id,))
                unit_name_result = cursor.fetchone()
                unit_name_val = unit_name_result[0] if unit_name_result else ""
                try:
                    send_stock_alert(product_name, new_qty, unit_name_val, price_per_unit)
                except Exception as e:
                    print(f"Email alert error: {e}")

        else:
            cursor.execute("""
                INSERT INTO stock_data (product_name, quantity, unit_id, price_per_unit)
                VALUES (%s, %s, %s, %s)
            """, (product_name, quantity, unit_id, price_per_unit))
            # --- AUTOMATIC EMAIL ALERT IF LOW STOCK ---
            if quantity < 5:
                cursor.execute("SELECT unit_name FROM unit_of_measure WHERE id = %s", (unit_id,))
                unit_name_result = cursor.fetchone()
                unit_name_val = unit_name_result[0] if unit_name_result else ""
                try:
                    send_stock_alert(product_name, quantity, unit_name_val, price_per_unit)
                except Exception as e:
                    print(f"Email alert error: {e}")

        conn.commit()
        cursor.close()
        return jsonify({"message": "Business entry saved and stock updated."})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/business", methods=["GET"])
def get_daily_business_states():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)

        today = datetime.now().strftime("%Y-%m-%d")
        query = """
            SELECT 
                product_name, quantity, unit_id, price_per_unit,
                customer_name, amount, transaction_type, entry_datetime, entry_by
            FROM business
            WHERE DATE(entry_datetime) = %s
        """
        cursor.execute(query, (today,))
        rows = cursor.fetchall()

        fetch_unit_name = "SELECT unit_name FROM unit_of_measure WHERE id = %s"
        for row in rows:
            cursor.execute(fetch_unit_name, (row['unit_id'],))
            unit_name_result = cursor.fetchone()
            row['unit_name'] = unit_name_result['unit_name'] if unit_name_result else None
        cursor.close()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/stocks/report', methods=['GET'])
def get_report():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)

        # Get query params
        report_type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        offset = (page - 1) * page_size

        # Build WHERE clause based on params
        where_clauses = ["b.transaction_type = 'sell'"]
        params = []

        if report_type == 'week':
            today = datetime.now().date()
            week_ago = today - timedelta(days=6)
            where_clauses.append("DATE(b.entry_datetime) BETWEEN %s AND %s")
            params.extend([week_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')])
        elif report_type == 'month':
            today = datetime.now().date()
            first_day = today.replace(day=1)
            where_clauses.append("DATE(b.entry_datetime) BETWEEN %s AND %s")
            params.extend([first_day.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')])
        elif start_date and end_date:
            where_clauses.append("DATE(b.entry_datetime) BETWEEN %s AND %s")
            params.extend([start_date, end_date])

        where_sql = " AND ".join(where_clauses)

        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT b.product_name)
            FROM business b
            WHERE {where_sql}
        """
        cursor.execute(count_query, tuple(params))
        total_count = cursor.fetchone()['COUNT(DISTINCT b.product_name)']

        # Get paginated data
        query = f"""
            SELECT 
                b.product_name, 
                SUM(b.quantity) AS total_quantity,
                SUM(b.amount) AS total_amount
            FROM business b
            WHERE {where_sql}
            GROUP BY b.product_name
            ORDER BY total_quantity DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, tuple(params) + (page_size, offset))
        report_data = cursor.fetchall()

        total_sales = sum([row["total_amount"] for row in report_data])
        for row in report_data:
            row["total_sales"] = row["total_amount"]

        cursor.close()
        conn.close()
        return jsonify({
            "items": report_data,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        })

    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/units', methods=['GET'])
def get_units():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, unit_name FROM unit_of_measure")
        units = cursor.fetchall()
        cursor.close()
        return jsonify(units)
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/logout', methods=['POST'])
def logout_stock():
    try:
        return jsonify({'message': 'Logout successful!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

# --- HTML Page Serving Routes ---
@app.route('/')
@app.route('/index.html')
def index_page():
    return app.send_static_file('index.html')

@app.route('/stocks.html')
def stocks_page():
    return app.send_static_file('stocks.html')

@app.route('/add_stock.html')
def add_stock_page():
    return app.send_static_file('add_stock.html')

@app.route('/report.html')
def report_page():
    return app.send_static_file('report.html')

@app.route('/update_stock.html')
def update_stock_page():
    return app.send_static_file('update_stock.html')

@app.route('/home.html')
def home_page():
    return app.send_static_file('home.html')

@app.route('/signup.html')
def signup_page():
    return app.send_static_file('signup.html')

@app.route('/business.html')
def business_page():
    return app.send_static_file('business.html')

@app.route('/dailystates.html')
def dailystates_page():
    return app.send_static_file('dailystates.html')

@app.route('/stock_low.html')
def stock_low_page():
    return app.send_static_file('stock_low.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)