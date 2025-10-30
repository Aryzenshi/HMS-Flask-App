from flask import Flask, render_template, request, redirect, url_for, flash, g
import mysql.connector as sql
from datetime import date, timedelta
from db_utils import (
    DB_CONFIG, create_initial_connection, setup_database_and_tables, 
    get_available_rooms, get_customer_by_id, insert_new_customer, 
    create_new_booking, get_active_bookings_for_customer, check_in_customer, 
    check_out_customer, get_all_records, cleanup, validate_phno, validate_govt_id
)

app = Flask(__name__)
app.secret_key = 'super_secret_hotel_key_change_me'

# --- Database Connection ---

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        try:
            g.db = sql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database']
            )
        except sql.Error as e:
            flash(f'Database Connection Error: {e}', 'error')
            g.db = None
            app.logger.error(f"Database Connection Error: {e}")
            
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

# --- Application Startup Setup ---

def initialize_db():
    """Initializes the database schema before the application runs."""
    print("--- Running Database Initialization ---")
    
    temp_db = create_initial_connection(DB_CONFIG['user'], DB_CONFIG['password'], DB_CONFIG['host'])
    
    if temp_db:
        try:
            setup_database_and_tables(temp_db)
            print("Database and tables are ready.")
            cleanup(temp_db)
            print("Initial cleanup performed.")
        except Exception as e:
            print(f"FATAL: Could not complete database setup. {e}")
            exit()
        finally:
            if temp_db.is_connected():
                temp_db.close()
    else:
        print("FATAL: Cannot connect to MySQL server. Check credentials in db_utils.py.")
        exit()

# --- Routes ---

@app.route('/')
def home():
    """Home page/Main Menu."""
    return render_template('index.html', title='Home - Hotel HMS')

# --- Booking Routes ---

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    db = get_db()
    if not db:
        return redirect(url_for('home'))

    today = date.today()
    default_checkin = today.strftime('%Y-%m-%d')
    default_checkout = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    available_rooms = []
    
    if request.method == 'POST':
        try:
            checkin = request.form.get('checkin')
            checkout = request.form.get('checkout')
            
            checkin_date = date.fromisoformat(checkin)
            checkout_date = date.fromisoformat(checkout)
            
            if checkin_date >= checkout_date:
                flash('Check-out date must be after Check-in date.', 'warning')
                return render_template('booking.html', title='New Booking', default_checkin=checkin, default_checkout=checkout)

            if checkin_date < today:
                flash('Check-in date cannot be in the past.', 'warning')
                return render_template('booking.html', title='New Booking', default_checkin=default_checkin, default_checkout=default_checkout)

            available_rooms = get_available_rooms(db, checkin, checkout)
            
            return render_template('booking.html', 
                                   title='Select Room & Customer',
                                   available_rooms=available_rooms, 
                                   checkin=checkin, 
                                   checkout=checkout,
                                   step=2)
            
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('booking'))

    return render_template('booking.html', 
                           title='New Booking', 
                           default_checkin=default_checkin, 
                           default_checkout=default_checkout,
                           step=1)

