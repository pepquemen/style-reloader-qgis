from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton,
    QCheckBox, QLabel, QTextEdit, QFrame,
    QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QColor
from qgis.core import QgsProject, QgsMapLayer

from core.style_sync import StyleSync


class ReloadPage(QWidget):
    """
    Handles layer selection and style reload.
    """

    def __init__(self, api=None):
        super().__init__()
        self.api = api
        self._setup_ui()
        self._setup_connections()
        self.load_layers()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # ── LLISTA DE CAPES ──────────────────────────────
        self.lst_layers = QListWidget()
        self.lst_layers.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.lst_layers)

        # Botons select/deselect
        btn_row = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_deselect_all = QPushButton("Deselect All")
        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_deselect_all)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Separador
        layout.addWidget(self._make_separator())

        # ── OPCIONS ──────────────────────────────────────
        self.chk_assign_style = QCheckBox("Apply style to layer")
        self.chk_assign_style.setChecked(True)
        layout.addWidget(self.chk_assign_style)

        # Botó reload
        self.btn_reload = QPushButton("Reload Style")
        self.btn_reload.setMinimumHeight(40)
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background-color: #00A8D6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0088B0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.btn_reload)

        # Separador
        layout.addWidget(self._make_separator())

        # ── LOG ──────────────────────────────────────────
        layout.addWidget(QLabel("Log"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(150)
        self.txt_log.setFont(QFont("Courier New", 9))
        layout.addWidget(self.txt_log)

    def _setup_connections(self):
        """Connect signals to slots."""
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.btn_reload.clicked.connect(self._on_reload)
        self.chk_assign_style.stateChanged.connect(self._on_assign_style_changed)

    def _make_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def set_api(self, api):
        """Update the API instance."""
        self.api = api

    def load_layers(self):
        """Load all vector layers from the current QGIS project."""
        self.lst_layers.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                item = QListWidgetItem(layer.name())
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.lst_layers.addItem(item)

    def _select_all(self):
        """Check all layers."""
        for i in range(self.lst_layers.count()):
            self.lst_layers.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self):
        """Uncheck all layers."""
        for i in range(self.lst_layers.count()):
            self.lst_layers.item(i).setCheckState(Qt.Unchecked)

    def _on_assign_style_changed(self, state):
        """Update reload button text based on checkbox state."""
        if state == Qt.Checked:
            self.btn_reload.setText("Reload and Apply")
        else:
            self.btn_reload.setText("Reload Style Only")

    def _get_checked_layers(self):
        """Return list of checked QGIS layers."""
        checked_names = []
        for i in range(self.lst_layers.count()):
            item = self.lst_layers.item(i)
            if item.checkState() == Qt.Checked:
                checked_names.append(item.text())

        # Match names to actual QGIS layers
        all_layers = QgsProject.instance().mapLayers().values()
        return [l for l in all_layers if l.name() in checked_names]

    def _on_reload(self):
        """Execute style reload for checked layers."""

        # No connection
        if not self.api:
            self._log_error("No active connection to GeoServer")
            return

        # Get checked layers
        layers = self._get_checked_layers()
        if not layers:
            self._log_error("No layers selected")
            return

        # Clear log
        self.txt_log.clear()

        # Execute sync
        sync = StyleSync(self.api)
        assign = self.chk_assign_style.isChecked()
        results, summary = sync.sync_layers(layers, assign_style=assign)

        # Show results in log
        for r in results:
            if r['status'] == StyleSync.SUCCESS:
                self._log_success(f"{r['layer']}: {r['message']}")
            elif r['status'] == StyleSync.SKIPPED:
                self._log_warning(f"{r['layer']}: {r['message']}")
            else:
                self._log_error(f"{r['layer']}: {r['message']}")

        # Show summary
        self._log_info(f"─── {summary['message']} ───")

    def _log_success(self, message):
        self.txt_log.append(f'<span style="color: green;">✅ {message}</span>')

    def _log_error(self, message):
        self.txt_log.append(f'<span style="color: red;">❌ {message}</span>')

    def _log_warning(self, message):
        self.txt_log.append(f'<span style="color: orange;">⚠️ {message}</span>')

    def _log_info(self, message):
        self.txt_log.append(f'<span style="color: gray;">{message}</span>')