from qgis.core import QgsSettings


class ConnectionManager:
    """
    Handles saving and loading GeoServer connection credentials
    using QGIS built-in settings system (QgsSettings).
    """

    SETTINGS_KEY = "style_reloader/connections"

    def __init__(self):
        self.settings = QgsSettings()

    def save_connection(self, name, url, user, password, workspace):
        """
        Save a GeoServer connection to QGIS settings.
        """
        self.settings.beginGroup(f"{self.SETTINGS_KEY}/{name}")
        self.settings.setValue("url", url)
        self.settings.setValue("user", user)
        self.settings.setValue("password", password)
        self.settings.setValue("workspace", workspace)
        self.settings.endGroup()

    def load_connection(self, name):
        """
        Load a GeoServer connection from QGIS settings.
        Returns a dict with the connection data or None if not found.
        """
        self.settings.beginGroup(f"{self.SETTINGS_KEY}/{name}")
        url = self.settings.value("url")
        self.settings.endGroup()

        if not url:
            return None

        self.settings.beginGroup(f"{self.SETTINGS_KEY}/{name}")
        connection = {
            'name': name,
            'url': self.settings.value("url"),
            'user': self.settings.value("user"),
            'password': self.settings.value("password"),
            'workspace': self.settings.value("workspace")
        }
        self.settings.endGroup()
        return connection

    def get_all_connections(self):
        """
        Return a list of all saved connection names.
        """
        self.settings.beginGroup(self.SETTINGS_KEY)
        names = self.settings.childGroups()
        self.settings.endGroup()
        return names

    def delete_connection(self, name):
        """
        Delete a saved connection from QGIS settings.
        """
        self.settings.beginGroup(self.SETTINGS_KEY)
        self.settings.remove(name)
        self.settings.endGroup()

    def connection_exists(self, name):
        """
        Check if a connection with the given name already exists.
        """
        return name in self.get_all_connections()