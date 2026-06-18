from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QMessageBox,
    QLabel, QSizePolicy, QFrame
)
from qgis.PyQt.QtCore import pyqtSignal

from core.connection_manager import ConnectionManager
from .connection_dialog import ConnectionDialog


class ConnectionsPage(QWidget):
    """
    Handles GeoServer connection management.
    """
    connections_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.manager = ConnectionManager()
        self._setup_ui()
        self._setup_connections()
        self._load_connections()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Title ────────────────────────────────────────
        title = QLabel("Connections")
        title.setProperty("role", "title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Manage your saved GeoServer connections. "
            "Select a connection in the header to work with it."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ── Card container ──────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # List of connections
        self.lst_connections = QListWidget()
        self.lst_connections.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        card_layout.addWidget(self.lst_connections)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_add = QPushButton("＋  Add")
        self.btn_edit = QPushButton("✎  Edit")
        self.btn_delete = QPushButton("🗑  Delete")
        self.btn_delete.setProperty("danger", "true")

        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()

        card_layout.addLayout(btn_row)

        layout.addWidget(card)

    def _setup_connections(self):
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.lst_connections.currentRowChanged.connect(self._on_selection_changed)

    def _load_connections(self):
        """Load all saved connections into the list."""
        self.lst_connections.clear()
        connections = self.manager.get_all_connections()
        for name in connections:
            self.lst_connections.addItem(name)

    def _on_selection_changed(self, index):
        """Enable/disable buttons based on selection."""
        has_selection = index >= 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _on_add(self):
        """Open dialog to add a new connection."""
        dialog = ConnectionDialog(parent=self)
        if dialog.exec_():
            self._load_connections()
            self.connections_changed.emit()

    def _on_edit(self):
        """Open dialog to edit the selected connection."""
        name = self.lst_connections.currentItem().text()
        connection = self.manager.load_connection(name)
        dialog = ConnectionDialog(connection=connection, parent=self)
        if dialog.exec_():
            self._load_connections()
            self.connections_changed.emit()

    def _on_delete(self):
        """Delete the selected connection after confirmation."""
        name = self.lst_connections.currentItem().text()
        reply = QMessageBox.question(
            self,
            "Delete Connection",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.manager.delete_connection(name)
            self._load_connections()
            self.connections_changed.emit()
