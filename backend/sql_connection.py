import mysql.connector
from mysql.connector import Error

_connection = None 

def get_sql_connection():
    global _connection
    if _connection is None or not _connection.is_connected():
        try:
            print("Attempting to connect to MySQL...")
            _connection = mysql.connector.connect(
                host='localhost',  
                database='grocery_store', 
                user='root',  
                password='123456'  
            )
            if _connection.is_connected():
                print(" Connected to MySQL database")
        except Error as e:
            print(f" Error while connecting to MySQL: {e}")
            raise
    return _connection

if __name__ == '__main__':
    try:
        conn = get_sql_connection()
        if conn:
            print(" Connected to MySQL successfully!")
        else:
            print(" Connection failed!")
    except Exception as e:
        print(f"Connection error: {e}")
