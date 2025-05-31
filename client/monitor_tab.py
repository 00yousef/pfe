# Monitor Tab Update (without graph)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

class MonitorTab(QWidget):
    def __init__(self, database, someiptab, cantab):
        super().__init__()
        self.database = database
        self.someiptab = someiptab
        self.cantab = cantab
        self.session_only = True  # Default to showing only current session
        self.init_ui()
        
        # Connect signals from CAN and SomeIP tabs
        self.cantab.message_received.connect(self.handle_can_message)
        self.someiptab.message_received.connect(self.handle_someip_message)

    def init_ui(self):
        """Initialize the monitor tab UI"""
        main_layout = QVBoxLayout()  # Main vertical layout
         # Top control layout with buttons and options
        top_control_layout = QHBoxLayout()
        
        # Clear button
        clear_btn = QPushButton("Clear Database")
        clear_btn.clicked.connect(self.delete_database)
        top_control_layout.addWidget(clear_btn)
        
        main_layout.addLayout(top_control_layout)
        
        # Message Table
        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(5)  # Now 5 columns including Length
        self.sequence_table.setHorizontalHeaderLabels(["Timestamp", "Message ID", "Data (Hex)", "Length (Bytes)", "Type"])
        
        # Set column widths
        self.sequence_table.setColumnWidth(0, 180)  # Timestamp column wider
        self.sequence_table.setColumnWidth(1, 100)  # Message ID
        self.sequence_table.setColumnWidth(2, 150)  # Data
        self.sequence_table.setColumnWidth(3, 150)   # Length
        self.sequence_table.setColumnWidth(4, 200)  # Type
        
        main_layout.addWidget(self.sequence_table)

        self.setLayout(main_layout)

        # Initial load
        self.load_message_sequence()

    def handle_can_message(self, timestamp, message_id, data, msg_type, data_len):
        """Handle signals from CAN tab"""
        can_type = "CAN " + msg_type
        self.add_data_to_table(message_id, data, can_type, timestamp, data_len)
    
    def handle_someip_message(self, timestamp, message_id, data, msg_type, data_len):
        """Handle signals from SomeIP tab"""
        self.add_data_to_table(message_id, data, msg_type, timestamp, data_len)

    def load_message_sequence(self):
        """Load the message sequence into the table"""
        # Clear table
        self.sequence_table.setRowCount(0)
        
        # Get messages (either all or just current session)
        messages = self.database.load_message_sequence()

        for idx, (timestamp, msg_type, msg_id, data, data_len) in enumerate(messages):
            # Add data to table
            self.add_data_to_table(msg_id, data, msg_type, timestamp, data_len)

    def add_data_to_table(self, message_id, data, msg_type, timestamp=None, data_len=None):
        """Add a row to the table"""
        row_count = self.sequence_table.rowCount()
        self.sequence_table.insertRow(row_count)
        
        # If data_len is not provided, calculate it
        if data_len is None and isinstance(data, str):
            # For hex strings, calculate length in bytes
            try:
                data_len = len(bytes.fromhex(data.replace(" ", "")))
            except ValueError:
                data_len = len(data)
        elif data_len is None:
            data_len = len(data)
        
        self.sequence_table.setItem(row_count, 0, QTableWidgetItem(str(timestamp)))
        self.sequence_table.setItem(row_count, 1, QTableWidgetItem(str(message_id)))
        self.sequence_table.setItem(row_count, 2, QTableWidgetItem(str(data)))
        self.sequence_table.setItem(row_count, 3, QTableWidgetItem(str(data_len)))
        self.sequence_table.setItem(row_count, 4, QTableWidgetItem(str(msg_type)))
        
        # Scroll to the new row
        self.sequence_table.scrollToItem(self.sequence_table.item(row_count, 0))


        
    def refresh(self):
        """Refresh the table when needed"""
        self.load_message_sequence()
        
    def delete_database(self):
        """Clear database"""
        self.database.clear_database()
        self.cantab.clear_table()
        self.someiptab.clear_table()
        self.refresh()
