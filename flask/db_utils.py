import datetime
import string
import random
import re
import mysql.connector as sql
from mysql.connector import pooling

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # REPLACE WITH YOUR ACTUAL USER
    'password': '1230', # REPLACE WITH YOUR ACTUAL PASSWORD
    'database': 'hms'
}

# ----------------- Database Connection and Setup -----------------

def create_initial_connection(user, password, host='localhost'):
    """Tries to connect to MySQL server without a database name."""
    try:
        db = sql.connect(
            host=host,
            user=user,
            password=password
        )
        return db
    except sql.errors.ProgrammingError as e:
        print(f"Database Connection Failed: {e}")
        return None

def setup_database_and_tables(db):
    """Ensures the specified database and necessary tables exist."""
    db_name = DB_CONFIG['database']
    try:
        mycur = db.cursor()
        
        mycur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        mycur.execute(f"USE {db_name}")

        print(f"NOW USING DATABASE: {db_name}")
        print("Creating User Tables...")

        mycur.execute("""
            CREATE TABLE IF NOT EXISTS Customer (
                CustID VARCHAR(5) PRIMARY KEY,
                Name VARCHAR(50) NOT NULL,
                Phone_No CHAR(10) NOT NULL, 
                Address VARCHAR(100),
                Govt_ID_Type ENUM('UID', 'DL', 'PSP') NOT NULL,
                Govt_ID_Number VARCHAR(20) NOT NULL,
                CONSTRAINT unique_govt_id UNIQUE (Govt_ID_Type, Govt_ID_Number)
            );
        """)

        mycur.execute("""
            CREATE TABLE IF NOT EXISTS Booking (
                SrNo INT AUTO_INCREMENT PRIMARY KEY,
                CustID VARCHAR(5) NOT NULL,
                checkin DATE NOT NULL,
                checkout DATE NOT NULL,
                roomno INT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'not_arrived',
                CONSTRAINT ID_Customer FOREIGN KEY (CustID) REFERENCES Customer(CustID) ON DELETE CASCADE
            );
        """)
        db.commit()
        print("Tables Created/Verified.")
    except Exception as e:
        print(f"Error during database setup: {e}")
        raise

# --- Utility Functions ---

def id_gen(size = 5, chars = string.ascii_uppercase + string.digits):
    """Generates a random ID."""
    return ''.join(random.choice(chars) for _ in range(size))

def validate_phno(phno, l=10):
    """Validates phone number length."""
    return len(phno) == l and phno.isdigit()

def validate_govt_id(govt_id_type, govt_id_number):
    """Validates government ID format."""
    patterns = {
        "UID": r"^\d{4} \d{4} \d{4}$|^\d{12}$",
        "PSP": r"^[A-Z]{1}-\d{7}$|^[A-Z]{1}\d{7}$",
        "DL": r"^[A-Z]{2}-\d{2}-(19|20)\d{2}-\d{7}$|^[A-Z]{2}\d{13}$"
    }
    return bool(re.match(patterns.get(govt_id_type, r''), govt_id_number))

def format_govt_id(govt_id_type, govt_id_number):
    """Formats government ID for display."""
    govt_id_number = govt_id_number.replace(' ', '').replace('-', '')
    if govt_id_type == "UID":
        return f"{govt_id_number[:4]} {govt_id_number[4:8]} {govt_id_number[8:]}"
    elif govt_id_type == "PSP":
        return f"{govt_id_number[0]}-{govt_id_number[1:]}"
    elif govt_id_type == "DL":
        return govt_id_number
    return govt_id_number.upper()

def cleanup(db):
    """Cleans up old 'checkedout' bookings."""
    try:
        mycur = db.cursor()
        today = datetime.date.today()
        mycur.execute("DELETE FROM Booking WHERE checkout < %s AND status = 'checkedout'", (today - datetime.timedelta(days=183),)) 
        db.commit()
    except Exception as e:
        print(f"Cleanup Error: {e}")
        db.rollback()


# --- Core CRUD Functions for Flask Routes ---

def get_available_rooms(db, checkin_date, checkout_date):
    """Returns a list of all rooms not booked between the given dates."""
    mycur = db.cursor(dictionary=True)
    mycur.execute("""
        SELECT DISTINCT roomno FROM Booking 
        WHERE NOT (checkout <= %s OR checkin >= %s) AND status != 'checkedout'
    """, (checkin_date, checkout_date))
    
    booked_rooms = {row['roomno'] for row in mycur.fetchall()}
    
    all_rooms = list(range(1, 101))
    available_rooms = [r for r in all_rooms if r not in booked_rooms]
    
    return available_rooms

