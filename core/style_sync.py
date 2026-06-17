from .geoserver_api import GeoServerAPI
from .sld_exporter import SLDExporter


class StyleSync:
    """
    Orchestrates the synchronization of QGIS layer styles to GeoServer.
    """

    # Result constants
    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"

    def __init__(self, api: GeoServerAPI):
        self.api = api
        self.exporter = SLDExporter()

    def sync_layer(self, layer, only_existing=False):
        """
        Sync the style of a single QGIS layer to GeoServer.
        Returns a dict with the result:
        {
            'status': SUCCESS | SKIPPED | ERROR,
            'layer': layer_name,
            'message': description
        }
        """
        layer_name = layer.name()

        # Check if layer exists in GeoServer
        layer_exists = self.api.layer_exists(layer_name)

        if only_existing and not layer_exists:
            return {
                'status': self.SKIPPED,
                'layer': layer_name,
                'message': 'Layer does not exist in GeoServer'
            }

        # Export SLD
        sld_content = SLDExporter.export_layer_style(layer)
        if sld_content is None:
            return {
                'status': self.ERROR,
                'layer': layer_name,
                'message': 'Could not export SLD from QGIS'
            }

        # Detect SLD version
        version, content_type = SLDExporter.detect_sld_version(sld_content)

        # Check if style has changed
        current_sld = self.api.get_style_content(layer_name)
        if current_sld and current_sld.strip() == sld_content.strip():
            return {
                'status': self.SKIPPED,
                'layer': layer_name,
                'message': 'Style has not changed, skipping upload'
            }

        # Upload style
        success, action, response = self.api.upload_style(
            layer_name, sld_content, content_type
        )
        if not success:
            return {
                'status': self.ERROR,
                'layer': layer_name,
                'message': f'Error uploading style: {response.status_code}'
            }

        # Assign style to layer
        if layer_exists:
            assigned = self.api.assign_style(layer_name, layer_name)
            if not assigned:
                return {
                    'status': self.ERROR,
                    'layer': layer_name,
                    'message': 'Style uploaded but could not be assigned'
                }

        return {
            'status': self.SUCCESS,
            'layer': layer_name,
            'message': f'Style {action} and assigned successfully'
        }

    def sync_layers(self, layers, only_existing=False):
        """
        Sync styles for a list of QGIS layers.
        Returns a list of result dicts and a summary.
        """
        # No layers in project
        if not layers:
            return [], {
                'total': 0,
                'success': 0,
                'skipped': 0,
                'errors': 0,
                'message': 'No layers found in project'
            }

        # No vector layers selected
        vector_layers = [l for l in layers if l.type() == l.VectorLayer]
        if not vector_layers:
            return [], {
                'total': 0,
                'success': 0,
                'skipped': 0,
                'errors': 0,
                'message': 'No vector layers selected'
            }

        # No active connection to GeoServer
        if not self.api.test_connection():
            return [], {
                'total': 0,
                'success': 0,
                'skipped': 0,
                'errors': 0,
                'message': 'No active connection to GeoServer'
            }

        results = []
        for layer in vector_layers:
            result = self.sync_layer(layer, only_existing)
            results.append(result)

        summary = {
            'total': len(results),
            'success': sum(1 for r in results if r['status'] == self.SUCCESS),
            'skipped': sum(1 for r in results if r['status'] == self.SKIPPED),
            'errors': sum(1 for r in results if r['status'] == self.ERROR),
            'message': None
        }

        # Automatic summary message
        if summary['errors'] == 0 and summary['skipped'] == 0:
            summary['message'] = (
                f"All {summary['success']} layers reloaded successfully"
            )
        elif summary['errors'] == 0:
            summary['message'] = (
                f"{summary['success']} layers reloaded, "
                f"{summary['skipped']} skipped (no changes)"
            )
        else:
            summary['message'] = (
                f"{summary['success']} layers reloaded successfully, "
                f"{summary['errors']} errors, "
                f"{summary['skipped']} skipped"
            )

        return results, summary