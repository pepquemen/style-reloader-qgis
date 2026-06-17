from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QHBoxLayout,
    QVBoxLayout, QListWidget, QStackedWidget,
    QComboBox, QLabel, QFrame, QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

from core.connection_manager import ConnectionManager
from core.geoserver_api import GeoServerAPI
from gui.reload_page import ReloadPage
from gui.connections_page import ConnectionsPage
from gui.styles_page import StylesPage
from gui.about_page import AboutPage


class MainPanel(QDockWidget):
    """
    Main plugin panel.
    Contains the global header (connection + workspace),
    the sidebar navigation and the stacked pages.
    """

    def __init__(self, iface):
        super().__init__("Style Reloader for GeoServer")
        self.iface = iface
        self.api = None
        self.manager = ConnectionManager()

        self._setup_ui()
        self._setup_connections()
        self._load_connections()

    def _setup_ui(self):
        """Build the main panel UI programmatically."""

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(120)
        self.sidebar.addItems(["Connexions", "Estils", "Publicació", "About"])
        self.sidebar.setCurrentRow(2)

        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #00A8D6;
                border: none;
                color: white;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 16px 8px;
                text-align: center;
            }
            QListWidget::item:selected {
                background-color: #0088B0;
                font-weight: bold;
                text-decoration: underline;
            }
            QListWidget::item:hover {
                background-color: #0099C0;
            }
        """)

        self.main_layout.addWidget(self.sidebar)

        # ── SEPARADOR VERTICAL ───────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(sep)

        # ── CONTINGUT ────────────────────────────────────
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(6)

        # Header — Connection + Workspace
        self.header_widget = QWidget()
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        # Connection row
        conn_row = QHBoxLayout()
        conn_row.addWidget(QLabel("Connection:"))
        self.cmb_connections = QComboBox()
        self.cmb_connections.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        conn_row.addWidget(self.cmb_connections)

        # Separador vertical entre connection i status
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setFrameShadow(QFrame.Sunken)
        conn_row.addWidget(sep_v)

        self.lbl_status = QLabel("●")
        self.lbl_status.setStyleSheet("color: red;")
        conn_row.addWidget(self.lbl_status)
        header_layout.addLayout(conn_row)

        # Workspace row
        ws_row = QHBoxLayout()
        ws_row.addWidget(QLabel("Workspace:"))
        self.cmb_workspace = QComboBox()
        self.cmb_workspace.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        ws_row.addWidget(self.cmb_workspace)
        header_layout.addLayout(ws_row)

        content_layout.addWidget(self.header_widget)

        # Separador horitzontal
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setFrameShadow(QFrame.Sunken)
        content_layout.addWidget(sep_h)

        # ── PÀGINES ───────────────────────────────────────
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        self.connections_page = ConnectionsPage()
        self.styles_page = StylesPage(self.api)
        self.reload_page = ReloadPage(self.api)
        self.about_page = AboutPage()

        self.stack.addWidget(self.connections_page)  # index 0
        self.stack.addWidget(self.styles_page)        # index 1
        self.stack.addWidget(self.reload_page)        # index 2
        self.stack.addWidget(self.about_page)         # index 3

        self.main_layout.addWidget(content_widget)
        self.setWidget(self.main_widget)

    def _setup_connections(self):
        """Connect all signals to slots."""
        self.sidebar.currentRowChanged.connect(self._on_page_changed)
        self.cmb_connections.currentTextChanged.connect(
            self._on_connection_changed
        )
        self.cmb_workspace.currentTextChanged.connect(
            self._on_workspace_changed
        )
        self.connections_page.connections_changed.connect(
            self._load_connections
        )

    def _on_page_changed(self, index):
        """Show or hide header depending on the page."""
        self.stack.setCurrentIndex(index)
        self.header_widget.setVisible(index in [1, 2])

    def _load_connections(self):
        """Load all saved connections into the ComboBox."""
        self.cmb_connections.blockSignals(True)
        self.cmb_connections.clear()
        connections = self.manager.get_all_connections()
        if connections:
            self.cmb_connections.addItems(connections)
        else:
            self.cmb_connections.addItem("No connections saved")
        self.cmb_connections.blockSignals(False)
        self._on_connection_changed(self.cmb_connections.currentText())

    def _on_connection_changed(self, name):
        """Called when user selects a different connection."""
        connection = self.manager.load_connection(name)
        if not connection:
            self._set_status(False)
            return

        self.api = GeoServerAPI(
            url=connection['url'],
            user=connection['user'],
            password=connection['password']
        )

        if not self.api.test_connection():
            self._set_status(False)
            return

        self._set_status(True)

        self.cmb_workspace.blockSignals(True)
        self.cmb_workspace.clear()
        workspaces = self.api.get_workspaces()
        self.cmb_workspace.addItems(workspaces)
        self.cmb_workspace.blockSignals(False)

        self._on_workspace_changed(self.cmb_workspace.currentText())

    def _on_workspace_changed(self, workspace):
        """Called when user selects a different workspace."""
        if self.api and workspace:
            self.api.set_workspace(workspace)
            self.reload_page.set_api(self.api)
            self.styles_page.set_api(self.api)

    def _set_status(self, connected):
        """Update the status indicator."""
        if connected:
            self.lbl_status.setText("●")
            self.lbl_status.setStyleSheet("color: green;")
        else:
            self.lbl_status.setText("●")
            self.lbl_status.setStyleSheet("color: red;")