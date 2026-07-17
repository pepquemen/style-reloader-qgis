from qgis.core import QgsProject, QgsMapLayer


class LayerMatcher:
    """
    Handles matching between QGIS layers and GeoServer layers.
    Manages name mappings when local and remote names differ.
    """

    def __init__(self, api):
        self.api = api
        self.custom_mappings = {}  # {'local_name': 'geoserver_name'}

    def get_project_vector_layers(self):
        """
        Return all vector layers loaded in the current QGIS project.
        """
        layers = QgsProject.instance().mapLayers().values()
        return [
            layer for layer in layers
            if layer.type() == QgsMapLayer.VectorLayer
        ]

    def get_geoserver_name(self, layer_name):
        """
        Get the GeoServer name for a given QGIS layer name.
        Uses custom mapping if defined, otherwise uses the same name.
        """
        return self.custom_mappings.get(layer_name, layer_name)

    def add_custom_mapping(self, local_name, geoserver_name):
        """
        Add a custom name mapping between a QGIS layer and a GeoServer layer.
        """
        self.custom_mappings[local_name] = geoserver_name

    def remove_custom_mapping(self, local_name):
        """
        Remove a custom name mapping.
        """
        if local_name in self.custom_mappings:
            del self.custom_mappings[local_name]

    def match_layers(self, layers=None):
        """
        Match QGIS layers with GeoServer layers.
        Returns a list of dicts with match status per layer:
        {
            'qgis_name': local layer name,
            'geoserver_name': remote layer name,
            'exists_in_geoserver': bool,
            'has_custom_mapping': bool
        }
        """
        if layers is None:
            layers = self.get_project_vector_layers()

        results = []
        for layer in layers:
            qgis_name = layer.name()
            geoserver_name = self.get_geoserver_name(qgis_name)
            exists = self.api.layer_exists(geoserver_name)

            results.append({
                'layer': layer,
                'qgis_name': qgis_name,
                'geoserver_name': geoserver_name,
                'exists_in_geoserver': exists,
                'has_custom_mapping': qgis_name in self.custom_mappings
            })

        return results

    def get_unmatched_layers(self, layers=None):
        """
        Return only layers that have no match in GeoServer.
        Useful to warn the user before syncing.
        """
        matches = self.match_layers(layers)
        return [m for m in matches if not m['exists_in_geoserver']]

    def get_matched_layers(self, layers=None):
        """
        Return only layers that have a match in GeoServer.
        """
        matches = self.match_layers(layers)
        return [m for m in matches if m['exists_in_geoserver']]