from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QFrame, QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
import os


class AboutPage(QWidget):
    """
    Shows plugin information, authors and links.
    """

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        # Logo placeholder
        self.lbl_logo = QLabel("🔄")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.lbl_logo)

        # Plugin name
        lbl_name = QLabel("Style Reloader for GeoServer")
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl_name)

        # Version
        version = self._get_version()
        lbl_version = QLabel(f"v{version}")
        lbl_version.setAlignment(Qt.AlignCenter)
        lbl_version.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(lbl_version)

        # Description
        lbl_desc = QLabel(
            "A QGIS plugin to sync layer styles\n"
            "from QGIS to GeoServer via REST API."
        )
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        layout.addWidget(self._make_separator())

        # Authors
        layout.addWidget(self._make_section_title("👤 Authors"))
        layout.addWidget(QLabel("Josep Quevedo & Pau Morell"))

        # Organization
        layout.addWidget(self._make_section_title("🏢 Organization"))
        lbl_org = QLabel(
            "Natural Hazards and Emergencies\n"
            "Observatory — Balearic Islands"
        )
        lbl_org.setWordWrap(True)
        layout.addWidget(lbl_org)

        layout.addWidget(self._make_separator())

        # Repository
        layout.addWidget(self._make_section_title("🔗 Repository"))
        lbl_repo = QLabel(
            '<a href="https://github.com/pepquemen/style-reloader-qgis">'
            'github.com/pepquemen/style-reloader-qgis</a>'
        )
        lbl_repo.setOpenExternalLinks(True)
        layout.addWidget(lbl_repo)

        # Report a bug
        layout.addWidget(self._make_section_title("🐛 Report a bug"))
        lbl_bugs = QLabel(
            '<a href="https://github.com/pepquemen/style-reloader-qgis/issues">'
            'github.com/pepquemen/style-reloader-qgis/issues</a>'
        )
        lbl_bugs.setOpenExternalLinks(True)
        layout.addWidget(lbl_bugs)

        layout.addWidget(self._make_separator())

        # License
        lbl_license = QLabel("Licensed under GPL v3")
        lbl_license.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(lbl_license)

        layout.addStretch()

    def _make_separator(self):
        """Create a horizontal separator."""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def _make_section_title(self, text):
        """Create a bold section title."""
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold;")
        return label

    def _get_version(self):
        """Read version from metadata.txt."""
        try:
            metadata_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'metadata.txt'
            )
            with open(metadata_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('version='):
                        return line.split('=')[1].strip()
        except Exception:
            pass
        return "1.0.0"