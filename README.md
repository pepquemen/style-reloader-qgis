<p align="center">
  <img src="assets/icons/reload.png" width="110" alt="Style Reloader for GeoServer logo"/>
</p>

<h1 align="center">Style Reloader for GeoServer</h1>

<p align="center">
  A QGIS plugin to manage, sync and publish layer styles between QGIS and GeoServer over the REST API.
</p>

<p align="center">
  <img alt="QGIS" src="https://img.shields.io/badge/QGIS-3.16%2B-589632?logo=qgis&logoColor=white">
  <img alt="GeoServer" src="https://img.shields.io/badge/GeoServer-REST%20API-2E5B8B">
  <img alt="Python" src="https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-GPL%20v3-blue">
</p>

---

## Overview

**Style Reloader** turns GeoServer into an organization-wide style repository that you manage
directly from QGIS. Connect to a GeoServer instance, pick a workspace, and browse, download,
apply, or publish SLD styles without leaving the map canvas.

It is built for teams that keep their cartography in GeoServer and want a fast, repeatable way
to push QGIS symbology to the server and pull server styles back into a project.

## Features

- **Connection manager** — save multiple GeoServer connections. Credentials are stored
  **encrypted** in the QGIS Authentication Manager, never in plain text.
- **Workspace selector** — switch the active workspace at runtime and work against its styles.
- **Browse styles** — list every style in a workspace, preview its SLD and its rendered legend.
- **Apply to layers** — apply a GeoServer style to any vector layer in your current project.
- **Download SLD** — save any server style to disk as an `.sld` file.
- **Publish / reload** — export QGIS layer symbology to SLD and push it to GeoServer in bulk,
  optionally assigning the uploaded style to the matching layer.
- **Right-click reload** — reload the style of a single layer straight from the layer tree.
- **Non-blocking UI** — legend previews and publishing run in background threads, so QGIS
  stays responsive even against slow servers or large workspaces.

## Requirements

- QGIS **3.16** or newer
- Network access to a GeoServer instance with REST enabled
- A GeoServer account with permission to read (and, for publishing, write) styles

## Installation

**From a ZIP**

1. Download this repository as a ZIP.
2. In QGIS open *Plugins ▸ Manage and Install Plugins… ▸ Install from ZIP*.
3. Select the ZIP and click *Install Plugin*.

**Manual**

Copy the plugin folder into your QGIS profile plugins directory and enable it from the
Plugin Manager:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\style_reloader` |
| Linux | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/style_reloader` |
| macOS | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/style_reloader` |

## Usage

1. Open the plugin from its toolbar button.
2. In **Connections**, add a GeoServer connection (URL, user, password) and test it.
   The first time, QGIS asks you to set a master password to unlock the encrypted
   credential store.
3. Pick a **connection** and a **workspace** from the header.
4. Use **Styles** to browse server styles, preview their SLD and legend, download them,
   or apply them to your project layers.
5. Use **Publication** to select project layers and push their styles to GeoServer,
   with the option to assign each style to its layer.

> **Tip:** always connect over **HTTPS**. Over plain HTTP the credentials travel using
> HTTP Basic Auth and can be intercepted; the plugin will warn you before saving an
> insecure connection.

## Project structure

```
style_reloader/
├── core/            # GeoServer REST client, SLD export, sync logic, credentials
├── gui/             # Panels, dialogs, icons and theming
├── assets/icons/    # Plugin and UI icons
├── metadata.txt     # QGIS plugin metadata
└── style_reloader.py
```

## Security

Connection credentials are stored through the **QGIS Authentication Manager**
(`QgsAuthManager`), which keeps them encrypted in the QGIS auth database behind a master
password. The plugin only persists a reference (`authcfg`) in QGIS settings — never the
password itself. Legacy connections saved in plain text by earlier versions are migrated
automatically on first run and their plain-text values removed.

## Authors

Josep Quevedo & Pau Morell — *Natural Hazards and Emergencies Observatory, Balearic Islands.*

## License

Released under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.
