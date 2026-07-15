from qgis.core import (
    QgsSettings,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsMessageLog,
    Qgis,
)


class ConnectionManager:
    """
    Handles saving and loading GeoServer connection credentials.

    The connection URL is stored in QGIS settings (QgsSettings), but the
    username and password are stored **encrypted** in the QGIS Authentication
    Manager (QgsAuthManager). QgsSettings only keeps a reference (``authcfg``
    id) to the encrypted credentials, never the password itself.

    Legacy connections that were previously saved with the password in plain
    text are transparently migrated to QgsAuthManager on first access and the
    plain-text values are removed.
    """

    SETTINGS_KEY = "style_reloader/connections"
    LOG_TAG = "Style Reloader"

    def __init__(self):
        self.settings = QgsSettings()
        self._migrate_plaintext_connections()

    # ── Auth manager helpers ─────────────────────────────────────────

    @staticmethod
    def _auth_manager():
        return QgsApplication.authManager()

    def _ensure_master_password(self):
        """
        Make sure the QGIS auth DB master password is available.
        QGIS will prompt the user interactively the first time.
        Returns True if the auth system is usable.
        """
        auth_mgr = self._auth_manager()
        if auth_mgr is None:
            return False
        try:
            if auth_mgr.masterPasswordIsSet():
                return True
            # Triggers the QGIS master-password dialog if not set yet.
            return auth_mgr.setMasterPassword(True)
        except Exception as e:  # pragma: no cover - defensive
            self._log(f"Could not initialise master password: {e}")
            return False

    def _store_credentials(self, name, user, password, authcfg=None):
        """
        Create or update an encrypted Basic-auth config in QgsAuthManager.
        Returns the authcfg id, or None on failure.
        """
        if not self._ensure_master_password():
            self._log(
                "Auth manager master password unavailable; cannot store "
                "credentials securely.",
                critical=True,
            )
            return None

        auth_mgr = self._auth_manager()
        config = QgsAuthMethodConfig()
        config.setName(f"style_reloader/{name}")
        config.setMethod("Basic")
        config.setConfig("username", user or "")
        config.setConfig("password", password or "")

        # Reuse the existing id when editing so we don't leak stale configs.
        if authcfg:
            config.setId(authcfg)

        stored = auth_mgr.storeAuthenticationConfig(config)
        # Depending on the QGIS version this returns either a bool or a
        # (bool, config) tuple. Normalise both.
        ok = stored[0] if isinstance(stored, tuple) else stored
        if not ok:
            self._log("storeAuthenticationConfig failed.", critical=True)
            return None

        return config.id()

    def _load_credentials(self, authcfg):
        """Resolve (user, password) from an authcfg id. Returns a tuple."""
        if not authcfg or not self._ensure_master_password():
            return "", ""

        auth_mgr = self._auth_manager()
        config = QgsAuthMethodConfig()
        # full=True decrypts the stored secrets.
        auth_mgr.loadAuthenticationConfig(authcfg, config, True)
        return config.config("username", ""), config.config("password", "")

    def _remove_credentials(self, authcfg):
        if not authcfg:
            return
        try:
            self._auth_manager().removeAuthenticationConfig(authcfg)
        except Exception as e:  # pragma: no cover - defensive
            self._log(f"Could not remove auth config {authcfg}: {e}")

    # ── Public API (unchanged signatures) ────────────────────────────

    def save_connection(self, name, url, user, password):
        """
        Save a GeoServer connection. URL is stored in QgsSettings; the
        credentials are stored encrypted in QgsAuthManager.
        """
        # Reuse existing authcfg when editing an existing connection.
        existing_authcfg = self.settings.value(
            f"{self.SETTINGS_KEY}/{name}/authcfg", None
        )
        authcfg = self._store_credentials(
            name, user, password, authcfg=existing_authcfg
        )

        self.settings.beginGroup(f"{self.SETTINGS_KEY}/{name}")
        self.settings.setValue("url", url)
        if authcfg:
            self.settings.setValue("authcfg", authcfg)
        # Never persist plain-text credentials.
        self.settings.remove("user")
        self.settings.remove("password")
        self.settings.endGroup()

        return authcfg is not None

    def load_connection(self, name):
        """
        Load a GeoServer connection. Returns a dict with the connection data
        (including the decrypted credentials) or None if not found.
        """
        self.settings.beginGroup(f"{self.SETTINGS_KEY}/{name}")
        url = self.settings.value("url")
        authcfg = self.settings.value("authcfg")
        self.settings.endGroup()

        if not url:
            return None

        user, password = self._load_credentials(authcfg)

        return {
            'name': name,
            'url': url,
            'user': user,
            'password': password,
            'authcfg': authcfg,
        }

    def get_all_connections(self):
        """Return a list of all saved connection names."""
        self.settings.beginGroup(self.SETTINGS_KEY)
        names = self.settings.childGroups()
        self.settings.endGroup()
        return names

    def delete_connection(self, name):
        """Delete a saved connection and its encrypted credentials."""
        authcfg = self.settings.value(
            f"{self.SETTINGS_KEY}/{name}/authcfg", None
        )
        self._remove_credentials(authcfg)

        self.settings.beginGroup(self.SETTINGS_KEY)
        self.settings.remove(name)
        self.settings.endGroup()

    def connection_exists(self, name):
        """Check if a connection with the given name already exists."""
        return name in self.get_all_connections()

    # ── Migration ────────────────────────────────────────────────────

    def _migrate_plaintext_connections(self):
        """
        One-off migration: move any legacy plain-text passwords into
        QgsAuthManager and strip the plain-text values from QgsSettings.
        """
        for name in self.get_all_connections():
            group = f"{self.SETTINGS_KEY}/{name}"
            self.settings.beginGroup(group)
            plain_user = self.settings.value("user")
            plain_password = self.settings.value("password")
            has_authcfg = bool(self.settings.value("authcfg"))
            self.settings.endGroup()

            # Nothing to migrate if there is no plain-text password.
            if has_authcfg and plain_password is None:
                continue
            if plain_password is None and plain_user is None:
                continue

            authcfg = self._store_credentials(
                name, plain_user or "", plain_password or ""
            )
            if not authcfg:
                # Leave the plain-text values in place rather than losing the
                # credential; will retry next time the auth DB is unlocked.
                self._log(
                    f"Deferred migration of connection '{name}' "
                    "(auth manager unavailable).",
                )
                continue

            self.settings.beginGroup(group)
            self.settings.setValue("authcfg", authcfg)
            self.settings.remove("user")
            self.settings.remove("password")
            self.settings.endGroup()
            self._log(
                f"Connection '{name}' migrated to encrypted credential store."
            )

    # ── Logging ──────────────────────────────────────────────────────

    def _log(self, message, critical=False):
        QgsMessageLog.logMessage(
            message,
            self.LOG_TAG,
            level=Qgis.Critical if critical else Qgis.Info,
        )
