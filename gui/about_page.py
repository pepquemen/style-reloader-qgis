from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("About Page — Coming soon"))