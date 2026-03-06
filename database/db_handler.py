import oracledb
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

oracledb.init_oracle_client(lib_dir=r"C:\oraclexe\app\oracle\product\11.2.0\server\bin")

def get_connection():
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
    if connection is None:
        print("Could not connect to database.")
        return
    cursor = connection.cursor()
    try:
        cursor.execute("""
            CREATE TABLE postal_forms (
                id          NUMBER PRIMARY KEY,
                name        VARCHAR2(200),
                address     VARCHAR2(500),
                phone       VARCHAR2(20),
                pincode     VARCHAR2(10),
                remarks     VARCHAR2(500),
                operator    VARCHAR2(100),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("Table created successfully.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if "ORA-00955" in str(error):
            print("Table already exists. Skipping creation.")
        else:
            print(f"Error creating table: {e}")

    try:
        cursor.execute("""
            CREATE SEQUENCE postal_forms_seq
            START WITH 1
            INCREMENT BY 1
            NOCACHE
            NOCYCLE
        """)
        connection.commit()
        print("Sequence created successfully.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if "ORA-00955" in str(error):
            print("Sequence already exists. Skipping creation.")
        else:
            print(f"Error creating sequence: {e}")

    try:
        cursor.execute("""
            CREATE OR REPLACE TRIGGER postal_forms_trigger
            BEFORE INSERT ON postal_forms
            FOR EACH ROW
            BEGIN
                SELECT postal_forms_seq.NEXTVAL INTO :NEW.id FROM DUAL;
            END;
        """)
        connection.commit()
        print("Trigger created successfully.")
    except Exception as e:
        print(f"Error creating trigger: {e}")
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
            "name":     data.get("name", ""),
            "address":  data.get("address", ""),
            "phone":    data.get("phone", ""),
            "pincode":  data.get("pincode", ""),
            "remarks":  data.get("remarks", ""),
            "operator": data.get("operator", "operator1")
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
                "id":         row[0],
                "name":       row[1],
                "address":    row[2],
                "phone":      row[3],
                "pincode":    row[4],
                "remarks":    row[5],
                "operator":   row[6],
                "created_at": str(row[7])
            })
        return forms
    except Exception as e:
        print(f"Error retrieving forms: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Creating database table...")
    create_table()