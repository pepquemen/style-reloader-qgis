from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton,
    QCheckBox, QLabel, QTextEdit, QFrame,
    QSizePolicy
)
from qgis.PyQt.QtCore import Qt, QSize, QThread, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.core import QgsProject, QgsMapLayer

from core.style_sync import StyleSync
from .icons import themed_icon


class _SyncWorker(QThread):
    """Run the network part of a publish off the GUI thread."""
    done = pyqtSignal(list, dict)

    def __init__(self, api, prepared, assign_style):
        super().__init__()
        self._api = api
        self._prepared = prepared
        self._assign_style = assign_style

    def run(self):
        try:
            results, summary = StyleSync(self._api).sync_prepared(
                self._prepared, assign_style=self._assign_style
            )
        except Exception as e:
            results, summary = [], {
                'total': 0, 'success': 0, 'skipped': 0, 'errors': 1,
                'message': f'Unexpected error: {e}',
            }
        self.done.emit(results, summary)


class ReloadPage(QWidget):
    """
    Handles layer selection and style reload (publication).
    """

    def __init__(self, api=None):
        super().__init__()
        self.api = api
        self._sync_worker = None
        self._setup_ui()
        self._setup_connections()
        self.load_layers()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Title ────────────────────────────────────────
        title = QLabel("Publication")
        title.setProperty("role", "title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Select the layers to publish to GeoServer and reload their styles."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ── Layers card ─────────────────────────────────
        layers_card = QFrame()
        layers_card.setObjectName("card")
        layers_card.setFrameShape(QFrame.StyledPanel)
        layers_layout = QVBoxLayout(layers_card)
        layers_layout.setContentsMargins(12, 12, 12, 12)
        layers_layout.setSpacing(10)

        lbl_layers = QLabel("Project layers")
        lbl_layers.setProperty("role", "section")
        layers_layout.addWidget(lbl_layers)

        self.lst_layers = QListWidget()
        self.lst_layers.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layers_layout.addWidget(self.lst_layers)

        # Select / Deselect buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_select_all = QPushButton("Select all")
        self.btn_deselect_all = QPushButton("Deselect all")
        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_deselect_all)
        btn_row.addStretch()
        layers_layout.addLayout(btn_row)

        layout.addWidget(layers_card, stretch=1)

        # ── Options card ────────────────────────────────
        options_card = QFrame()
        options_card.setObjectName("card")
        options_card.setFrameShape(QFrame.StyledPanel)
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(10)

        lbl_options = QLabel("Options")
        lbl_options.setProperty("role", "section")
        options_layout.addWidget(lbl_options)

        self.chk_assign_style = QCheckBox("Apply style to layer")
        self.chk_assign_style.setChecked(True)
        options_layout.addWidget(self.chk_assign_style)

        self.btn_reload = QPushButton("  Reload and apply")
        self.btn_reload.setProperty("primary", "true")
        self.btn_reload.setMinimumHeight(38)
        # Primary buttons render white text, so tint the icon white too.
        self.btn_reload.setIcon(themed_icon("ic_reload.svg", "#ffffff"))
        self.btn_reload.setIconSize(QSize(16, 16))
        options_layout.addWidget(self.btn_reload)

        layout.addWidget(options_card)

        # ── Log card ─────────────────────────────────────
        log_card = QFrame()
        log_card.setObjectName("card")
        log_card.setFrameShape(QFrame.StyledPanel)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(8)

        lbl_log = QLabel("Log")
        lbl_log.setProperty("role", "section")
        log_layout.addWidget(lbl_log)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(150)
        self.txt_log.setFont(QFont("Consolas, Courier New", 9))
        log_layout.addWidget(self.txt_log)

        layout.addWidget(log_card)

    def _setup_connections(self):
        """Connect signals to slots."""
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.btn_reload.clicked.connect(self._on_reload)
        self.chk_assign_style.stateChanged.connect(self._on_assign_style_changed)

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
            self.btn_reload.setText("  Reload and apply")
        else:
            self.btn_reload.setText("  Reload style only")

    def _get_checked_layers(self):
        """Return list of checked QGIS layers."""
        checked_names = []
        for i in range(self.lst_layers.count()):
            item = self.lst_layers.item(i)
            if item.checkState() == Qt.Checked:
                checked_names.append(item.text())

        # Match names to actual QGIS layers
        all_layers = QgsProject.instance().mapLayers().values()
        return [
            layer for layer in all_layers
            if layer.name() in checked_names
        ]

    def _on_reload(self):
        """Export SLDs (GUI thread) then publish to GeoServer in background."""

        # Avoid launching a second publish while one is running.
        if self._sync_worker is not None and self._sync_worker.isRunning():
            return

        # No connection
        if not self.api:
            self._log_error("No active connection to GeoServer")
            return

        # Get checked layers
        layers = self._get_checked_layers()
        if not layers:
            self._log_error("No layers selected")
            return

        self.txt_log.clear()

        # Export SLDs on the GUI thread (touches QGIS layer objects — must not
        # happen in a worker thread), then hand the network work to the worker.
        sync = StyleSync(self.api)
        prepared = sync.prepare_layers(layers)

        assign = self.chk_assign_style.isChecked()

        self.btn_reload.setEnabled(False)
        self._log_info("Publishing…")

        self._sync_worker = _SyncWorker(self.api, prepared, assign)
        self._sync_worker.done.connect(self._on_sync_done)
        self._sync_worker.start()

    def _on_sync_done(self, results, summary):
        """Render sync results once the background publish finishes."""
        self.btn_reload.setEnabled(True)
        self.txt_log.clear()

        for r in results:
            if r['status'] == StyleSync.SUCCESS:
                self._log_success(f"{r['layer']}: {r['message']}")
            elif r['status'] == StyleSync.SKIPPED:
                self._log_warning(f"{r['layer']}: {r['message']}")
            else:
                self._log_error(f"{r['layer']}: {r['message']}")

        if summary.get('message'):
            self._log_info(f"─── {summary['message']} ───")

    def _log_success(self, message):
        self.txt_log.append(f'<span style="color: #10b981;">✓ {message}</span>')

    def _log_error(self, message):
        self.txt_log.append(f'<span style="color: #ef4444;">✗ {message}</span>')

    def _log_warning(self, message):
        self.txt_log.append(f'<span style="color: #f59e0b;">⚠ {message}</span>')

    def _log_info(self, message):
        self.txt_log.append(f'<span style="color: #64748b;">{message}</span>')
