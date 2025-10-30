# 🏨 Hotel Management System (HMS) - Flask Web App 🌐

## 📖 Overview
The **Hotel Management System (HMS)** is a web-based application built using **Python Flask** and **MySQL**, designed to replace the earlier console-based version.  
It provides hotel staff with a modern, secure, and responsive interface to manage room bookings, customer data, and check-in/check-out operations.

---

## ✨ Features

### 💻 Web-Based Interface
- Responsive and user-friendly web application using **Flask**, **HTML**, **Jinja2**, and **Tailwind CSS**.
- Accessible on both desktop and mobile devices.

### 🔒 Secure Database Connection
- Uses **MySQL connection pooling** and a **least-privileged user** (`hms_user`) for efficient and secure database access.

### 🧩 Core Operations
- **Booking:** Quick entry for new customers and room reservations.  
- **Arrivals & Departures:** Manage check-ins and check-outs efficiently.  
- **Records:** View comprehensive customer and booking history.

### 🧠 Data Integrity
- Validates **phone numbers** and **Government ID formats** before insertion.  
- Prevents duplicate or invalid data entries.

### 🕓 Real-Time Room Availability
- Dynamically calculates and displays available rooms for booking.

### 🧹 Automatic Cleanup
- Automatically removes bookings older than **6 months** (defined in `db_utils.py`) to maintain performance.

---

## ⚙️ Installation and Setup

### Project Setup
```bash
# Create and navigate to the project directory
mkdir hotel_hms_flask
cd hotel_hms_flask

# (Optional but recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate    # On Windows, use: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Database Configuration 
-- Create the database
```bash
CREATE DATABASE hms;
```

-- Create the dedicated, restricted application user
```bash
CREATE USER 'hms_user'@'localhost' IDENTIFIED BY 'a_secure_password';
```

-- Grant minimal privileges
```bash
GRANT SELECT, INSERT, UPDATE, DELETE ON hms.* TO 'hms_user'@'localhost';
FLUSH PRIVILEGES;
```

### Update Database Configuration
```bash
DB_CONFIG = {
    'host': 'localhost',
    'user': 'hms_user',
    'password': 'a_secure_password',  # Replace with your actual password
    'database': 'hms'
}
```

### Running the application
```bash
python app.py
```

Click the link in the terminal to access the app

## 🗃️ Database Schema

### 🧍 Customer Table

| Column         | Type                     | Constraints | Description                |
| -------------- | ------------------------ | ----------- | -------------------------- |
| CustID         | VARCHAR(5)               | PRIMARY KEY | Unique customer identifier |
| Name           | VARCHAR(20)              | NOT NULL    | Customer's full name       |
| Phone_No       | CHAR(10)                 | NOT NULL    | 10-digit phone number      |
| Address        | VARCHAR(50)              | NOT NULL    | Physical address           |
| Govt_ID_Type   | ENUM('UID', 'DL', 'PSP') | NOT NULL    | Type of government ID      |
| Govt_ID_Number | VARCHAR(20)              | UNIQUE      | ID number                  |

### 🏠 Booking Table

| Column   | Type        | Constraints  | Description                                 |
| -------- | ----------- | ------------ | ------------------------------------------- |
| SrNo     | INT         | PRIMARY KEY  | Sequential record number                    |
| CustID   | VARCHAR(5)  | FOREIGN KEY  | Links to the Customer table                 |
| Checkin  | DATE        | NOT NULL     | Date of arrival                             |
| Checkout | DATE        | NOT NULL     | Date of departure                           |
| RoomNo   | INT         | NOT NULL     | Room number (1–100)                         |
| Status   | VARCHAR(20) | DEFAULT 'NA' | 'not_arrived', 'checkedin', or 'checkedout' |

---

## 🧩 Project Structure

```
hotel_hms_flask/
├── app.py              # Main Flask app with routes and views
├── db_utils.py         # Database connection, CRUD, and business logic
├── requirements.txt    # Python dependencies
└── templates/          # HTML (Jinja2) templates
    ├── base.html
    ├── index.html
    ├── booking.html
    ├── records.html
    └── customer_details.html
```

---

## 📜 License

This project is released for educational and learning purposes.
You are free to modify and extend it for your own use.

---

## 👨‍💻 Author

**Hotel Management System (HMS) - Flask Web App**
Developed by Aaryav Rastogi 🧠
Built with ❤️ using **Python Flask**, **MySQL**, and **Tailwind CSS**
