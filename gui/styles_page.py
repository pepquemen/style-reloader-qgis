from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QPushButton,
    QLabel, QSizePolicy, QFileDialog,
    QMessageBox, QFrame, QScrollArea
)
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from core.sld_exporter import SLDExporter


class StylesPage(QWidget):
    """
    Handles GeoServer styles visualization and management.
    Left panel: GeoServer workspace styles.
    Right panel: QGIS project layers.
    Bottom: SLD preview.
    Buttons: Download, Apply style to layer, Delete.
    """

    def __init__(self, api=None):
        super().__init__()
        self.api = api
        self._setup_ui()
        self._setup_connections()
        self._connect_project_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Title
        title = QLabel("Styles")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        # ── TOP ROW: styles list | layers list ───────────────
        top_row = QHBoxLayout()

        # Left — GeoServer styles
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("GeoServer styles:"))
        self.lst_styles = QListWidget()
        self.lst_styles.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        left_layout.addWidget(self.lst_styles)
        top_row.addLayout(left_layout)

        # Vertical separator
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setFrameShadow(QFrame.Sunken)
        top_row.addWidget(sep_v)

        # Right — QGIS project layers
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Project layers:"))
        self.lst_layers = QListWidget()
        self.lst_layers.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.lst_layers)
        top_row.addLayout(right_layout)

        top_row.setStretch(0, 1)
        top_row.setStretch(2, 1)

        layout.addLayout(top_row)

        # ── PREVIEW ROW: SLD + Legend ─────────────────────────
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep_h)

        preview_row = QHBoxLayout()

        # SLD XML preview
        sld_layout = QVBoxLayout()
        sld_layout.addWidget(QLabel("SLD Preview:"))
        self.txt_sld_preview = QTextEdit()
        self.txt_sld_preview.setReadOnly(True)
        self.txt_sld_preview.setFont(QFont("Courier New", 9))
        self.txt_sld_preview.setPlaceholderText(
            "Select a style to preview its SLD..."
        )
        self.txt_sld_preview.setFixedHeight(160)
        sld_layout.addWidget(self.txt_sld_preview)
        preview_row.addLayout(sld_layout, stretch=3)

        # Vertical separator
        sep_pv = QFrame()
        sep_pv.setFrameShape(QFrame.VLine)
        sep_pv.setFrameShadow(QFrame.Sunken)
        preview_row.addWidget(sep_pv)

        # Legend graphic
        legend_layout = QVBoxLayout()
        legend_layout.addWidget(QLabel("Legend:"))
        self.scroll_legend = QScrollArea()
        self.scroll_legend.setWidgetResizable(True)
        self.scroll_legend.setFixedHeight(160)
        self.scroll_legend.setAlignment(Qt.AlignCenter)
        self.lbl_legend = QLabel("Select a style\nto load legend")
        self.lbl_legend.setAlignment(Qt.AlignCenter)
        self.lbl_legend.setStyleSheet("color: gray; font-size: 11px;")
        self.scroll_legend.setWidget(self.lbl_legend)
        legend_layout.addWidget(self.scroll_legend)
        preview_row.addLayout(legend_layout, stretch=1)

        layout.addLayout(preview_row)

        # ── BUTTONS ──────────────────────────────────────────
        sep_h2 = QFrame()
        sep_h2.setFrameShape(QFrame.HLine)
        sep_h2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep_h2)

        btn_row = QHBoxLayout()
        self.btn_download = QPushButton("⬇ Download SLD")
        self.btn_apply = QPushButton("▶ Apply style to layer")
        self.btn_delete = QPushButton("🗑 Delete Style")

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
        """Load all styles from the current workspace."""
        self.lst_styles.clear()
        self.txt_sld_preview.clear()
        self.btn_download.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_delete.setEnabled(False)

        if not self.api:
            return

        styles = self.api.get_workspace_styles()
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
            items = self.lst_layers.findItems(current_name, 0)
            if items:
                self.lst_layers.setCurrentItem(items[0])

    def _on_style_selected(self, style_name):
        """Load SLD preview and legend when a style is selected."""
        if not style_name or not self.api:
            self.txt_sld_preview.clear()
            self._clear_legend()
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self._update_apply_button()
            return

        sld = self.api.get_style_content(style_name)
        if sld:
            self.txt_sld_preview.setPlainText(sld)
            self.btn_download.setEnabled(True)
            self.btn_delete.setEnabled(True)
            self._load_legend(sld)
        else:
            self.txt_sld_preview.setPlainText("Could not load SLD content.")
            self._clear_legend()
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)

        self._update_apply_button()

    def _load_legend(self, sld_content):
        """Fetch and display the legend graphic from GeoServer."""
        self.lbl_legend.setText("Loading...")
        self.lbl_legend.setPixmap(QPixmap())

        style_name = self.lst_styles.currentItem().text()
        png_bytes = self.api.get_legend_graphic(style_name, sld_content)
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

    def _clear_legend(self, text="Select a style\nto load legend"):
        """Reset the legend panel to its placeholder state."""
        self.lbl_legend.setPixmap(QPixmap())
        self.lbl_legend.setText(text)
        self.lbl_legend.setStyleSheet("color: gray; font-size: 11px;")

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
