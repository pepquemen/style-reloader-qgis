from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QFrame
)
from qgis.PyQt.QtCore import Qt

from core.connection_manager import ConnectionManager
from core.geoserver_api import GeoServerAPI


class ConnectionDialog(QDialog):
    """
    Dialog for adding or editing a GeoServer connection.
    """

    def __init__(self, connection=None, parent=None):
        super().__init__(parent)
        self.connection = connection  # None = Add, dict = Edit
        self.manager = ConnectionManager()
        self.is_edit = connection is not None

        self.setWindowTitle("Edit Connection" if self.is_edit else "New Connection")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._setup_ui()
        self._setup_connections()

        if self.is_edit:
            self._fill_fields()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Title ────────────────────────────────────────
        title = QLabel(
            "Edit connection" if self.is_edit else "New connection"
        )
        title.setProperty("role", "title")
        layout.addWidget(title)

        subtitle = QLabel(
            "Configure a GeoServer instance to connect to."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ── Form card ────────────────────────────────────
        form_card = QFrame()
        form_card.setObjectName("card")
        form_card.setFrameShape(QFrame.StyledPanel)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)

        # Name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        name_layout.addWidget(self._make_section_title("Name"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. GeoServer Production")
        if self.is_edit:
            self.txt_name.setEnabled(False)
        name_layout.addWidget(self.txt_name)
        form_layout.addLayout(name_layout)

        # URL
        url_layout = QVBoxLayout()
        url_layout.setSpacing(4)
        url_layout.addWidget(self._make_section_title("URL"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText(
            "e.g. https://geoserver.example.com/geoserver"
        )
        url_layout.addWidget(self.txt_url)
        form_layout.addLayout(url_layout)

        # User
        user_layout = QVBoxLayout()
        user_layout.setSpacing(4)
        user_layout.addWidget(self._make_section_title("User"))
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("admin")
        user_layout.addWidget(self.txt_user)
        form_layout.addLayout(user_layout)

        # Password
        pwd_layout = QVBoxLayout()
        pwd_layout.setSpacing(4)
        pwd_layout.addWidget(self._make_section_title("Password"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("••••••••")
        pwd_layout.addWidget(self.txt_password)
        form_layout.addLayout(pwd_layout)

        layout.addWidget(form_card)

        # ── Test connection row ──────────────────────────
        test_row = QHBoxLayout()
        test_row.setSpacing(10)

        self.btn_test = QPushButton("Test connection")
        test_row.addWidget(self.btn_test)

        self.lbl_test_status = QLabel("● Not tested")
        self.lbl_test_status.setProperty("role", "subtitle")
        test_row.addWidget(self.lbl_test_status)
        test_row.addStretch()

        layout.addLayout(test_row)

        layout.addStretch()

        # ── Action buttons ──────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.btn_save.setProperty("primary", "true")

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)

        layout.addLayout(btn_row)

    def _setup_connections(self):
        self.btn_test.clicked.connect(self._on_test)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

    def _make_section_title(self, text):
        """Create a small uppercase section label."""
        label = QLabel(text)
        label.setProperty("role", "section")
        return label

    def _fill_fields(self):
        """Fill fields with existing connection data (Edit mode)."""
        self.txt_name.setText(self.connection.get('name', ''))
        self.txt_url.setText(self.connection.get('url', ''))
        self.txt_user.setText(self.connection.get('user', ''))
        self.txt_password.setText(self.connection.get('password', ''))

    def _set_test_status(self, text, color=None):
        """Helper to update the test status label."""
        self.lbl_test_status.setText(text)
        if color:
            self.lbl_test_status.setStyleSheet(
                f"color: {color}; background: transparent; border: none;"
            )
        else:
            self.lbl_test_status.setStyleSheet(
                "background: transparent; border: none;"
            )

    def _on_test(self):
        """Test the connection with current field values."""
        url = self.txt_url.text().strip()
        user = self.txt_user.text().strip()
        password = self.txt_password.text().strip()

        if not url or not user or not password:
            self._set_test_status("● Fill all fields first", "#f59e0b")
            return

        self._set_test_status("● Testing...")

        try:
            api = GeoServerAPI(url=url, user=user, password=password)
            if api.test_connection():
                self._set_test_status("● Connected", "#10b981")
            else:
                self._set_test_status("● Connection failed", "#ef4444")
        except Exception as e:
            self._set_test_status(f"● Error: {str(e)[:30]}", "#ef4444")

    def _on_save(self):
        """Save the connection and close the dialog."""
        name = self.txt_name.text().strip()
        url = self.txt_url.text().strip()
        user = self.txt_user.text().strip()
        password = self.txt_password.text().strip()

        # Validation
        if not name or not url or not user or not password:
            self._set_test_status("● Fill all fields first", "#f59e0b")
            return

        # Check duplicate name (only on Add mode)
        if not self.is_edit and self.manager.connection_exists(name):
            self._set_test_status("● Name already exists", "#f59e0b")
            return

        self.manager.save_connection(name, url, user, password)
        self.accept()
