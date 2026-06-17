import sys
import os

# Add plugin path to sys.path
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt

from gui.main_panel import MainPanel


class StyleReloader:
    """
    Main plugin class.
    Initializes the GUI and connects it to QGIS.
    """

    def __init__(self, iface):
        self.iface = iface
        self.main_panel = None
        self.action = None

    def initGui(self):
        """Create the plugin UI elements."""

        # ── TOOLBAR ACTION ────────────────────────────────
        icon_path = os.path.join(
            plugin_dir,
            'resources', 'icons', 'reload.png'
        )
        self.action = QAction(
            QIcon(icon_path),
            "Style Reloader for GeoServer",
            self.iface.mainWindow()
        )
        self.action.setToolTip("Reload styles to GeoServer")
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addToolBarIcon(self.action)

        # ── MAIN PANEL ────────────────────────────────────
        self.main_panel = MainPanel(self.iface)
        self.iface.addDockWidget(
            Qt.LeftDockWidgetArea,
            self.main_panel
        )
        self.main_panel.hide()

        # ── RIGHT CLICK CONTEXT MENU ──────────────────────
        self.iface.layerTreeView().contextMenuAboutToShow.connect(
            self._add_context_menu
        )

    def toggle_panel(self):
        """Show or hide the main panel."""
        if self.main_panel.isVisible():
            self.main_panel.hide()
        else:
            self.main_panel.show()
            self.main_panel.reload_page.load_layers()

    def _add_context_menu(self, menu):
        """Add reload style option to layer right-click menu."""
        layer = self.iface.activeLayer()
        if not layer:
            return

        menu.addSeparator()

        reload_action = QAction(
            "Reload Style on GeoServer",
            menu
        )
        reload_action.triggered.connect(
            lambda: self._reload_single_layer(layer)
        )
        menu.addAction(reload_action)

    def _reload_single_layer(self, layer):
        """Reload style for a single layer from context menu."""
        from core.style_sync import StyleSync

        if not self.main_panel.api:
            self.iface.messageBar().pushWarning(
                "Style Reloader",
                "No active connection to GeoServer"
            )
            return

        sync = StyleSync(self.main_panel.api)
        result = sync.sync_layer(
            layer,
            assign_style=self.main_panel.reload_page.chk_assign_style.isChecked()
        )

        if result['status'] == StyleSync.SUCCESS:
            self.iface.messageBar().pushSuccess(
                "Style Reloader",
                f"{result['layer']}: {result['message']}"
            )
        elif result['status'] == StyleSync.SKIPPED:
            self.iface.messageBar().pushInfo(
                "Style Reloader",
                f"{result['layer']}: {result['message']}"
            )
        else:
            self.iface.messageBar().pushCritical(
                "Style Reloader",
                f"{result['layer']}: {result['message']}"
            )

    def unload(self):
        """Remove the plugin UI elements."""
        self.iface.removeToolBarIcon(self.action)
        self.iface.layerTreeView().contextMenuAboutToShow.disconnect(
            self._add_context_menu
        )
        self.iface.removeDockWidget(self.main_panel)
        self.main_panel.deleteLater()
        self.main_panel = None