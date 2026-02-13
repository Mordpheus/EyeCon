"""
EyeCon - Main application file

Starts the application with a main window and layout.
Gracefully handles missing hardware (camera, COM port).
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from app_layout import AppLayout 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)

        # === Global stylesheet for all QPushButtons ===
        # Unified design for all buttons throughout the project
        btn_style = """
        QPushButton {
            background-color: #e7ecf8;
            color: #1f2d4d;
            border: 1px solid #c4d1f2;
            border-radius: 6px;
            padding: 8px 12px;
        }
        QPushButton:hover {
            background-color: #d2ddf6;
        }
        QPushButton:pressed {
            background-color: #c0cff1;
        }
        """
        app.setStyleSheet(btn_style)

        # === Create main window ===
        win = QMainWindow()
        win.setWindowTitle("Layout Prototype")
        win.resize(1200, 800)
        
        # Try to load app layout (will handle missing hardware gracefully)
        try:
            app_layout = AppLayout()
            win.setCentralWidget(app_layout)
        except Exception as e:
            logger.error(f"Error initializing app layout: {e}")
            # Show error but continue running (UI still functional)
            win.setCentralWidget(AppLayout())
        
        win.show()

        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Fatal error starting application: {e}")
        import traceback
        traceback.print_exc()
        
        # Show error dialog
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "Application Error",
            f"Failed to start EyeCon:\n\n{str(e)}\n\n"
            "The application will continue with limited functionality.\n"
            "Check logs for hardware connection details."
        )
        
        sys.exit(1)

