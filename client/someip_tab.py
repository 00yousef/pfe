# SomeIP Tab Update
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLineEdit
)
from someip_module import SomeIPClient
from PyQt6.QtCore import pyqtSignal

class SomeIPTab(QWidget):
        
    message_received = pyqtSignal(str, str, str, str, int)  # timestamp, message_id, data, type, length
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.someip_client = SomeIPClient()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        # Filter controls
        filter_layout = QHBoxLayout()
        self.filter_id_input = QLineEdit()
        self.filter_id_input.setPlaceholderText("Filter by Message ID...")
    
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("All Types")
        self.filter_type_combo.addItem("Tx")
        self.filter_type_combo.addItem("Rx")
    
        self.filter_button = QPushButton("Apply Filter")
        self.reset_filter_button = QPushButton("Reset")
    
        filter_layout.addWidget(QLabel("Message ID:"))
        filter_layout.addWidget(self.filter_id_input)
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.filter_type_combo)
        filter_layout.addWidget(self.filter_button)
        filter_layout.addWidget(self.reset_filter_button)
    
        layout.addLayout(filter_layout)
        # Table for displaying SomeIP messages
        self.someip_table = QTableWidget()
        self.someip_table.setColumnCount(5)  # Now 5 columns including Length
        self.someip_table.setHorizontalHeaderLabels(["Timestamp", "Message ID", "Data (Hex)", "Length (Bytes)", "Type"])
        
        # Set column widths to accommodate full timestamp
        self.someip_table.setColumnWidth(0, 180)  # Timestamp column wider
        self.someip_table.setColumnWidth(1, 100)  # Message ID
        self.someip_table.setColumnWidth(2, 150)  # Data
        self.someip_table.setColumnWidth(3, 150)   # Length
        self.someip_table.setColumnWidth(4, 100)  # Type
        
        layout.addWidget(self.someip_table)
        
        # Input fields and send button
        self.someip_id_input = QLineEdit("X055")
        self.someip_id_input.setReadOnly(True)
        self.someip_data_input = QLineEdit("PredefinedSomeIPData")
        self.someip_data_input.setReadOnly(True)
        
        someip_button_layout = QHBoxLayout()
        self.someip_send_button = QPushButton("SEND")
        someip_button_layout.addWidget(self.someip_id_input)
        someip_button_layout.addWidget(self.someip_data_input)
        someip_button_layout.addWidget(self.someip_send_button)
        
        layout.addLayout(someip_button_layout)
        self.setLayout(layout)
        
        # Connect signals
        self.someip_send_button.clicked.connect(self.test_someip_message)
        self.filter_button.clicked.connect(self.apply_filter)
        self.reset_filter_button.clicked.connect(self.reset_filter)
        
    def test_someip_message(self):
        """Test sending a predefined SOMEIP message"""
        message_id = "X055"
        data = "PredefinedSomeIPData"
        data_len = len(data)
        
        # Actually send the message
        if self.someip_client.send_message(message_id, data):
            timestamp = self.database.save_message("SomeIP", message_id, data, "Tx", data_len)
            self.add_data_to_table(message_id, data, "Tx", timestamp, data_len)
        
    def send_someip_message(self, message_id, data):
        """Handle SOMEIP messages generated from CAN messages"""
        if isinstance(data, str):
            # For hex strings, calculate length in bytes
            data_len = len(bytes.fromhex(data.replace(" ", "")))
        else:
            data_len = len(data)
            
        timestamp = self.database.save_message("SomeIP", message_id, data, "Tx", data_len)
        self.add_data_to_table(message_id, data, "Tx", timestamp, data_len)
        
        # Emit signal with message details
        self.message_received.emit(timestamp, message_id, data, "SomeIP Tx", data_len)
    
    def receive_someip_message(self, message_id, data):
        """Handle received SomeIP messages"""
        if isinstance(data, str):
            # For hex strings, calculate length in bytes
            data_len = len(bytes.fromhex(data.replace(" ", "")))
        else:
            data_len = len(data)
            
        timestamp = self.database.save_message("SomeIP", message_id, data, "Rx", data_len)
        self.add_data_to_table(message_id, data, "Rx", timestamp, data_len)
        
        # Emit signal with message details
        self.message_received.emit(timestamp, message_id, data, "SomeIP Rx", data_len)
    
    def add_data_to_table(self, message_id, data, msg_type, timestamp=None, data_len=None):
        row_count = self.someip_table.rowCount()
        self.someip_table.insertRow(row_count)
        
        # If data_len is not provided, calculate it
        if data_len is None and isinstance(data, str):
            # For hex strings, each byte is represented by 2 hex characters
            data_len = len(bytes.fromhex(data.replace(" ", "")))
        elif data_len is None:
            data_len = len(data)
        
        self.someip_table.setItem(row_count, 0, QTableWidgetItem(timestamp))
        self.someip_table.setItem(row_count, 1, QTableWidgetItem(message_id))
        self.someip_table.setItem(row_count, 2, QTableWidgetItem(data))
        self.someip_table.setItem(row_count, 3, QTableWidgetItem(str(data_len)))
        self.someip_table.setItem(row_count, 4, QTableWidgetItem(msg_type))
        
    def load_saved_messages(self):
        """Load saved messages from the database"""
        messages = self.database.load_messages("SomeIP")
        for msg in messages:
            # messages format: timestamp, message_id, data, type, length
            if len(msg) >= 5:  # If database already has length field
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0], msg[4])
            else:  # For backward compatibility
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0])
    
    def apply_filter(self):
        """Apply filters to the SOMEIP message table"""
        # Clear current table
        self.someip_table.setRowCount(0)
    
        # Get filter values
        id_filter = self.filter_id_input.text()
        type_filter = self.filter_type_combo.currentText()
        if type_filter == "All Types":
            type_filter = None
    
        # Load filtered messages
        messages = self.database.load_messages_filtered("SomeIP", id_filter, type_filter)
        for msg in messages:
            # messages format: timestamp, message_id, data, type, length
            if len(msg) >= 5:  # If database already has length field
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0], msg[4])
            else:  # For backward compatibility
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0])

    def reset_filter(self):
        """Reset filters and reload all messages"""
        self.filter_id_input.clear()
        self.filter_type_combo.setCurrentIndex(0)
        self.load_saved_messages()
    
    def clear_table(self):
        self.someip_table.setRowCount(0)
