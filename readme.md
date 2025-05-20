# QArcConnect – ArcGIS Online Integration for QGIS

**QArcConnect** is a lightweight QGIS plugin that lets you authenticate with **ArcGIS Online (AGOL)**, search for user content, preview items in a rich table, and load supported layers into your QGIS project with a double-click.

This repository contains two plugin versions:

- `qarcConnect3`: For **QGIS 3.x** using **PyQt5**
- `qarcConnect4`: For **QGIS 4.x** using **PyQt6**

---

## 🔁 Repository Structure

```
QArcConnect/
├── qarcConnect3/    # QGIS 3 plugin (PyQt5)
├── qarcConnect4/    # QGIS 4 plugin (PyQt6)
├── LICENSE
└── README.md
```

---

## ✨ Features (Both Versions)

- 🔑 **Login** with your ArcGIS Online credentials
- 🔍 **Search** AGOL content by keyword
- 🧾 **Preview results** in a structured table (title, owner, type, last modified, thumbnail)
- 🖱️ **Double-click to load** ArcGIS layers directly into QGIS
- 🌐 **Proxy support**, either auto-detected or user-defined
- 🧠 Caches user credentials and proxy configuration using `QSettings`

---

## 🧭 Usage Overview

1. Start QGIS and open the **QArcConnect** panel.
2. Enter your **AGOL username and password**.
3. Set a **proxy** if needed.
4. Use the **search field** to look up items by keyword.
5. View **search results** in a table:
   - Thumbnail icon
   - Title
   - Owner
   - Type
   - Last modified date
6. **Hover** over an item for the full AGOL URL.
7. **Double-click** a result to resolve and load the corresponding feature layer into your project.

---

## 🧰 Installation

### QGIS 3 (PyQt5)

1. Copy `qarcConnect3/` into your QGIS 3 plugin directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux/macOS:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS.
3. Activate the plugin under `Plugins > Manage and Install Plugins`.

### QGIS 4 (PyQt6)

1. Copy `qarcConnect4/` into your QGIS 4 plugin directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`
   - **Linux/macOS:** `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
2. Restart QGIS 4.
3. Enable the plugin as above.

---

## 🧑‍💻 Developer Guide

- UI is built in Qt Designer (`.ui` files) and converted via `pyuic5` or `pyuic6`
- Network logic is modularized in `network.py`
- AGOL content is accessed through REST API with token-based auth
- Preview icons are retrieved using thumbnail URLs and shown in a responsive table
- All persistent configuration is stored using `QSettings`

### Compile UI

```bash
# For QGIS 3 / PyQt5
pyuic5 -o qarcconnect3_dialog_base.py qarcconnect3_dialog_base.ui

# For QGIS 4 / PyQt6
pyuic6 -o qarcconnect4_dialog_base.py qarcconnect4_dialog_base.ui
```

---

## 🧪 Testing

- Both plugins are tested with AGOL public and private items
- QGIS Python console can be used for debugging
- `logging` output appears in the QGIS log panel

---

## 🤝 Contributing

Contributions are welcome! Please:

- Target the correct folder (`qarcConnect3/` or `qarcConnect4/`)
- Follow [QGIS plugin development guidelines](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/)
- Use clear commit messages
- Add yourself to the `AUTHORS.md` (optional)

---

## 🛡 License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---

## 📸 Screenshots

_Add screenshots for each version in future if desired._

---

## 🧠 Acknowledgements

Thanks to:
- The QGIS community for tools and guidance
- The ArcGIS REST API community for reference docs and test data
