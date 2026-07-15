from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QPushButton,
    QLabel, QSizePolicy, QFileDialog,
    QMessageBox, QFrame, QScrollArea
)
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.PyQt.QtCore import Qt, QSize, QThread, pyqtSignal
from qgis.core import QgsProject
from core.sld_exporter import SLDExporter
from .icons import themed_icon


class _StylesListWorker(QThread):
    """Fetch the workspace style list off the GUI thread."""
    ready = pyqtSignal(int, object)

    def __init__(self, api, req_id):
        super().__init__()
        self._api = api
        self._req_id = req_id

    def run(self):
        try:
            styles = self._api.get_workspace_styles()
        except Exception:
            styles = []
        self.ready.emit(self._req_id, styles)


class _StyleDetailWorker(QThread):
    """Fetch a style's SLD + legend graphic off the GUI thread."""
    ready = pyqtSignal(int, str, object)

    def __init__(self, api, style_name, req_id):
        super().__init__()
        self._api = api
        self._style_name = style_name
        self._req_id = req_id

    def run(self):
        sld = ""
        png = None
        try:
            sld = self._api.get_style_content(self._style_name) or ""
            if sld:
                png = self._api.get_legend_graphic(self._style_name, sld)
        except Exception:
            pass
        self.ready.emit(self._req_id, sld, png)


