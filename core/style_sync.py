from core.geoserver_api import GeoServerAPI
from core.sld_exporter import SLDExporter


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

    # ── Local export (must run on the GUI thread) ────────────────────

    def prepare_layer(self, layer):
        """
        Export a layer's SLD locally. This touches the QGIS layer object, so
        it must be called on the main/GUI thread. Returns a job dict with the
        exported SLD, or an ERROR result dict if the export failed.
        """
        layer_name = layer.name()
        sld_content = SLDExporter.export_layer_style(layer)
        if sld_content is None:
            return {
                'status': self.ERROR,
                'layer': layer_name,
                'message': 'Could not export SLD from QGIS'
            }
        _, content_type = SLDExporter.detect_sld_version(sld_content)
        return {
            'layer': layer_name,
            'sld_content': sld_content,
            'content_type': content_type,
        }

    def prepare_layers(self, layers):
        """Export SLDs for several layers (GUI thread). Returns a job list."""
        vector_layers = [
            layer for layer in layers if layer.type() == layer.VectorLayer
        ]
        return [self.prepare_layer(layer) for layer in vector_layers]

    # ── Network sync (safe to run off the GUI thread) ────────────────

    def sync_layer(self, layer, only_existing=False, assign_style=True):
        """Sync the style of a single QGIS layer to GeoServer."""
        prepared = self.prepare_layer(layer)
        if prepared.get('status') == self.ERROR:
            return prepared
        return self._sync_prepared_one(prepared, only_existing, assign_style)

    def _sync_prepared_one(self, prepared, only_existing=False,
                           assign_style=True):
        """Upload/assign an already-exported SLD. Network only, thread-safe."""
        layer_name = prepared['layer']
        sld_content = prepared['sld_content']
        content_type = prepared['content_type']

        layer_exists = self.api.layer_exists(layer_name)
        if only_existing and not layer_exists:
            return {
                'status': self.SKIPPED,
                'layer': layer_name,
                'message': 'Layer does not exist in GeoServer'
            }

        current_sld = self.api.get_style_content(layer_name)
        if current_sld and current_sld.strip() == sld_content.strip():
            return {
                'status': self.SKIPPED,
                'layer': layer_name,
                'message': 'Style has not changed, skipping upload'
            }

        success, action, response = self.api.upload_style(
            layer_name, sld_content, content_type
        )
        if not success:
            return {
                'status': self.ERROR,
                'layer': layer_name,
                'message': f'Error uploading style: {response.status_code}'
            }

        if assign_style and layer_exists:
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

        return {
            'status': self.SUCCESS,
            'layer': layer_name,
            'message': f'Style {action} (not assigned to layer)'
        }

    def sync_prepared(self, prepared_list, only_existing=False,
                      assign_style=True):
        """
        Run the network part of a sync for a list of prepared jobs. Safe to
        call from a worker thread — it performs no local QGIS layer access.
        """
        if not prepared_list:
            return [], self._empty_summary('No layers found in project')

        if not self.api.test_connection():
            return [], self._empty_summary('No active connection to GeoServer')

        results = []
        for prepared in prepared_list:
            # Pass through export errors produced on the GUI thread.
            if prepared.get('status') == self.ERROR:
                results.append(prepared)
                continue
            results.append(
                self._sync_prepared_one(prepared, only_existing, assign_style)
            )

        return results, self._summarize(results, assign_style)

    def sync_layers(self, layers, only_existing=False, assign_style=True):
        """
        Sync styles for a list of QGIS layers (exports locally, then network).
        Kept for callers that run entirely on the GUI thread.
        """
        if not layers:
            return [], self._empty_summary('No layers found in project')

        prepared = self.prepare_layers(layers)
        if not prepared:
            return [], self._empty_summary('No vector layers selected')

        return self.sync_prepared(prepared, only_existing, assign_style)

    # ── Summaries ────────────────────────────────────────────────────

    @staticmethod
    def _empty_summary(message):
        return {
            'total': 0, 'success': 0, 'skipped': 0, 'errors': 0,
            'message': message,
        }

    def _summarize(self, results, assign_style):
        summary = {
            'total': len(results),
            'success': sum(1 for r in results if r['status'] == self.SUCCESS),
            'skipped': sum(1 for r in results if r['status'] == self.SKIPPED),
            'errors': sum(1 for r in results if r['status'] == self.ERROR),
            'message': None
        }

        if summary['errors'] == 0 and summary['skipped'] == 0:
            if assign_style:
                summary['message'] = (
                    f"All {summary['success']} layers reloaded and assigned successfully"
                )
            else:
                summary['message'] = (
                    f"All {summary['success']} layers uploaded successfully (not assigned)"
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

        return summary