from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy
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
        self.setMinimumWidth(380)

        self._setup_ui()
        self._setup_connections()

        if self.is_edit:
            self._fill_fields()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Name
        layout.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. GeoServer Production")
        if self.is_edit:
            self.txt_name.setEnabled(False)
        layout.addWidget(self.txt_name)

        # URL
        layout.addWidget(QLabel("URL:"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("e.g. https://geoserver.example.com/geoserver")
        layout.addWidget(self.txt_url)

        # User
        layout.addWidget(QLabel("User:"))
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("admin")
        layout.addWidget(self.txt_user)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("••••••••")
        layout.addWidget(self.txt_password)

        # Test connection
        test_row = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.lbl_test_status = QLabel("● Not tested")
        self.lbl_test_status.setStyleSheet("color: gray;")
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.lbl_test_status)
        test_row.addStretch()
        layout.addLayout(test_row)

        layout.addStretch()

        # Cancel / Save buttons
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #00A8D6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #0088B0; }
        """)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def _setup_connections(self):
        self.btn_test.clicked.connect(self._on_test)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

    def _fill_fields(self):
        """Fill fields with existing connection data (Edit mode)."""
        self.txt_name.setText(self.connection.get('name', ''))
        self.txt_url.setText(self.connection.get('url', ''))
        self.txt_user.setText(self.connection.get('user', ''))
        self.txt_password.setText(self.connection.get('password', ''))

    def _on_test(self):
        """Test the connection with current field values."""
        url = self.txt_url.text().strip()
        user = self.txt_user.text().strip()
        password = self.txt_password.text().strip()

        if not url or not user or not password:
            self.lbl_test_status.setText("● Fill all fields first")
            self.lbl_test_status.setStyleSheet("color: orange;")
            return

        self.lbl_test_status.setText("● Testing...")
        self.lbl_test_status.setStyleSheet("color: gray;")

        try:
            api = GeoServerAPI(url=url, user=user, password=password)
            if api.test_connection():
                self.lbl_test_status.setText("● Connected")
                self.lbl_test_status.setStyleSheet("color: green;")
            else:
                self.lbl_test_status.setText("● Connection failed")
                self.lbl_test_status.setStyleSheet("color: red;")
        except Exception as e:
            self.lbl_test_status.setText(f"● Error: {str(e)[:30]}")
            self.lbl_test_status.setStyleSheet("color: red;")

    def _on_save(self):
        """Save the connection and close the dialog."""
        name = self.txt_name.text().strip()
        url = self.txt_url.text().strip()
        user = self.txt_user.text().strip()
        password = self.txt_password.text().strip()

        # Validation
        if not name or not url or not user or not password:
            self.lbl_test_status.setText("● Fill all fields first")
            self.lbl_test_status.setStyleSheet("color: orange;")
            return

        # Check duplicate name (only on Add mode)
        if not self.is_edit and self.manager.connection_exists(name):
            self.lbl_test_status.setText("● Name already exists")
            self.lbl_test_status.setStyleSheet("color: orange;")
            return

        self.manager.save_connection(name, url, user, password)
        self.accept()