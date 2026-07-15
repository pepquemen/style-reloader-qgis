import os

from qgis.PyQt.QtWidgets import (
    QDialog, QWidget, QHBoxLayout,
    QVBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QComboBox, QLabel,
    QFrame, QSizePolicy
)
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtCore import Qt, QSize

from core.connection_manager import ConnectionManager
from core.geoserver_api import GeoServerAPI
from gui.reload_page import ReloadPage
from gui.connections_page import ConnectionsPage
from gui.styles_page import StylesPage
from gui.about_page import AboutPage
from gui.icons import themed_icon
from gui.styles import STYLESHEET, SIDEBAR_STYLESHEET


class MainPanel(QDialog):
    """
    Main plugin panel as a floating dialog.
    Contains the sidebar navigation and the stacked pages.
    """

    def __init__(self, iface):
        super().__init__(
            iface.mainWindow(),
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("Style Reloader for GeoServer")
        # Use the plugin's own icon in the window title bar (not the QGIS one).
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'assets', 'icons', 'reload.png'
        )
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(700, 500)
        self.iface = iface
        self.api = None
        self.manager = ConnectionManager()

        self.setStyleSheet(STYLESHEET)

        self._setup_ui()
        self._setup_connections()
        self._load_connections()
        self._on_page_changed(2)

    def _setup_ui(self):
        """Build the main panel UI programmatically."""

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(150)
        self.sidebar.setStyleSheet(SIDEBAR_STYLESHEET)
        self.sidebar.setIconSize(QSize(18, 18))

        # Sidebar items with clean line icons (white on the blue sidebar)
        nav_white = QColor("#ffffff")
        nav_items = [
            ("Connections", "nav_connections.svg", 0),
            ("Styles", "nav_styles.svg", 1),
            ("Publication", "nav_publication.svg", 2),
            ("About", "nav_about.svg", 3),
        ]
        for label, icon_file, index in nav_items:
            item = QListWidgetItem(
                themed_icon(icon_file, nav_white), f"  {label}"
            )
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(2)

        self.main_layout.addWidget(self.sidebar)

        # ── CONTENT AREA ─────────────────────────────────
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        # Header — Connection + Workspace + Status
        self.header_widget = QWidget()
        self.header_widget.setObjectName("headerWidget")
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Connection row
        conn_row = QHBoxLayout()
        conn_row.setSpacing(8)

        lbl_conn = QLabel("Connection")
        lbl_conn.setProperty("role", "section")
        conn_row.addWidget(lbl_conn)

        self.cmb_connections = QComboBox()
        self.cmb_connections.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        conn_row.addWidget(self.cmb_connections, stretch=1)

        self.status_pill = QFrame()
        self.status_pill.setObjectName("statusPill")
        self.status_pill.setProperty("connected", "false")
        status_layout = QHBoxLayout(self.status_pill)
        status_layout.setContentsMargins(10, 2, 10, 2)
        status_layout.setSpacing(6)
        self.lbl_status = QLabel("● Disconnected")
        self.lbl_status.setStyleSheet("background: transparent; border: none;")
        status_layout.addWidget(self.lbl_status)
        conn_row.addWidget(self.status_pill)

        header_layout.addLayout(conn_row)

        # Workspace row
        ws_row = QHBoxLayout()
        ws_row.setSpacing(8)
        lbl_ws = QLabel("Workspace")
        lbl_ws.setProperty("role", "section")
        ws_row.addWidget(lbl_ws)

        self.cmb_workspace = QComboBox()
        self.cmb_workspace.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        ws_row.addWidget(self.cmb_workspace, stretch=1)
        ws_row.addStretch()
        header_layout.addLayout(ws_row)

        content_layout.addWidget(self.header_widget)

        # Horizontal separator
        sep_h = QFrame()
        sep_h.setProperty("role", "separator")
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setFrameShadow(QFrame.Plain)
        content_layout.addWidget(sep_h)

        # ── PAGES (stacked) ───────────────────────────────
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

        dlg_layout = QHBoxLayout(self)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.addWidget(self.main_widget)

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
        """Update the connection status pill."""
        if connected:
            self.lbl_status.setText("● Connected")
            self.status_pill.setProperty("connected", "true")
        else:
            self.lbl_status.setText("● Disconnected")
            self.status_pill.setProperty("connected", "false")
        # Re-apply stylesheet so the property change takes effect
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.status_pill.update()
