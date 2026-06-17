from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel
from qgis.PyQt.QtCore import pyqtSignal


class ConnectionsPage(QWidget):
    """
    Handles GeoServer connection management.
    """
    connections_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Connections Page — Coming soon"))