from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
import sys
from pathlib import Path
from GUI.kimdosi_ui import KimdosiUI


def check_required_tools():
    """Check if 7-Zip is available in the Tools directory"""
    root_dir = Path(__file__).parent.parent
    seven_zip_path = root_dir / "Tools" / "7z" / "7z.exe"
    
    if not seven_zip_path.exists():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Required Tool Missing")
        msg.setText("7-Zip not found in the Tools directory.")
        msg.setInformativeText("Please ensure 7-Zip is installed in Tools/7z/7z.exe")
        msg.exec()
        return False
    return True


def check_required_directories():
    """Check if required directories exist and create them if user approves"""
    required_dirs = [
        "Analysis",
        "Tools"
    ]
    
    # Get the root directory (one level up from Source)
    root_dir = Path(__file__).parent.parent
    missing_dirs = []
    
    # Check which directories are missing
    for dir_name in required_dirs:
        if not (root_dir / dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        # Create message box to ask user about creating directories
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Required Directories Missing")
        msg.setText("The following required directories are missing:\n" + "\n".join(missing_dirs))
        msg.setInformativeText("Would you like Kimdosi to create these directories?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Create the missing directories
            for dir_name in missing_dirs:
                (root_dir / dir_name).mkdir(exist_ok=True)
            return True
        else:
            return False
    return True


def main():
    # Create application instance
    app = QApplication(sys.argv)
    
    # Set up application icon
    icon_path = Path(__file__).parent / "Images" / "kimdosi_icon.ico"
    if not icon_path.exists():
        print(f"Warning: Icon not found at {icon_path}")
        icon_path = Path(__file__).parent / "Images" / "Kimdosi_icon.png"  # Try PNG as fallback
        if not icon_path.exists():
            print(f"Warning: Fallback icon not found at {icon_path}")
    
    # Set icon in multiple ways to ensure it shows up
    icon = QIcon(str(icon_path))
    app.setWindowIcon(icon)
    QApplication.setWindowIcon(icon)
      # Check required directories and tools before showing the main window
    if not check_required_directories():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Directory Setup Required")
        msg.setText("Please create the required directories manually before running Kimdosi.")
        msg.exec()
        return 1
        
    if not check_required_tools():
        return 1
    
    # Create and show main window
    window = KimdosiUI()
    window.show()
    
    # Start event loop and handle exit
    return_code = app.exec()
    
    # Ensure cleanup is performed (window's closeEvent will be called)
    window.close()
    
    sys.exit(return_code)


if __name__ == "__main__":
    # Add the parent directory to sys.path to allow imports to work when run directly
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    main()