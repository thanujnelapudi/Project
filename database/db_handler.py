import oracledb
import sqlite3
import sys
import os
from werkzeug.security import generate_password_hash, check_password_hash

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, DATABASE_TYPE, DB_PATH

try:
    oracledb.init_oracle_client(lib_dir=r"C:\oraclexe\app\oracle\product\11.2.0\server\bin")
except Exception as e:
    print(f"[DB] Oracle Client init warning: {e}")
    print("[DB] Proceeding with thin mode if possible, or expect connection errors later.")

def get_connection():
    if DATABASE_TYPE == "sqlite":
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row  # Makes it accessible by column name
            return conn
        except Exception as e:
            print(f"SQLite connection error: {e}")
            return None
    else:
        try:
            connection = oracledb.connect(
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                dsn=DB_CONFIG["dsn"]
            )
            return connection
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

def create_table():
    connection = get_connection()
    if connection is None: return
    cursor = connection.cursor()
    try:
        if DATABASE_TYPE == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS postal_forms (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT,
                    address         TEXT,
                    phone           TEXT,
                    pincode         TEXT,
                    remarks         TEXT,
                    operator        TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # Oracle implementation
            try:
                cursor.execute("""
                    CREATE TABLE postal_forms (
                        id              NUMBER PRIMARY KEY,
                        name            VARCHAR2(200),
                        address         VARCHAR2(500),
                        phone           VARCHAR2(20),
                        pincode         VARCHAR2(10),
                        remarks         VARCHAR2(500),
                        operator        VARCHAR2(100),
                        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE SEQUENCE postal_forms_seq START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE")
                cursor.execute("""
                    CREATE OR REPLACE TRIGGER postal_forms_trigger
                    BEFORE INSERT ON postal_forms
                    FOR EACH ROW
                    BEGIN
                        SELECT postal_forms_seq.NEXTVAL INTO :NEW.id FROM DUAL;
                    END;
                """)
            except oracledb.DatabaseError as e:
                error, = e.args
                if "ORA-00955" not in str(error): print(f"Error creating table: {e}")
        connection.commit()
    except Exception as e:
        print(f"Error initializing postal_forms: {e}")
    finally:
        cursor.close()
        connection.close()

def save_form(data):
    connection = get_connection()
    if connection is None:
        return False
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO postal_forms 
                (name, address, phone, pincode, remarks, operator)
            VALUES 
                (:name, :address, :phone, :pincode, :remarks, :operator)
        """, {
            "name":           data.get("name", ""),
            "address":        data.get("address", ""),
            "phone":          data.get("phone", ""),
            "pincode":        data.get("pincode", ""),
            "remarks":        data.get("remarks", ""),
            "operator":       data.get("operator", "operator1")
        })
        connection.commit()
        return True
    except Exception as e:
        print(f"Error saving form: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def get_all_forms():
    connection = get_connection()
    if connection is None:
        return []
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, name, address, phone, pincode, remarks, operator, created_at
            FROM postal_forms
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        forms = []
        for row in rows:
            forms.append({
                "id":             row[0],
                "name":           row[1],
                "address":        row[2],
                "phone":          row[3],
                "pincode":        row[4],
                "remarks":        row[5],
                "operator":       row[6],
                "created_at":     str(row[7])
            })
        return forms
    except Exception as e:
        print(f"Error retrieving forms: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def create_user_table():
    connection = get_connection()
    if connection is None: return
    cursor = connection.cursor()
    try:
        if DATABASE_TYPE == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    full_name TEXT,
                    department TEXT,
                    role TEXT,
                    id_number TEXT,
                    status TEXT DEFAULT 'PENDING',
                    is_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            try:
                cursor.execute("""
                    CREATE TABLE app_users (
                        id NUMBER PRIMARY KEY,
                        username VARCHAR2(100) UNIQUE,
                        password_hash VARCHAR2(255),
                        full_name VARCHAR2(200),
                        department VARCHAR2(100),
                        role VARCHAR2(100),
                        id_number VARCHAR2(50),
                        status VARCHAR2(20) DEFAULT 'PENDING',
                        is_admin NUMBER(1) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE SEQUENCE app_users_seq START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE")
                cursor.execute("""
                    CREATE OR REPLACE TRIGGER app_users_trigger
                    BEFORE INSERT ON app_users
                    FOR EACH ROW
                    BEGIN
                        SELECT app_users_seq.NEXTVAL INTO :NEW.id FROM DUAL;
                    END;
                """)
            except oracledb.DatabaseError as e:
                error, = e.args
                if "ORA-00955" not in str(error): print(f"Error creating user table: {e}")
        connection.commit()
    except Exception as e:
        print(f"Error initializing app_users: {e}")
    finally:
        cursor.close()
        connection.close()

    create_user("admin", "password123", "System Administrator", "IT", "Admin", "001", is_admin=1, status='APPROVED')
    create_user("Thanuj", "pass-1234", "Thanuj", "Management", "Admin", "999", is_admin=1, status='APPROVED')

def create_activity_table():
    connection = get_connection()
    if connection is None: return
    cursor = connection.cursor()
    try:
        if DATABASE_TYPE == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    activity_type TEXT,
                    description TEXT,
                    ip_address TEXT,
                    device_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            try:
                cursor.execute("""
                    CREATE TABLE app_activity_logs (
                        id NUMBER PRIMARY KEY,
                        username VARCHAR2(100),
                        activity_type VARCHAR2(50),
                        description VARCHAR2(500),
                        ip_address VARCHAR2(50),
                        device_info VARCHAR2(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE SEQUENCE app_activity_seq START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE")
                cursor.execute("""
                    CREATE OR REPLACE TRIGGER app_activity_trigger
                    BEFORE INSERT ON app_activity_logs
                    FOR EACH ROW
                    BEGIN
                        SELECT app_activity_seq.NEXTVAL INTO :NEW.id FROM DUAL;
                    END;
                """)
            except oracledb.DatabaseError as e:
                error, = e.args
                if "ORA-00955" not in str(error): print(f"Error creating activity table: {e}")
        connection.commit()
    except Exception as e:
        print(f"Error initializing app_activity_logs: {e}")
    finally:
        cursor.close()
        connection.close()

def log_activity(username, activity_type, description, ip_address=None, device_info=None):
    connection = get_connection()
    if connection is None: return
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO app_activity_logs (username, activity_type, description, ip_address, device_info)
            VALUES (:username, :activity_type, :description, :ip_address, :device_info)
        """, {
            "username": username,
            "activity_type": activity_type,
            "description": description,
            "ip_address": ip_address,
            "device_info": device_info
        })
        connection.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
    finally:
        cursor.close()
        connection.close()

def get_activity_logs(limit=50):
    connection = get_connection()
    if connection is None: return []
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, username, activity_type, description, ip_address, device_info, created_at
            FROM app_activity_logs
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchmany(limit)
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "username": row[1],
                "type": row[2],
                "description": row[3],
                "ip": row[4],
                "device": row[5],
                "time": str(row[6])
            })
        return logs
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def create_user(username, password, full_name=None, department=None, role=None, id_number=None, is_admin=0, status='PENDING'):
    connection = get_connection()
    if connection is None:
        return False
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM app_users WHERE username = :username", {"username": username})
        if cursor.fetchone()[0] > 0:
            # If admin exists, update their fields just in case
            if username == "admin":
                hashed_pw = generate_password_hash(password)
                cursor.execute("""
                    UPDATE app_users 
                    SET full_name=:fn, department=:dept, role=:role, id_number=:idn, is_admin=:adm, status=:st, password_hash=:pw
                    WHERE username=:u
                """, {"fn": full_name, "dept": department, "role": role, "idn": id_number, "adm": is_admin, "st": status, "pw": hashed_pw, "u": username})
                connection.commit()
                return True
            return False  # username already exists
            
        hashed_pw = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO app_users (username, password_hash, full_name, department, role, id_number, is_admin, status)
            VALUES (:username, :password_hash, :full_name, :department, :role, :id_number, :is_admin, :status)
        """, {
            "username": username, 
            "password_hash": hashed_pw,
            "full_name": full_name,
            "department": department,
            "role": role,
            "id_number": id_number,
            "is_admin": is_admin,
            "status": status
        })
        connection.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def verify_user(username, password):
    connection = get_connection()
    if connection is None:
        return False, None
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT password_hash, status, is_admin FROM app_users WHERE username = :username", {"username": username})
        row = cursor.fetchone()
        if row:
            if check_password_hash(row[0], password):
                return True, {"status": row[1], "is_admin": row[2]}
        return False, None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False, None
    finally:
        cursor.close()
        connection.close()

def get_pending_users():
    connection = get_connection()
    if connection is None: return []
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT username, full_name, department, role, id_number, created_at 
            FROM app_users WHERE status = 'PENDING' ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        return [{"username": r[0], "full_name": r[1], "department": r[2], "role": r[3], "id_number": r[4], "created_at": str(r[5])} for r in rows]
    except Exception as e:
        print(f"Error fetching pending users: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def update_user_status(username, status):
    connection = get_connection()
    if connection is None: return False
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE app_users SET status = :s WHERE username = :u", {"s": status, "u": username})
        connection.commit()
        return True
    except Exception as e:
        print(f"Error updating user status: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_all_users():
    """Returns list of all user details in app_users."""
    connection = get_connection()
    if connection is None:
        return []
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT username, full_name, department, role, id_number, status, is_admin FROM app_users ORDER BY username")
        rows = cursor.fetchall()
        return [{"username": r[0], "full_name": r[1], "department": r[2], "role": r[3], "id_number": r[4], "status": r[5], "is_admin": r[6]} for r in rows]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def delete_user(username):
    """Deletes a user by username. Returns (True, None) or (False, error_message)."""
    connection = get_connection()
    if connection is None:
        return False, "Database connection failed"
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM app_users WHERE username = :username", {"username": username})
        connection.commit()
        return True, None
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False, str(e)
    finally:
        cursor.close()
        connection.close()


def change_password(username, old_password, new_password):
    """Verifies old password then updates to new_password hash.
    Returns (True, None) or (False, error_message)."""
    auth_ok, info = verify_user(username, old_password)
    if not auth_ok:
        return False, "Current password is incorrect"
    connection = get_connection()
    if connection is None:
        return False, "Database connection failed"
    cursor = connection.cursor()
    try:
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE app_users SET password_hash = :h WHERE username = :u",
            {"h": new_hash, "u": username}
        )
        connection.commit()
        return True, None
    except Exception as e:
        print(f"Error changing password: {e}")
        return False, str(e)
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    print("Initializing Database...")
    create_table()
    create_user_table()
    create_activity_table()
    print("Database initialization complete.")