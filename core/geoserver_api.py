import requests
from requests.auth import HTTPBasicAuth


class GeoServerAPI:
    """
    Handles all communication with the GeoServer REST API.
    """

    def __init__(self, url, user, password, workspace):
        self.url = url.rstrip('/')
        self.workspace = workspace
        self.auth = HTTPBasicAuth(user, password)

    def test_connection(self):
        """Check if the connection to GeoServer is successful."""
        try:
            r = requests.get(
                f"{self.url}/rest/workspaces/{self.workspace}.json",
                auth=self.auth,
                timeout=5
            )
            return r.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def layer_exists(self, layer_name):
        """Check if a layer exists in the workspace."""
        url = f"{self.url}/rest/workspaces/{self.workspace}/layers/{layer_name}.json"
        r = requests.get(url, auth=self.auth)
        return r.status_code == 200

    def style_exists(self, style_name):
        """Check if a style exists in the workspace."""
        url = f"{self.url}/rest/workspaces/{self.workspace}/styles/{style_name}.json"
        r = requests.get(url, auth=self.auth)
        return r.status_code == 200

    def upload_style(self, style_name, sld_content, content_type):
        """Create or overwrite a style in GeoServer."""
        headers = {"Content-Type": content_type}

        if self.style_exists(style_name):
            url = f"{self.url}/rest/workspaces/{self.workspace}/styles/{style_name}"
            r = requests.put(
                url, auth=self.auth, headers=headers,
                params={"raw": "true"},
                data=sld_content.encode('utf-8')
            )
            action = "updated (PUT)"
        else:
            url = f"{self.url}/rest/workspaces/{self.workspace}/styles"
            r = requests.post(
                url, auth=self.auth, headers=headers,
                params={"name": style_name, "raw": "true"},
                data=sld_content.encode('utf-8')
            )
            action = "created (POST)"

        return r.status_code in (200, 201), action, r

    def assign_style(self, layer_name, style_name):
        """Assign a style to a GeoServer layer."""
        url = f"{self.url}/rest/workspaces/{self.workspace}/layers/{layer_name}"
        xml = f"""<layer>
  <defaultStyle>
    <name>{self.workspace}:{style_name}</name>
    <workspace>{self.workspace}</workspace>
  </defaultStyle>
</layer>"""
        r = requests.put(
            url, auth=self.auth,
            headers={"Content-Type": "application/xml"},
            data=xml.encode('utf-8')
        )
        return r.status_code in (200, 201)

    def get_workspaces(self):
        """Return the list of available workspaces."""
        url = f"{self.url}/rest/workspaces.json"
        r = requests.get(url, auth=self.auth)
        if r.status_code == 200:
            data = r.json()
            return [w['name'] for w in data['workspaces']['workspace']]
        return []