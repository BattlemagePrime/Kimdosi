from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from GUI.kimdosi_ui import KimdosiUI
import sys


def main():
    # Create application instance
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("Source/Images/kimdosi_icon.ico"))
    
    # Create and show main window
    window = KimdosiUI()
    window.show()
    
    # Start event loop and handle exit
    return_code = app.exec()
    
    # Ensure cleanup is performed (window's closeEvent will be called)
    window.close()
    
    sys.exit(return_code)


if __name__ == "__main__":
    main()