@app.route('/complete_booking', methods=['POST'])
def complete_booking():
    db = get_db()
    if not db:
        return redirect(url_for('home'))

    room_num = request.form.get('room_num')
    checkin = request.form.get('checkin_date')
    checkout = request.form.get('checkout_date')
    
    name = request.form.get('name', '').strip().title()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip().capitalize()
    govt_id_type = request.form.get('govt_id_type', '').strip().upper()
    govt_id_number = request.form.get('govt_id_number', '').strip().upper()
    
    if not (room_num and checkin and checkout and name and phone and govt_id_type and govt_id_number):
        flash('Missing required booking or customer information.', 'error')
        return redirect(url_for('booking'))

    try:
        room_num = int(room_num)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        flash('Invalid room number or date format.', 'error')
        return redirect(url_for('booking'))

    if not validate_phno(phone):
        flash('Invalid Phone Number. Must be 10 digits.', 'error')
        return redirect(url_for('booking'))
    
    if govt_id_type not in ['UID', 'DL', 'PSP'] or not validate_govt_id(govt_id_type, govt_id_number):
        flash(f'Invalid {govt_id_type} ID format.', 'error')
        return redirect(url_for('booking'))
    
    cust_id, message = insert_new_customer(db, name, phone, address, govt_id_type, govt_id_number)
    
    if "already exists" in message:
        flash(f'Customer already exists (CustID: {cust_id}). Proceeding with booking.', 'info')
    elif "created successfully" in message:
        flash(message, 'success')
    else:
        flash(f'Error saving customer: {message}', 'error')
        return redirect(url_for('booking'))

    success, booking_message = create_new_booking(db, cust_id, checkin_date, checkout_date, room_num)
    
    if success:
        flash(f'Booking for Room {room_num} successful! CustID: {cust_id}', 'success')
    else:
        flash(f'Booking failed: {booking_message}', 'error')

    return redirect(url_for('booking'))

# --- Arrival/Departure Routes ---

@app.route('/arrival_management', methods=['GET'])
def arrival_management():
    db = get_db()
    if not db:
        return redirect(url_for('home'))

    mycur = db.cursor(dictionary=True)
    mycur.execute("""
        SELECT DISTINCT C.CustID, C.Name, C.Phone_No
        FROM Customer C
        JOIN Booking B ON C.CustID = B.CustID
        WHERE B.status IN ('not_arrived', 'checkedin')
        ORDER BY C.Name
    """)
    active_customers = mycur.fetchall()
    
    return render_template('arrival_management.html', 
                           title='Arrival/Departure', 
                           active_customers=active_customers)

@app.route('/customer_details/<cust_id>', methods=['GET'])
def customer_details(cust_id):
    db = get_db()
    if not db:
        return redirect(url_for('home'))
        
    customer = get_customer_by_id(db, cust_id)
    bookings = get_active_bookings_for_customer(db, cust_id)
    
    if not customer:
        flash(f'Customer ID {cust_id} not found.', 'error')
        return redirect(url_for('arrival_management'))

    return render_template('customer_details.html', 
                           title='Customer Actions', 
                           customer=customer, 
                           bookings=bookings)

@app.route('/checkin/<cust_id>', methods=['POST'])
def checkin_action(cust_id):
    db = get_db()
    if not db:
        return redirect(url_for('home'))
        
    success, message = check_in_customer(db, cust_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'warning')
        
    return redirect(url_for('customer_details', cust_id=cust_id))

@app.route('/checkout/<cust_id>/<int:room_no>', methods=['POST'])
def checkout_action(cust_id, room_no):
    db = get_db()
    if not db:
        return redirect(url_for('home'))
        
    success, message = check_out_customer(db, cust_id, room_no)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'warning')
        
    return redirect(url_for('customer_details', cust_id=cust_id))

# --- Records Routes ---

@app.route('/records')
def records():
    db = get_db()
    if not db:
        return redirect(url_for('home'))

    customer_records = get_all_records(db, 'Customer')
    booking_records = get_all_records(db, 'Booking')

    # Calculate current room availability (similar to RoomsAvailable function)
    mycur = db.cursor()
    mycur.execute("SELECT DISTINCT(roomno) FROM booking WHERE status != 'checkedout'")
    rooms_booked_temp = {i[0] for i in mycur.fetchall()}
    all_rooms = set(range(1, 101))
    rooms_available_list = sorted(list(all_rooms - rooms_booked_temp))
    rooms_booked_list = sorted(list(rooms_booked_temp))

    return render_template('records.html',
                           title='Hotel Records',
                           customer_records=customer_records,
                           booking_records=booking_records,
                           rooms_available_list=rooms_available_list,
                           rooms_booked_list=rooms_booked_list)

# --- Run the App ---
if __name__ == '__main__':
    initialize_db()
    app.run(debug=True, host='127.0.0.1', port=5000)
