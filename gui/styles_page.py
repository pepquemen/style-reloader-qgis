from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel


class StylesPage(QWidget):
    def __init__(self, api=None):
        super().__init__()
        self.api = api
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Styles Page — Coming soon"))

    def set_api(self, api):
        self.api = api