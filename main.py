import sys
from setup_dialog import InitialSetupDialog
from terminal_app import ModernDarkTerminalApp
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernDarkTerminalApp()
    window.show()
    sys.exit(app.exec())