from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QPushButton,
    QLabel, QSizePolicy, QFileDialog,
    QMessageBox, QFrame
)
from qgis.PyQt.QtGui import QFont


class StylesPage(QWidget):
    """
    Handles GeoServer styles visualization and management.
    """

    def __init__(self, api=None):
        super().__init__()
        self.api = api
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Title
        title = QLabel("Styles")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        # Main content — list + preview
        content_row = QHBoxLayout()

        # Left — styles list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Available styles:"))
        self.lst_styles = QListWidget()
        self.lst_styles.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        left_layout.addWidget(self.lst_styles)
        content_row.addLayout(left_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        content_row.addWidget(sep)

        # Right — SLD preview
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("SLD Preview:"))
        self.txt_sld_preview = QTextEdit()
        self.txt_sld_preview.setReadOnly(True)
        self.txt_sld_preview.setFont(QFont("Courier New", 9))
        self.txt_sld_preview.setPlaceholderText(
            "Select a style to preview its SLD..."
        )
        self.txt_sld_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.txt_sld_preview)
        content_row.addLayout(right_layout)

        # Proporció 1:2
        content_row.setStretch(0, 1)
        content_row.setStretch(2, 2)

        layout.addLayout(content_row)

        # Separator
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep_h)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_download = QPushButton("⬇ Download SLD")
        self.btn_delete = QPushButton("🗑 Delete Style")
        self.btn_download.setEnabled(False)
        self.btn_delete.setEnabled(False)
        btn_row.addWidget(self.btn_download)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _setup_connections(self):
        self.lst_styles.currentTextChanged.connect(self._on_style_selected)
        self.btn_download.clicked.connect(self._on_download)
        self.btn_delete.clicked.connect(self._on_delete)

    def set_api(self, api):
        """Update the API instance and reload styles."""
        self.api = api
        self.load_styles()

    def load_styles(self):
        """Load all styles from the current workspace."""
        self.lst_styles.clear()
        self.txt_sld_preview.clear()
        self.btn_download.setEnabled(False)
        self.btn_delete.setEnabled(False)

        if not self.api:
            return

        styles = self.api.get_workspace_styles()
        self.lst_styles.addItems(styles)

    def _on_style_selected(self, style_name):
        """Load SLD preview when a style is selected."""
        if not style_name or not self.api:
            return

        sld = self.api.get_style_content(style_name)
        if sld:
            self.txt_sld_preview.setPlainText(sld)
            self.btn_download.setEnabled(True)
            self.btn_delete.setEnabled(True)
        else:
            self.txt_sld_preview.setPlainText("Could not load SLD content.")
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(False)

    def _on_download(self):
        """Download the selected style as an SLD file."""
        style_name = self.lst_styles.currentItem()
        if not style_name:
            return

        style_name = style_name.text()
        sld_content = self.txt_sld_preview.toPlainText()

        if not sld_content:
            return

        # Open save dialog
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
        style_name = self.lst_styles.currentItem()
        if not style_name:
            return

        style_name = style_name.text()

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