# Graph Tab Implementation
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox,
    QComboBox, QToolTip
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import datetime
import time
from pyqtgraph import ScatterPlotItem
from PyQt5 import QtWidgets
from pyqtgraph.graphicsItems.DateAxisItem import DateAxisItem


class HoverScatter(ScatterPlotItem):
    def hoverEvent(self, ev):
        # always call the base implementation to handle highlighting, etc.
        super().hoverEvent(ev)

        if ev.isExit():
            QToolTip.hideText()
        else:
            # find which spots are under the mouse
            spots = self.pointsAt(ev.pos())
            if spots:
                # show the first spot's data in a tooltip
                data = spots[0].data()
                QToolTip.showText(ev.screenPos().toPoint(), str(data))
class GraphTab(QWidget):
    def __init__(self, database, someiptab, cantab,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = database
        self.someiptab = someiptab
        self.cantab = cantab
        
        # Data structures to store messages for the current session
        self.message_sequence = []  # List of (timestamp, type, message_id, data, length)
        self.message_counter = 0    # Counter for X-axis sequencing
        
        self.init_ui()
        
        # Connect signals from CAN and SomeIP tabs
        self.cantab.message_received.connect(self.handle_can_message)
        self.someiptab.message_received.connect(self.handle_someip_message)

    def init_ui(self):
        """Initialize the graph tab UI"""
        main_layout = QVBoxLayout()
        
        # Controls for the graph
        controls_layout = QHBoxLayout()
        
        
        # Clear button
        clear_btn = QPushButton("Clear Graph")
        clear_btn.clicked.connect(self.clear_graph)
        controls_layout.addWidget(clear_btn)
        
        
        main_layout.addLayout(controls_layout)
        
        # Create the graph
        axis = DateAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(title="Temperature and Fan Speed", axisItems={'bottom': axis})
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Timestamp')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        self.plot_widget.setYRange(0,150)
        self.plot_widget.enableAutoRange(axis='y',enable=False)
        self.plot_widget.enableAutoRange(axis='x',enable=False)
        self.plot_widget.getViewBox().setMouseEnabled(x=True,y=False)
        self.plot_widget.addLegend()
        
        main_layout.addWidget(self.plot_widget)
        self.setLayout(main_layout)

    def handle_can_message(self, timestamp, message_id, data, msg_type, data_len):
        """Handle signals from CAN tab"""

        # Convert timestamp string to float (Unix time)
        if isinstance(timestamp, str):
            try:
                dt = datetime.datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
                timestamp = dt.timestamp()
            except ValueError:
                print("Invalid CAN timestamp format:", timestamp)
                return

        # Convert hex data to int
        if isinstance(data, str):
            try:
                data = int(data, 16)
            except ValueError:
                data = 0

        can_type = "CAN " + msg_type
        self.message_counter += 1
        self.message_sequence.append((timestamp, can_type, message_id, data, data_len))

        if self.isVisible():
            self.refresh()




    def handle_someip_message(self, timestamp, message_id, data, msg_type, data_len):
        """Handle signals from SomeIP tab"""
        # Convert timestamp string to float (Unix time)
        if isinstance(timestamp, str):
            try:
                dt = datetime.datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")  # Match your timestamp format
                timestamp = dt.timestamp()  # Convert to float seconds
            except ValueError:
                print("Invalid timestamp format:", timestamp)
                return

        # Convert data to int if needed
        if isinstance(data, str):
            try:
                data = int(data)
            except ValueError:
                data = 0

        self.message_counter += 1
        self.message_sequence.append((timestamp, msg_type, message_id, data, data_len))

        if self.isVisible():
            self.refresh()

    def refresh(self):
        """Refresh the graph with current data"""
        self.plot_widget.clear()
        self.plot_widget.setYRange(0,150)
        self.plot_widget.enableAutoRange(axis='y',enable=False)
        messages = self.message_sequence

        
        # Prepare data for plotting
        can_rx_x = []
        can_rx_y = []
        someip_rx_x = []
        someip_rx_y = []
        
        for idx, (timestamp, msg_type, msg_id, data, data_len) in enumerate(messages):
            if msg_type == "CAN Rx":
                can_rx_x.append(timestamp)
                can_rx_y.append(data)
            elif msg_type == "SomeIP Rx":
                someip_rx_x.append(timestamp)
                someip_rx_y.append(data)

        
        # Plot the data with different colors and symbols
        if can_rx_x:
            self.plot_widget.plot(can_rx_x, can_rx_y, pen='b', symbol='o', symbolPen='b', 
                                 symbolBrush='b', name="Temperature")
        if someip_rx_x:
            # Add a standard plot item for the legend first
            self.plot_widget.plot(someip_rx_x, someip_rx_y, pen='g', symbol='s', symbolPen='g',
                                 symbolBrush='g', name="Fan Speed")
            
            # Then add the hover scatter for interactive functionality
            spots = [
                {'pos': (x, y), 'data': y, 'brush': 'g'}
                for x, y in zip(someip_rx_x, someip_rx_y)
            ]
            scatter = HoverScatter(spots=spots, symbol='s', size=10)
            self.plot_widget.addItem(scatter)

    def clear_graph(self):
        """Clear all data points from the graph"""
        self.message_sequence = []
        self.message_counter = 0
        self.plot_widget.clear()
