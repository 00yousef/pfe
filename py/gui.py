from PyQt6.QtWidgets import QMainWindow, QTabWidget
from can_module import CANListener
from someip_module import SomeIPListener
from can_tab import CANTab
from someip_tab import SomeIPTab
from monitor_tab import MonitorTab 
from graph_tab import GraphTab  # Import the new GraphTab

class SupervisionUI(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.database = database
        
        # Setup UI
        self.setWindowTitle("Automotive HMI")
        self.setGeometry(100, 100, 600, 400)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Initialize tabs
        self.can_tab = CANTab(self.database)
        self.tabs.addTab(self.can_tab, "CAN")
    
        self.someip_tab = SomeIPTab(self.database)
        self.tabs.addTab(self.someip_tab, "SomeIP")
        
        self.monitor_tab = MonitorTab(self.database, self.someip_tab, self.can_tab)
        self.tabs.addTab(self.monitor_tab, "Monitoring")
        
        # Add the new Graph tab
        self.graph_tab = GraphTab(self.database, self.someip_tab, self.can_tab)
        self.tabs.addTab(self.graph_tab, "Graph")
        
        # Load saved messages from database
        self.can_tab.load_saved_messages()
        self.someip_tab.load_saved_messages()
        
        # Start CAN listener
        self.can_listener = CANListener()
        self.can_listener.new_can_message.connect(self.can_tab.receive_can_message)
        self.can_listener.new_someip_message.connect(self.someip_tab.send_someip_message)
        self.can_listener.start()
        
        # Start SomeIP listener
        self.someip_listener = SomeIPListener()
        self.someip_listener.new_someip_message.connect(self.someip_tab.receive_someip_message)
        self.someip_listener.new_can_message.connect(self.can_tab.receive_can_message)
        self.someip_listener.start()
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Connect signals to refresh graph when new messages arrive
        self.can_listener.new_can_message.connect(self.refresh_graph_if_visible)
        self.someip_listener.new_someip_message.connect(self.refresh_graph_if_visible)
    
    def refresh_monitor_if_visible(self, *args):
        """Refresh monitor tab if it's currently visible"""
        if self.tabs.currentWidget() == self.monitor_tab:
            self.monitor_tab.refresh()
    
    def refresh_graph_if_visible(self, *args):
        """Refresh graph tab if it's currently visible"""
        if self.tabs.currentWidget() == self.graph_tab:
            self.graph_tab.refresh()
    
    def on_tab_changed(self, index):
        """Handle tab change events"""
        current_tab = self.tabs.widget(index)
        if current_tab == self.monitor_tab:
            print("Refreshing Monitor tab...")
            self.monitor_tab.refresh()
        elif current_tab == self.graph_tab:
            print("Refreshing Graph tab...")
            self.graph_tab.refresh()
            
    def closeEvent(self, event):
        """Handle window close event"""
        self.can_listener.stop()
        self.someip_listener.stop()  # Stop the SomeIP listener
        self.database.close()
        event.accept()
