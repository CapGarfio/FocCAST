"""Punto de entrada principal de la aplicación desktop."""
import sys
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def launch() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
