import os
import re
import tempfile


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

    @staticmethod
    def export_layer_style(layer):
        """
        Export the style of a QGIS layer as an SLD string.
        Returns the SLD content as string, or None if export fails.
        """
        tmp = tempfile.NamedTemporaryFile(
            suffix='.sld', delete=False, mode='w'
        )
        tmp.close()

        try:
            layer.saveSldStyle(tmp.name)
        except Exception as e:
            print(f"[SLDExporter] Error exporting SLD: {e}")
            return None

        if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
            return None

        with open(tmp.name, 'r', encoding='utf-8') as f:
            sld = f.read()

        os.unlink(tmp.name)
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