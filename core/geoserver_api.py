import threading
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth


def _seg(value):
    """URL-encode a single path segment (no slashes allowed through)."""
    return quote(str(value), safe='')


def xml_escape(value):
    """Escape &, < and > for safe inclusion in XML text (no XML parsing)."""
    return (
        str(value)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


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
        self._sample_layer_cache = {}  # {workspace: 'ws:layer' or None}
        self._global_sample_layer = False  # False = not fetched yet

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

    def _sample_layer_of(self, workspace):
        """
        Return '{workspace}:{layer}' for any published layer in the given
        workspace, or None. Cached per workspace (one request at most).
        """
        if workspace in self._sample_layer_cache:
            return self._sample_layer_cache[workspace]

        sample = None
        try:
            r = self._request(
                "GET",
                f"{self.url}/rest/workspaces/{_seg(workspace)}/layers.json",
                timeout=10,
            )
            if r.status_code == 200:
                layers = r.json().get('layers', {}).get('layer', [])
                if layers:
                    sample = f"{workspace}:{layers[0]['name']}"
        except Exception as e:
            print(f"[_sample_layer_of] exception: {e}")

        self._sample_layer_cache[workspace] = sample
        return sample

    def _get_sample_layer(self):
        """
        Return a '{workspace}:{layer}' to use only as a rendering context for
        GetLegendGraphic (the legend itself is drawn from SLD_BODY, so the
        layer's workspace/geometry does not affect the result).

        Prefers a layer in the active workspace; if it has none (e.g. a
        styles-only workspace), falls back to any published layer in any
        workspace. Both lookups are cached, so after the first legend it costs
        zero extra requests — no per-layer scanning.
        """
        # 1) A layer in the active workspace (best locality).
        sample = self._sample_layer_of(self.workspace)
        if sample:
            return sample

        # 2) Any layer in any workspace, resolved once and cached per session.
        if self._global_sample_layer is not False:
            return self._global_sample_layer

        result = None
        try:
            r = self._request(
                "GET", f"{self.url}/rest/workspaces.json", timeout=10
            )
            if r.status_code == 200:
                workspaces = r.json().get('workspaces', {}).get('workspace', [])
                for w in workspaces:
                    candidate = self._sample_layer_of(w['name'])
                    if candidate:
                        result = candidate
                        break
        except Exception as e:
            print(f"[_get_sample_layer:global] exception: {e}")

        self._global_sample_layer = result
        return result

    def get_legend_graphic(self, style_name, sld_content):
        """
        Fetch a legend graphic from GeoServer using SLD_BODY via POST.

        GeoServer's GetLegendGraphic requires a LAYER, but the legend is drawn
        from SLD_BODY, so the layer only provides a rendering context. We try a
        layer named like the style first (most faithful); if there is none, we
        fall back to any published layer in the workspace (cached). This lets
        legends work for styles not assigned to any layer, without scanning
        every layer in the workspace.

        Returns raw PNG bytes, or None on failure.
        """
        def _legend(layer_qualified):
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
            # Fast path: a layer named like the style (best rendering context).
            result = _legend(f"{self.workspace}:{style_name}")
            if result:
                return result

            # Fallback: any published layer in the workspace (cached, 1 request).
            sample = self._get_sample_layer()
            if sample:
                return _legend(sample)
        except Exception as e:
            print(f"[LegendGraphic] exception: {e}")

        return None
