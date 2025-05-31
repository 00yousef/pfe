import sys
from PyQt6.QtWidgets import QApplication
from database import Database
from gui import SupervisionUI

def main():
    app = QApplication(sys.argv)
    
    # Initialize database
    db = Database()
    
    # Create and show main window
    window = SupervisionUI(db)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()