class StylesPage(QWidget):
    """
    Handles GeoServer styles visualization and management.
    Left panel: GeoServer workspace styles.
    Right panel: QGIS project layers.
    Bottom: SLD preview + legend.
    """

    def __init__(self, api=None):
        super().__init__()
        self.api = api
        self._list_req = 0
        self._detail_req = 0
        self._workers = set()
        self._setup_ui()
        self._setup_connections()
        self._connect_project_signals()

    def _track(self, worker):
        """Keep a reference to a running worker until it finishes."""
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Title ────────────────────────────────────────
        title = QLabel("Styles")
        title.setProperty("role", "title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Browse styles from the active workspace and apply them to your layers."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ── Top card: GeoServer styles | QGIS layers ─────
        top_card = QFrame()
        top_card.setObjectName("card")
        top_card.setFrameShape(QFrame.StyledPanel)
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(12)

        # Left column — GeoServer styles
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        lbl_styles = QLabel("GeoServer styles")
        lbl_styles.setProperty("role", "section")
        left_layout.addWidget(lbl_styles)

        self.lst_styles = QListWidget()
        self.lst_styles.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        left_layout.addWidget(self.lst_styles)
        top_layout.addLayout(left_layout, stretch=1)

        # Vertical separator
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setFrameShadow(QFrame.Plain)
        sep_v.setProperty("role", "separator")
        top_layout.addWidget(sep_v)

        # Right column — QGIS project layers
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        lbl_layers = QLabel("Project layers")
        lbl_layers.setProperty("role", "section")
        right_layout.addWidget(lbl_layers)

        self.lst_layers = QListWidget()
        self.lst_layers.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.lst_layers)
        top_layout.addLayout(right_layout, stretch=1)

        layout.addWidget(top_card)

        # ── Bottom card: SLD preview + Legend ────────────
        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_card.setFrameShape(QFrame.StyledPanel)
        preview_layout = QHBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(12)

        # SLD XML preview
        sld_layout = QVBoxLayout()
        sld_layout.setSpacing(6)
        lbl_sld = QLabel("SLD Preview")
        lbl_sld.setProperty("role", "section")
        sld_layout.addWidget(lbl_sld)

        self.txt_sld_preview = QTextEdit()
        self.txt_sld_preview.setReadOnly(True)
        self.txt_sld_preview.setFont(QFont("Consolas, Courier New", 9))
        self.txt_sld_preview.setPlaceholderText(
            "Select a style to preview its SLD..."
        )
        self.txt_sld_preview.setFixedHeight(180)
        sld_layout.addWidget(self.txt_sld_preview)
        preview_layout.addLayout(sld_layout, stretch=3)

        # Vertical separator
        sep_pv = QFrame()
        sep_pv.setFrameShape(QFrame.VLine)
        sep_pv.setFrameShadow(QFrame.Plain)
        sep_pv.setProperty("role", "separator")
        preview_layout.addWidget(sep_pv)

        # Legend graphic
        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(6)
        lbl_legend = QLabel("Legend")
        lbl_legend.setProperty("role", "section")
        legend_layout.addWidget(lbl_legend)

        self.scroll_legend = QScrollArea()
        self.scroll_legend.setWidgetResizable(True)
        self.scroll_legend.setFixedHeight(180)
        self.scroll_legend.setAlignment(Qt.AlignCenter)
        self.lbl_legend = QLabel("Select a style\nto load legend")
        self.lbl_legend.setAlignment(Qt.AlignCenter)
        self.lbl_legend.setProperty("role", "subtitle")
        self.scroll_legend.setWidget(self.lbl_legend)
        legend_layout.addWidget(self.scroll_legend)
        preview_layout.addLayout(legend_layout, stretch=1)

        layout.addWidget(preview_card)

        # ── Action buttons row ───────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_download = QPushButton("  Download SLD")
        self.btn_apply = QPushButton("  Apply style to layer")
        self.btn_apply.setProperty("primary", "true")
        self.btn_delete = QPushButton("  Delete style")
        self.btn_delete.setProperty("danger", "true")

        for btn, icon_file in (
            (self.btn_download, "ic_download.svg"),
            (self.btn_apply, "ic_apply.svg"),
            (self.btn_delete, "ic_delete.svg"),
        ):
            btn.setIcon(themed_icon(icon_file))
            btn.setIconSize(QSize(16, 16))

        self.btn_download.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_delete.setEnabled(False)

        btn_row.addWidget(self.btn_download)
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()

        layout.addLayout(btn_row)

    def _setup_connections(self):
        self.lst_styles.currentTextChanged.connect(self._on_style_selected)
        self.lst_layers.currentTextChanged.connect(self._update_apply_button)
        self.btn_download.clicked.connect(self._on_download)
        self.btn_apply.clicked.connect(self._on_apply_style)
        self.btn_delete.clicked.connect(self._on_delete)

    def _connect_project_signals(self):
        """Keep the layers list in sync with the QGIS project."""
        QgsProject.instance().layersAdded.connect(self._load_layers)
        QgsProject.instance().layersRemoved.connect(self._load_layers)

    def set_api(self, api):
        """Update the API instance and reload styles."""
        self.api = api
        self.load_styles()
        self._load_layers()

    def load_styles(self):
        """Load all styles from the current workspace (in the background)."""
        self.lst_styles.clear()
        self.txt_sld_preview.clear()
        self._clear_legend()
        self.btn_download.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_delete.setEnabled(False)

        if not self.api:
            return

        self._list_req += 1
        worker = _StylesListWorker(self.api, self._list_req)
        worker.ready.connect(self._on_styles_listed)
        self._track(worker)
        worker.start()

    def _on_styles_listed(self, req_id, styles):
        """Populate the style list once the background fetch completes."""
        if req_id != self._list_req:
            return  # a newer request superseded this one
        self.lst_styles.clear()
        self.lst_styles.addItems(styles)

    def _load_layers(self, *args):
        """Load all vector layers from the current QGIS project."""
        current = self.lst_layers.currentItem()
        current_name = current.text() if current else None

        self.lst_layers.clear()

        layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == layer.VectorLayer
        ]
        for layer in layers:
            self.lst_layers.addItem(layer.name())

        # Restore selection if still present
        if current_name:
            items = self.lst_layers.findItems(current_name, Qt.MatchExactly)
            if items:
                self.lst_layers.setCurrentItem(items[0])

    def _on_style_selected(self, style_name):
        """Load SLD preview and legend when a style is selected (async)."""
        if not style_name or not self.api:
            self.txt_sld_preview.clear()
            self._clear_legend()
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self._update_apply_button()
            return

        # Optimistic loading state — the network work runs in a worker thread
        # so the QGIS UI never freezes while the legend is fetched.
        self.txt_sld_preview.clear()
        self.btn_download.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.lbl_legend.setPixmap(QPixmap())
        self.lbl_legend.setText("Loading…")

        self._detail_req += 1
        worker = _StyleDetailWorker(self.api, style_name, self._detail_req)
        worker.ready.connect(self._on_style_detail)
        self._track(worker)
        worker.start()

    def _on_style_detail(self, req_id, sld, png_bytes):
        """Update preview + legend once the background fetch completes."""
        if req_id != self._detail_req:
            return  # a newer selection superseded this one

        if sld:
            self.txt_sld_preview.setPlainText(sld)
            self.btn_download.setEnabled(True)
            self.btn_delete.setEnabled(True)
            if png_bytes:
                pixmap = QPixmap()
                pixmap.loadFromData(png_bytes)
                self.lbl_legend.setPixmap(
                    pixmap.scaledToWidth(
                        min(pixmap.width(), self.scroll_legend.width() - 10),
                        Qt.SmoothTransformation
                    )
                )
                self.lbl_legend.adjustSize()
            else:
                self._clear_legend("Could not load legend")
        else:
            self.txt_sld_preview.setPlainText("Could not load SLD content.")
            self._clear_legend()
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)

        self._update_apply_button()

    def _clear_legend(self, text="Select a style\nto load legend"):
        """Reset the legend panel to its placeholder state."""
        self.lbl_legend.setPixmap(QPixmap())
        self.lbl_legend.setText(text)
        self.lbl_legend.setProperty("role", "subtitle")
        # Re-polish so property-driven styling applies
        self.lbl_legend.style().unpolish(self.lbl_legend)
        self.lbl_legend.style().polish(self.lbl_legend)
        self.lbl_legend.update()

    def _update_apply_button(self, *args):
        """Enable Apply button only when both a style and a layer are selected."""
        style_selected = self.lst_styles.currentItem() is not None
        layer_selected = self.lst_layers.currentItem() is not None
        sld_loaded = bool(self.txt_sld_preview.toPlainText())
        self.btn_apply.setEnabled(style_selected and layer_selected and sld_loaded)

    def _on_apply_style(self):
        """Apply the selected GeoServer SLD style to the selected QGIS layer."""
        style_item = self.lst_styles.currentItem()
        layer_item = self.lst_layers.currentItem()
        if not style_item or not layer_item:
            return

        style_name = style_item.text()
        layer_name = layer_item.text()
        sld_content = self.txt_sld_preview.toPlainText()

        if not sld_content:
            return

        # Find the QGIS layer object by name
        matched = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.name() == layer_name
        ]
        if not matched:
            QMessageBox.warning(self, "Error", f"Layer '{layer_name}' not found in project.")
            return
        layer = matched[0]

        success, error_msg = SLDExporter.apply_sld_to_layer(layer, sld_content)

        if success:
            QMessageBox.information(
                self,
                "Style applied",
                f"Style '{style_name}' applied to layer '{layer_name}'."
            )
        else:
            QMessageBox.warning(
                self,
                "Error applying style",
                f"Could not apply style '{style_name}' to '{layer_name}'.\n\n{error_msg}"
            )

    def _on_download(self):
        """Download the selected style as an SLD file."""
        style_item = self.lst_styles.currentItem()
        if not style_item:
            return

        style_name = style_item.text()
        sld_content = self.txt_sld_preview.toPlainText()
        if not sld_content:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save SLD File",
            f"{style_name}.sld",
            "SLD Files (*.sld);;All Files (*)"
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(sld_content)

    def _on_delete(self):
        """Delete the selected style from GeoServer."""
        style_item = self.lst_styles.currentItem()
        if not style_item:
            return

        style_name = style_item.text()

        reply = QMessageBox.question(
            self,
            "Delete Style",
            f"Are you sure you want to delete '{style_name}' from GeoServer?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.api.delete_style(style_name)
            if success:
                self.load_styles()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Could not delete style '{style_name}'"
                )
