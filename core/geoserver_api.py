import threading
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

import requests
from requests.auth import HTTPBasicAuth


def _seg(value):
    """URL-encode a single path segment (no slashes allowed through)."""
    return quote(str(value), safe='')


class GeoServerAPI:
    """
    Handles all communication with the GeoServer REST API.
    """

    #: Default timeout (seconds) applied to every request so the QGIS UI
    #: thread can never hang indefinitely on an unresponsive server.
    DEFAULT_TIMEOUT = 15

    def __init__(self, url, user, password, workspace=None, verify_tls=True):
        self.url = url.rstrip('/')
        self.workspace = workspace
        self.verify_tls = verify_tls
        self.auth = HTTPBasicAuth(user, password)
        # requests.Session is not safe to share across threads, so keep one
        # session per thread. Legend/style fetches run in worker threads.
        self._local = threading.local()
        self._style_layer_cache = {}  # {workspace: {style_name: layer_name}}

    def _session(self):
        """Return a per-thread requests.Session (connection reuse, safe)."""
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def set_workspace(self, workspace):
        """Set or change the active workspace at runtime."""
        self.workspace = workspace

    # ── Internal request helper ──────────────────────────────────────

    def _request(self, method, url, **kwargs):
        """
        Wrapper around the session that always enforces auth, TLS
        verification and a timeout.
        """
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)
        return self._session().request(
            method,
            url,
            auth=self.auth,
            verify=self.verify_tls,
            **kwargs,
        )

    # ── REST calls ───────────────────────────────────────────────────

    def test_connection(self):
        """Check if the connection to GeoServer is successful."""
        try:
            r = self._request(
                "GET",
                f"{self.url}/rest/workspaces.json",
                timeout=5,
            )
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False

    def layer_exists(self, layer_name):
        """Check if a layer exists in the workspace."""
        url = (
            f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
            f"/layers/{_seg(layer_name)}.json"
        )
        r = self._request("GET", url)
        return r.status_code == 200

    def style_exists(self, style_name):
        """Check if a style exists in the workspace."""
        url = (
            f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
            f"/styles/{_seg(style_name)}.json"
        )
        r = self._request("GET", url)
        return r.status_code == 200

    def upload_style(self, style_name, sld_content, content_type):
        """Create or overwrite a style in GeoServer."""
        headers = {"Content-Type": content_type}

        if self.style_exists(style_name):
            url = (
                f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
                f"/styles/{_seg(style_name)}"
            )
            r = self._request(
                "PUT", url, headers=headers,
                params={"raw": "true"},
                data=sld_content.encode('utf-8')
            )
            action = "updated (PUT)"
        else:
            url = f"{self.url}/rest/workspaces/{_seg(self.workspace)}/styles"
            r = self._request(
                "POST", url, headers=headers,
                params={"name": style_name, "raw": "true"},
                data=sld_content.encode('utf-8')
            )
            action = "created (POST)"

        return r.status_code in (200, 201), action, r

    def assign_style(self, layer_name, style_name):
        """Assign a style to a GeoServer layer."""
        url = (
            f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
            f"/layers/{_seg(layer_name)}"
        )
        # Escape all interpolated values to avoid breaking / injecting XML.
        ws = xml_escape(self.workspace or "")
        style = xml_escape(style_name)
        xml = (
            "<layer>\n"
            "  <defaultStyle>\n"
            f"    <name>{ws}:{style}</name>\n"
            f"    <workspace>{ws}</workspace>\n"
            "  </defaultStyle>\n"
            "</layer>"
        )
        r = self._request(
            "PUT", url,
            headers={"Content-Type": "application/xml"},
            data=xml.encode('utf-8')
        )
        return r.status_code in (200, 201)

    def get_workspaces(self):
        """Return the list of available workspaces."""
        url = f"{self.url}/rest/workspaces.json"
        r = self._request("GET", url)
        if r.status_code == 200:
            data = r.json()
            return [w['name'] for w in data['workspaces']['workspace']]
        return []

    def get_style_content(self, style_name):
        """Get the current SLD content of a style from GeoServer."""
        url = (
            f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
            f"/styles/{_seg(style_name)}.sld"
        )
        r = self._request("GET", url)
        if r.status_code == 200:
            return r.text
        return None

    def get_workspace_styles(self):
        """Get all styles available in the current workspace."""
        url = f"{self.url}/rest/workspaces/{_seg(self.workspace)}/styles.json"
        r = self._request("GET", url)
        if r.status_code == 200:
            data = r.json()
            styles = data.get('styles', {}).get('style', [])
            return [s['name'] for s in styles]
        return []

    def delete_style(self, style_name):
        """Delete a style from GeoServer."""
        url = (
            f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
            f"/styles/{_seg(style_name)}"
        )
        r = self._request("DELETE", url, params={"purge": "true"})
        return r.status_code == 200

    def find_layer_for_style(self, style_name):
        """
        Find the first layer in the workspace that uses the given style
        (as default or alternate). Results are cached per workspace.
        Returns '{workspace}:{layer_name}' or None.
        """
        cache = self._style_layer_cache.setdefault(self.workspace, {})
        if style_name in cache:
            return cache[style_name]

        try:
            r = self._request(
                "GET",
                f"{self.url}/rest/workspaces/{_seg(self.workspace)}/layers.json",
                timeout=10,
            )
            if r.status_code != 200:
                return None

            layer_names = [
                l['name']
                for l in r.json().get('layers', {}).get('layer', [])
            ]

            for name in layer_names:
                rd = self._request(
                    "GET",
                    f"{self.url}/rest/workspaces/{_seg(self.workspace)}"
                    f"/layers/{_seg(name)}.json",
                    timeout=10,
                )
                if rd.status_code != 200:
                    continue

                layer_data = rd.json().get('layer', {})
                default = layer_data.get('defaultStyle', {}).get('name', '')
                alternates = [
                    s.get('name', '')
                    for s in layer_data.get('styles', {}).get('style', [])
                ]
                used_styles = [default] + alternates

                # GeoServer may return 'workspace:style' or just 'style'
                for used in used_styles:
                    bare = used.split(':')[-1]
                    if bare == style_name or used == style_name:
                        qualified = f"{self.workspace}:{name}"
                        cache[style_name] = qualified
                        return qualified
        except Exception as e:
            print(f"[find_layer_for_style] exception: {e}")

        cache[style_name] = None
        return None

    def get_legend_graphic(self, style_name, sld_content):
        """
        Fetch a legend graphic from GeoServer using SLD_BODY via POST.
        Tries {workspace}:{style_name} first; falls back to searching
        for any layer that uses the style.
        Returns raw PNG bytes, or None on failure.
        """
        def _request(layer_qualified):
            r = self._request(
                "POST",
                f"{self.url}/wms",
                timeout=10,
                data={
                    "SERVICE": "WMS",
                    "VERSION": "1.1.1",
                    "REQUEST": "GetLegendGraphic",
                    "FORMAT": "image/png",
                    "LAYER": layer_qualified,
                    "SLD_BODY": sld_content,
                    "LEGEND_OPTIONS": "fontAntiAliasing:true;dpi:96",
                }
            )
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                return r.content
            return None

        try:
            # Fast path: layer with same name as style
            result = _request(f"{self.workspace}:{style_name}")
            if result:
                return result

            # Slow path: find a layer that uses this style
            layer = self.find_layer_for_style(style_name)
            if layer:
                return _request(layer)
        except Exception as e:
            print(f"[LegendGraphic] exception: {e}")

        return None
