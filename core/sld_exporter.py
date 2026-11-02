import os
import re
import tempfile

try:
    from qgis.core import QgsMessageLog, Qgis
except ImportError:  # pragma: no cover - outside QGIS
    QgsMessageLog = Qgis = None

LOG_TAG = "Style Reloader"


def log_message(text, level="warning"):
    """Write to QGIS's Log Messages panel (tab 'Style Reloader')."""
    if QgsMessageLog is None:
        print(f"[{LOG_TAG}] {text}")
        return
    lvl = {"info": Qgis.Info, "warning": Qgis.Warning,
           "critical": Qgis.Critical}.get(level, Qgis.Warning)
    QgsMessageLog.logMessage(text, LOG_TAG, lvl)


class SLDExporter:
    """
    Handles the export of QGIS layer styles to SLD format.
    """

    @staticmethod
    def detect_sld_version(sld_content):
        """
        Detect the SLD version by analyzing the content.
        Returns a tuple (version, content_type).
        """
        m = re.search(
            r'StyledLayerDescriptor[^>]*version\s*=\s*["\']([\d.]+)["\']',
            sld_content
        )
        version = m.group(1) if m else None

        # If no explicit version, deduce from SE namespace
        if version is None:
            if 'se.opengis.net/se' in sld_content or 'xmlns:se' in sld_content:
                version = '1.1.0'
            else:
                version = '1.0.0'

        if version.startswith('1.1'):
            content_type = "application/vnd.ogc.se+xml"
        else:
            content_type = "application/vnd.ogc.sld+xml"

        return version, content_type

    # Detailed reason of the last failed export (read by StyleSync).
    last_error = None

    @staticmethod
    def export_layer_style(layer):
        """
        Export the style of a QGIS layer as an SLD string.
        Returns the SLD content as string, or None if export fails; in that
        case SLDExporter.last_error holds QGIS's own explanation.
        """
        SLDExporter.last_error = None
        tmp = tempfile.NamedTemporaryFile(
            suffix='.sld', delete=False, mode='w'
        )
        tmp.close()

        def _fail(reason):
            SLDExporter.last_error = reason
            log_message(f"{layer.name()}: SLD export failed — {reason}", "warning")
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            return None

        try:
            result = layer.saveSldStyle(tmp.name)
        except Exception as e:
            return _fail(f"{type(e).__name__}: {e}")

        # PyQGIS returns (message, ok) — keep QGIS's message when it fails.
        ok, qgis_msg = True, ""
        if isinstance(result, tuple) and len(result) == 2:
            a, b = result
            if isinstance(a, bool):
                ok, qgis_msg = a, str(b or "")
            else:
                qgis_msg, ok = str(a or ""), bool(b)

        if not ok:
            return _fail(qgis_msg or "QGIS reported a failure without details")

        if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
            return _fail(
                (qgis_msg + " — " if qgis_msg else "")
                + "QGIS wrote an empty SLD. Some symbology or label settings "
                  "can't be expressed in SLD; try Layer Properties → Style → "
                  "Save Style → As SLD Style File to see which one."
            )

        with open(tmp.name, 'r', encoding='utf-8') as f:
            sld = f.read()

        os.unlink(tmp.name)

        # Raster layers: QGIS only exports some renderers (single band
        # pseudocolor/gray, paletted, ...). Without a RasterSymbolizer the
        # SLD would publish an empty style, so treat it as a failed export.
        if layer.type() == layer.RasterLayer and 'RasterSymbolizer' not in sld:
            SLDExporter.last_error = (
                "this raster renderer can't be exported to SLD (use single band "
                "pseudocolor, single band gray or paletted)")
            log_message(f"{layer.name()}: {SLDExporter.last_error}", "warning")
            return None
        return sld

    @staticmethod
    def apply_sld_to_layer(layer, sld_content):
        """
        Apply an SLD string to a QGIS layer.
        Returns (success: bool, error_msg: str).
        """
        tmp = tempfile.NamedTemporaryFile(
            suffix='.sld', delete=False, mode='w', encoding='utf-8'
        )
        tmp.write(sld_content)
        tmp.close()

        try:
            success, error_msg = layer.loadSldStyle(tmp.name)
        finally:
            os.unlink(tmp.name)

        if success:
            layer.triggerRepaint()

        return success, error_msg