from qgis.PyQt.QtWidgets import (
    QListWidgetItem,
    QDialog,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
    QProgressDialog,
    QApplication
)
from urllib.parse import urlparse, parse_qs
from PyQt5.QtCore import (
    pyqtSignal,
    QSize,
    Qt,
    QAbstractTableModel,
    QModelIndex,
)
from PyQt5.QtGui import QStandardItemModel
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtCore import QSettings
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsAuthMethodConfig,
    QgsApplication,
    QgsDataSourceUri
)
from .qarcconnect3_dialog_base import Ui_QarcConnect3Dialog
import base64
from qarcconnect3 import network


class LayerSelectionDialog(QDialog):
    layerSelected = pyqtSignal(int)  

    def __init__(self, layers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select a Layer")
        self.resize(400, 300)

        self.layers = layers
        self.list_widget = QListWidget()
        for layer in layers:
            name = layer.get("name", "Unnamed")
            layer_id = layer.get("id", -1)
            self.list_widget.addItem(f"{layer_id}: {name}")

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clickedsingle)

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def on_item_double_clickedsingle(self, item):
        layer_id = int(item.text().split(":")[0])
        self.layerSelected.emit(layer_id)
        self.accept()  # close dialog after selection


class AgolItemsModel(QAbstractTableModel):
    def __init__(self, items_data, parent=None):
        super().__init__(parent)
        self.items = items_data
        self.icons = [QIcon()] * len(items_data)  # placeholder for thumbnails

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        # Removed URL column, so now 5 columns total:
        # Title, Thumbnail, Owner, Type, Date
        return 5

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            headers = ["Title", "Thumbnail", "Owner", "Type", "Date"]
            if 0 <= section < len(headers):
                return headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        item = self.items[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.get("title", "")
            elif col == 2:
                return item.get("owner", "")
            elif col == 3:
                return item.get("type", "")
            elif col == 4:
                return item.get("date", "")

        if role == Qt.ItemDataRole.DecorationRole:
            # Thumbnail icon in column 1
            if col == 1:
                return self.icons[row]

        if role == Qt.ItemDataRole.ToolTipRole:
            # Show URL tooltip on Title column
            if col == 0:
                return item.get("url", "")

        return None

    def setIcon(self, row, icon):
        self.icons[row] = icon
        # Notify view the data changed for icon cell (col 1)
        self.dataChanged.emit(self.index(row, 1), self.index(row, 1), [Qt.ItemDataRole.DecorationRole])

class QarcConnect3Dialog(QDialog, Ui_QarcConnect3Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.loginButton.clicked.connect(self.get_own_content)
        self.pushButtonSearch.clicked.connect(self.search_agol_content)
        self.SearchitemTableView.setIconSize(QSize(64, 64))
        self.UserSearchitemTableView.setIconSize(QSize(64, 64))
        self.SearchitemTableView.setWordWrap(True)
        self.UserSearchitemTableView.setWordWrap(True)
        # self.itemListWidget.setIconSize(QSize(64, 64))  # or 128,128 for bigger
        # self.itemListWidget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.saveCredsPushButton.clicked.connect(self.save_credentials)
        # self.itemListWidget.itemDoubleClicked.connect(
        #    self.on_item_double_clicked)
        self.SearchitemTableView.doubleClicked.connect(self.on_item_double_clicked)
        #self.SearchitemListWidget.itemDoubleClicked.connect(
        #    self.on_item_double_clicked)
        self.UserSearchitemTableView.doubleClicked.connect(self.on_item_double_clicked)

        self.find_auth_config_by_name()

    def save_credentials(self):
        username = self.usernameLineEdit.text()
        password = self.passwordLineEdit.text()
        encoded = base64.b64encode(password.encode("utf-8")).decode("utf-8")
        QSettings().setValue("QarcConnect3/hex", encoded)
        QSettings().setValue("QarcConnect3/user", username)

    def find_auth_config_by_name(self):
        encoded = QSettings().value("QarcConnect3/hex", None)
        user = QSettings().value("QarcConnect3/user", None)
        if encoded is None:
            print("Encoded password not found in settings.")
        try:
            decoded = base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
            self.passwordLineEdit.setText(decoded)
            self.usernameLineEdit.setText(user)
        except Exception as e:
            print("Decoding error:", e)

    def get_own_content(self):
        username = self.usernameLineEdit.text()
        password = self.passwordLineEdit.text()
        print(f"Attempting to log in with username: {username}")
        token = self.get_token(username, password)
        if not token:
            QMessageBox.critical(self, "Error", "Failed to authenticate.")
            return
        items = self.get_user_items(username, token)
        # self.itemListWidget.clear()
        empty_model = QStandardItemModel(0, 0)
        self.UserSearchitemTableView.setModel(empty_model)
        
        items_data = self.extract_item_details(items)
        # self.populate_list(items_data, self.itemListWidget)
        self.populate_table(items_data, self.UserSearchitemTableView)
        
    def get_service_url(self, item_id, token=None):
        if token is None:
            metadata_url = (
                f"https://www.arcgis.com/sharing/rest/content/items/"
                f"{item_id}?f=json"
            )
        else:
            metadata_url = (
                f"https://www.arcgis.com/sharing/rest/content/items/"
                f"{item_id}?f=json&token={token}"
            )
        print(metadata_url)
        response = network.get(metadata_url)
        response.raise_for_status()
        item_data = response.json()
        return item_data.get("url")  # This is the feature service url

    def populate_table(self, items_data, table_view):
        if not items_data:
            QMessageBox.information(self, "No Results", "No items found.")
            return

        model = AgolItemsModel(items_data)
        table_view.setModel(model)
        table_view.resizeColumnsToContents()
        table_view.setSelectionBehavior(table_view.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(table_view.SelectionMode.SingleSelection)

        # --- progress dialog ------------------------------------------
        dlg = QProgressDialog("Loading thumbnails…", "Cancel", 0,
                            len(items_data), self)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)            # show immediately
        dlg.setAutoClose(True)
        dlg.setAutoReset(True)
        # -------------------------------------------------------------

        for i, item_info in enumerate(items_data):
            if dlg.wasCanceled():
                break

            thumbnail_url = item_info.get("thumbnail_url", "")
            if thumbnail_url:
                try:
                    resp = network.get(thumbnail_url, timeout=8)
                    resp.raise_for_status()
                    pixmap = QPixmap()
                    pixmap.loadFromData(resp.content)
                    icon = QIcon(pixmap)
                except Exception:
                    icon = QIcon()
            else:
                icon = QIcon()

            model.setIcon(i, icon)


            dlg.setValue(i + 1)               # update progress bar
            QApplication.processEvents()      # keep UI responsive

        dlg.close()


    def populate_list(self, items_data, target_list_widget):
        if not items_data:
            QMessageBox.information(self, "No Results", "No items found.")
            return

        target_list_widget.clear()

        # --- progress indicator ------------------------------------------
        dlg = QProgressDialog("Loading thumbnails…", "Cancel", 0,
                              len(items_data), self)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)            # show immediately
        dlg.setAutoClose(True)
        dlg.setAutoReset(True)
        # -----------------------------------------------------------------

        for i, item_info in enumerate(items_data, start=1):
            if dlg.wasCanceled():
                break

            title = item_info["title"]
            url = item_info["url"]
            thumbnail_url = item_info["thumbnail_url"]

            # download thumbnail (blocking) --------------------------
            try:
                resp = network.get(thumbnail_url, timeout=8)
                resp.raise_for_status()
                pixmap = QPixmap()
                pixmap.loadFromData(resp.content)
                icon = QIcon(pixmap)
            except Exception:
                icon = QIcon()
            # -----------------------------------------------------------

            list_item = QListWidgetItem(icon, title)
            #list_item.setToolTip(url)
            target_list_widget.addItem(list_item)

            dlg.setValue(i)                 # update bar
            QApplication.processEvents()    # let Qt refresh UI

        dlg.close()

    def get_token(self, username, password):
        token_url = "https://www.arcgis.com/sharing/rest/generateToken"
        data = {
            "f": "json",
            "username": username,
            "password": password,
            "client": "referer",
            "referer": "https://www.arcgis.com",
            "expiration": 600
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = network.post(token_url, data=data, headers=headers)
        token_info = response.json()
        token = token_info["token"]
        return token

    def get_user_items(self, username, token):
        url = f"https://www.arcgis.com/sharing/rest/content/users/{username}"
        params = {"f": "json", "token": token}
        print(url, params)
        try:
            r = network.get(url, params=params)
            result = r.json()
            all_items = result.get("items", [])
            print(f"Found {len(all_items)} items for user.")

            # Only allow QGIS-compatible services
            allowed_types = {"Feature Service", "Map Service", "Image Service"}
            filtered_items = [
                item for item in all_items
                if item.get("type") in allowed_types
            ]

            print(f"Filtered down to {len(filtered_items)} compatible")
            return filtered_items

        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def get_search_items(self, search_term):
        url = "https://www.arcgis.com/sharing/rest/search"
        search_term = "working"
        params = {
            "q": f'{search_term} type:"Feature Service"',
            "f": "json",
            "num": 3,
            "start": 1
        }
        try:
            r = network.get(url, params=params)
            result = r.json()
            print(result)
            return result.get("results", [])
        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def extract_item_details(self, items):
        items_data = []
        for item in items:
            title = item.get("title", "No Title")
            item_id = item.get("id")
            url = f"https://www.arcgis.com/home/item.html?id={item_id}"

            thumbnail = item.get("thumbnail")
            if thumbnail:
                thumbnail_url = (
                    "https://www.arcgis.com/sharing/rest/content/items/"
                    f"{item_id}/info/{thumbnail}"
                )
            else:
                thumbnail_url = (
                    "https://www.arcgis.com/sharing/rest/content/items/thumbnail/thumbnail.png"
                )
            owner = item.get("owner", "Unknown")
            item_type = item.get("type", "Unknown")
            date = item.get("modified")  # epoch timestamp in ms?
            if date:
                from datetime import datetime
                try:
                    date = datetime.utcfromtimestamp(date / 1000).strftime("%Y-%m-%d")
                except Exception:
                    date = "Unknown"
            else:
                date = "Unknown"

            items_data.append({
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "owner": owner,
                "type": item_type,
                "date": date
            })

        return items_data

    def search_agol_content(self, max_results=20):
        search_term = self.SearchTextlineEdit.text()
        items = self.get_search_items(search_term)
        empty_model = QStandardItemModel(0, 0)  # no rows, no columns
        self.SearchitemTableView.setModel(empty_model)
        items_data = self.extract_item_details(items)
        self.populate_table(items_data, self.SearchitemTableView)

    def get_feature_service_layers(self, service_url, token=None):
        if token is None:
            url_tokend = f"{service_url}?f=json"
        else:
            url_tokend = f"{service_url}?f=json&token={token}"
        print(url_tokend)
        try:
            response = network.get(url_tokend)
            response.raise_for_status()
            data = response.json()
            return data.get("layers", [])
        except Exception as e:
            print(f"Failed to fetch layers: {e}")
            return []

    def select_and_load_arcgis_layer(self, service_url):
        try:
            token = self.get_token(
                self.usernameLineEdit.text(), self.passwordLineEdit.text())
        except Exception as e:
            print(f"Token generation failed: {e}")
            token = None
        layers = self.get_feature_service_layers(service_url, token)
        print(service_url)
        if not layers:
            QMessageBox.warning(None, "No Layers Found", 
                                "The service has no feature layers.")
            return
        dialog = LayerSelectionDialog(layers)
        
        def on_layer_selected(layer_id):
            layer_name = next((l["name"] for l in layers if l["id"] == layer_id), "ArcGIS Layer")
            self.load_selected_arcgis_layer(service_url, layer_id, layer_name, token)

        dialog.layerSelected.connect(on_layer_selected)
        dialog.exec()

    def load_selected_arcgis_layer(
        self, service_url, layer_id, name="ArcGIS Layer", token=None
    ):
        layer_url = f"url='{service_url}/{layer_id}'"
        if token:
            auth_mgr = QgsApplication.authManager()
            auth_config = QgsAuthMethodConfig("EsriToken")
            auth_config.setName("QarcConnect Token")
            auth_config.setMethod("EsriToken")  # For custom HTTP headers
            auth_config.setConfig("token", token)
            auth_mgr = QgsApplication.authManager()
            for cfg_id in auth_mgr.availableAuthMethodConfigs():
                cfg = QgsAuthMethodConfig()
                if auth_mgr.loadAuthenticationConfig(cfg_id, cfg):
                    if cfg.name() == "QarcConnect Token" and cfg.method() == "Basic":
                        auth_mgr.removeAuthenticationConfig(cfg_id)
            success = auth_mgr.storeAuthenticationConfig(auth_config)
            if success:
                print("Authentication config stored.")
            else:
                raise Exception("Failed to store authentication config.")
        uri = QgsDataSourceUri()
        uri.setParam('url', layer_url)
        if token:
            print(token)
            layer_url = f"authcfg={auth_config.id()} " + layer_url
        print("layer_url")
        print(layer_url)
        layer = QgsVectorLayer(layer_url, name,
                               "arcgisfeatureserver")
        print(layer.source())
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            print("Layer loaded successfully with authcfg in URI.")
        else:
            print("Failed to load layer.")

    def on_item_double_clicked(self, index, token=None):
        if not index.isValid():
            return
        title_index = index.sibling(index.row(), 0)
        tooltip_url = title_index.data(Qt.ToolTipRole)
        if not tooltip_url:
            print("No URL found in tooltip.")
            return
        try:
            token = self.get_token(
                self.usernameLineEdit.text(), self.passwordLineEdit.text())
        except Exception as e:
            print(f"Token generation failed: {e}")
            token = None
        from urllib.parse import urlparse, parse_qs
        item_id = parse_qs(urlparse(tooltip_url).query).get("id", [None])[0]
        if item_id:
            service_url = self.get_service_url(item_id, token)
            if service_url:
                self.select_and_load_arcgis_layer(service_url)
            else:
                print("Could not resolve feature service URL.")