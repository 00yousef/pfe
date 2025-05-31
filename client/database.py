import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="messages.db"):
        self.db_name = db_name
        self.conn = self.init_db()
        #self.clear_database()
        

    def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS CAN
                        (timestamp TEXT, message_id TEXT, data TEXT, type TEXT, length INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS SomeIP
                        (timestamp TEXT, message_id TEXT, data TEXT, type TEXT, length INTEGER)''')
        conn.commit()
        return conn

    def save_message(self, table, message_id, data, msg_type, length=None):
        """Save a message to the database"""
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
        # Calculate length if not provided
        if length is None and isinstance(data, str):
            try:
                length = len(bytes.fromhex(data.replace(" ", "")))
            except ValueError:
                length = len(data)
        elif length is None:
            length = len(data)
    
        cursor = self.conn.cursor()
        cursor.execute(f"INSERT INTO {table} (timestamp, message_id, data, type, length) VALUES (?, ?, ?, ?, ?)", 
                    (timestamp, message_id, data, msg_type, length))
        self.conn.commit()
        return timestamp

    def load_messages(self, table):
        """Load all messages from a specific table"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT timestamp, message_id, data, type, length FROM {table}")
        return cursor.fetchall()

    def load_messages_filtered(self, table, message_id=None, msg_type=None):
        """Load messages from a specific table with optional filters"""
        cursor = self.conn.cursor()

        # Start with base query
        query = f"SELECT timestamp, message_id, data, type, length FROM {table}"
        params = []

        # Add filters if provided
        conditions = []
        if message_id:
            conditions.append("message_id LIKE ?")
            params.append(f"%{message_id}%")
        if msg_type:
            conditions.append("type = ?")
            params.append(msg_type)

        # Add WHERE clause if we have conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Execute query
        cursor.execute(query, params)
        return cursor.fetchall()

    def load_message_sequence(self):
        """Load messages in chronological order from CAN and SomeIP tables"""
        cursor = self.conn.cursor()

        sql = """
        SELECT timestamp, 'CAN Rx' AS type, message_id, data, length FROM CAN WHERE type = 'Rx'
        UNION ALL
        SELECT timestamp, 'SomeIP Tx' AS type, message_id, data, length FROM SomeIP WHERE type = 'Tx'
        UNION ALL
        SELECT timestamp, 'SomeIP Rx' AS type, message_id, data, length FROM SomeIP WHERE type = 'Rx'
        UNION ALL
        SELECT timestamp, 'CAN Tx' AS type, message_id, data, length FROM CAN WHERE type = 'Tx'
        ORDER BY timestamp ASC;
        """
    
        cursor.execute(sql)
        messages = cursor.fetchall()
        return messages
    
    def clear_database(self):
        """Clears all records from the CAN and SomeIP tables"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM CAN;")
        cursor.execute("DELETE FROM SomeIP;")
        self.conn.commit()

    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()