def insert_new_customer(db, name, phone, address, govt_id_type, govt_id_number):
    """Inserts a new customer record and returns the new CustID."""
    mycur = db.cursor()
    
    mycur.execute("""
        SELECT CustID FROM Customer 
        WHERE Govt_ID_Type = %s AND Govt_ID_Number = %s
    """, (govt_id_type, govt_id_number))
    
    existing = mycur.fetchone()
    if existing:
        return existing[0], "Customer already exists with this ID."

    CID = id_gen()
    while True:
        mycur.execute("SELECT CustID FROM Customer WHERE CustID = %s", (CID,))
        if not mycur.fetchone():
            break
        CID = id_gen()

    vals = (CID, name, phone, address, govt_id_type, govt_id_number)
    comd = "INSERT INTO Customer (CustID, Name, Phone_No, Address, Govt_ID_Type, Govt_ID_Number) VALUES (%s, %s, %s, %s, %s, %s)"
    mycur.execute(comd, vals)
    db.commit()
    return CID, "New Customer created successfully."

def create_new_booking(db, cust_id, checkin_date, checkout_date, room_num):
    """Inserts a new booking record."""
    mycur = db.cursor()
    
    today = datetime.date.today()
    status = "checkedin" if checkin_date == today else "not_arrived"

    mycur.execute("""
        SELECT COUNT(*) FROM Booking 
        WHERE roomno = %s AND NOT (checkout <= %s OR checkin >= %s)
    """, (room_num, checkin_date, checkout_date))

    if mycur.fetchone()[0] > 0:
        return False, "Room is no longer available for the selected dates."

    vals = (cust_id, checkin_date, checkout_date, room_num, status)
    comd = "INSERT INTO Booking (CustID, checkin, checkout, roomno, status) VALUES (%s, %s, %s, %s, %s)"
    mycur.execute(comd, vals)
    db.commit()
    return True, "Booking Successful."


def get_customer_by_id(db, cust_id):
    """Fetches customer details by ID."""
    mycur = db.cursor(dictionary=True)
    mycur.execute("SELECT * FROM Customer WHERE CustID = %s", (cust_id,))
    return mycur.fetchone()

def get_active_bookings_for_customer(db, cust_id):
    """Fetches active bookings for a given customer."""
    mycur = db.cursor(dictionary=True)
    mycur.execute("""
        SELECT B.*, C.Name, C.Phone_No 
        FROM Booking B
        JOIN Customer C ON B.CustID = C.CustID
        WHERE B.CustID = %s AND B.status IN ('not_arrived', 'checkedin')
    """, (cust_id,))
    return mycur.fetchall()

def check_in_customer(db, cust_id):
    """Updates a booking status to 'checkedin'."""
    mycur = db.cursor()
    
    mycur.execute("""
        SELECT roomno, checkin FROM Booking 
        WHERE CustID = %s AND status = 'not_arrived'
    """, (cust_id,))
    booking = mycur.fetchone()

    if not booking:
        return False, "No pending booking found for this Customer ID."
    
    room_no, checkin_date = booking

    if checkin_date > datetime.date.today():
        return False, f"Cannot check in before the scheduled date: {checkin_date}."

    mycur.execute("UPDATE Booking SET status = 'checkedin' WHERE CustID = %s AND status = 'not_arrived'", (cust_id,))
    db.commit()
    return True, f"Customer {cust_id} checked in to Room {room_no} successfully!"


def check_out_customer(db, cust_id, room_no):
    """Updates a booking status to 'checkedout'."""
    mycur = db.cursor()

    mycur.execute("""
        SELECT checkout FROM Booking 
        WHERE CustID = %s AND roomno = %s AND status = 'checkedin'
    """, (cust_id, room_no))
    
    result = mycur.fetchone()

    if not result:
        return False, f"No active check-in found for Customer {cust_id} in Room {room_no}."

    original_checkout_date = result[0]
    today_date = datetime.date.today()

    if today_date < original_checkout_date:
        mycur.execute("UPDATE Booking SET checkout = %s WHERE CustID = %s AND roomno = %s", (today_date, cust_id, room_no))

    mycur.execute("UPDATE Booking SET status = 'checkedout' WHERE CustID = %s AND roomno = %s AND status = 'checkedin'", (cust_id, room_no))
    db.commit()
    return True, f"Customer {cust_id} checked out from Room {room_no} successfully."

def get_all_records(db, table_name):
    """Fetches all records from a specified table."""
    if table_name not in ['Customer', 'Booking']:
        return []
    mycur = db.cursor(dictionary=True)
    mycur.execute(f"SELECT * FROM {table_name}")
    return mycur.fetchall()
