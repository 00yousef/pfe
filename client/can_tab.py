# CAN Tab Update
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLineEdit
)
from can_module import send_can_message
from PyQt6.QtCore import pyqtSignal
class CANTab(QWidget):
    message_received = pyqtSignal(str, str, str, str, int)  # timestamp, message_id, data, type, length
    def __init__(self, database):
        super().__init__()
        self.database = database
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
        # Table for displaying CAN messages
        self.can_table = QTableWidget()
        self.can_table.setColumnCount(5)  # Now 5 columns including Length
        self.can_table.setHorizontalHeaderLabels(["Timestamp", "Message ID", "Data (Hex)", "Length (Bytes)", "Type"])
        
        # Set column widths to accommodate full timestamp
        self.can_table.setColumnWidth(0, 180)  # Timestamp column wider
        self.can_table.setColumnWidth(1, 100)  # Message ID
        self.can_table.setColumnWidth(2, 150)  # Data
        self.can_table.setColumnWidth(3, 150)   # Length
        self.can_table.setColumnWidth(4, 100)  # Type
        
        layout.addWidget(self.can_table)
        
        # Input fields and send button
        self.can_id_input = QLineEdit("X054")
        self.can_id_input.setReadOnly(True)
        self.can_data_input = QLineEdit("PredefinedData")
        self.can_data_input.setReadOnly(True)
        
        can_button_layout = QHBoxLayout()
        self.can_send_button = QPushButton("SEND")
        can_button_layout.addWidget(self.can_id_input)
        can_button_layout.addWidget(self.can_data_input)
        can_button_layout.addWidget(self.can_send_button)
        
        layout.addLayout(can_button_layout)
        self.setLayout(layout)
        
        # Connect signals
        self.can_send_button.clicked.connect(self.send_can_message)
        self.filter_button.clicked.connect(self.apply_filter)
        self.reset_filter_button.clicked.connect(self.reset_filter)
        
    def send_can_message(self):
        message_id = 0x054
        data = bytes.fromhex("DE AD BE EF")
        data_len = len(data)
        
        if send_can_message(message_id, data):
            timestamp = self.database.save_message("CAN", hex(message_id), data.hex(), "Tx", data_len)
            self.add_data_to_table(hex(message_id), data.hex(), "Tx", timestamp, data_len)
            print(f"Sent CAN: {hex(message_id)} {data.hex()} Length: {data_len}")
        
    def add_data_to_table(self, message_id, data, msg_type, timestamp=None, data_len=None):
        row_count = self.can_table.rowCount()
        self.can_table.insertRow(row_count)
        
        # If data_len is not provided, calculate it
        if data_len is None and isinstance(data, str):
            # For hex strings, each byte is represented by 2 hex characters
            data_len = len(bytes.fromhex(data.replace(" ", "")))
        elif data_len is None:
            data_len = len(data)
        
        self.can_table.setItem(row_count, 0, QTableWidgetItem(timestamp))
        self.can_table.setItem(row_count, 1, QTableWidgetItem(message_id))
        self.can_table.setItem(row_count, 2, QTableWidgetItem(data))
        self.can_table.setItem(row_count, 3, QTableWidgetItem(str(data_len)))
        self.can_table.setItem(row_count, 4, QTableWidgetItem(msg_type))
        
    def apply_filter(self):
        """Apply filters to the CAN message table"""
        # Clear current table
        self.can_table.setRowCount(0)
    
        # Get filter values
        id_filter = self.filter_id_input.text()
        type_filter = self.filter_type_combo.currentText()
        if type_filter == "All Types":
            type_filter = None
    
        # Load filtered messages
        messages = self.database.load_messages_filtered("CAN", id_filter, type_filter)
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

    def load_saved_messages(self):
        """Load saved messages from the database"""
        # Clear current table
        self.can_table.setRowCount(0)
        messages = self.database.load_messages("CAN")
        for msg in messages:
            # messages format: timestamp, message_id, data, type, length
            if len(msg) >= 5:  # If database already has length field
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0], msg[4])
            else:  # For backward compatibility
                self.add_data_to_table(msg[1], msg[2], msg[3], msg[0])
            
    def receive_can_message(self, message_id, data, msg_type="Rx"):
        """Handle CAN messages"""
        if isinstance(data, str):
            # For hex strings, calculate length in bytes
            data_len = len(bytes.fromhex(data.replace(" ", "")))
        else:
            data_len = len(data)
            
        timestamp = self.database.save_message("CAN", message_id, data, msg_type, data_len)
        self.add_data_to_table(message_id, data, msg_type, timestamp, data_len)
        
        # Emit signal with message details
        self.message_received.emit(timestamp, message_id, data, msg_type, str(data_len))
    
    def clear_table(self):
        self.can_table.setRowCount(0)
