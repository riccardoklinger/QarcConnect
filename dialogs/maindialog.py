###############################################################################
#
# QarcConnect - QGIS Plugin
#
# Copyright (C) 2025 Riccardo Klinger (riccardoklinger.xyz)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
###############################################################################

import json
from urllib.request import build_opener, install_opener, ProxyHandler

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QComboBox,
    QMessageBox,
    QTreeWidgetItem,
    QWidget,
    QLineEdit,
)
from qgis.core import (
    # Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    QgsProviderRegistry,
    QgsSettings,
    QgsProject,
    QgsRectangle,
    QgsSettingsTree,
)
from qgis.gui import QgsGui
from qgis.utils import OverrideCursor

try:
    from owslib.util import Authentication
except ImportError:
    pass

from QarcConnect import link_types
from QarcConnect.dialogs.recorddialog import RecordDialog
from QarcConnect.search_backend import get_catalog_service
from QarcConnect.util import (
    clean_ows_url,
    get_ui_class,
    get_help_url,
    normalize_text,
    open_url,
    render_template,
    serialize_string,
)

BASE_CLASS = get_ui_class("maindialog.ui")


class QarcConnectDialog(QDialog, BASE_CLASS):
    """main dialogue"""

    def __init__(self, iface):
        """init window"""

        QDialog.__init__(self)
        self.setupUi(self)

        self.iface = iface
        self.map = iface.mapCanvas()
        self.settings = QgsSettings()
        self.maxrecords = 100
        self.timeout = 10
        self.show_password_checkbox.stateChanged.connect(
            self.toggle_password_visibility
        )
        self.startfrom = 1
        self.catalog = None
        self.rubber_band = None
        self.catalog_url = None
        self.catalog_username = None
        self.catalog_password = None
        self.disable_ssl_verification = False
        self.log_debugging_messages = False
        self.manageGui()

    def manageGui(self):
        """open window"""

        def _on_timeout_change(value):
            self.settings.setValue("/QarcConnect/timeout", value)
            self.timeout = value

        def _on_records_change(value):
            self.settings.setValue("/QarcConnect/returnRecords", value)
            self.maxrecords = value

        def _on_ssl_state_change(state):
            self.settings.setValue("/QarcConnect/disableSSL", bool(state))
            self.disable_ssl_verification = bool(state)

        #def _on_debugging_state_change(state):
        
            self.settings.setValue("/QarcConnect/logDebugging", bool(state))
            self.log_debugging_messages = bool(state)

        self.tabWidget.setCurrentIndex(0)
        #self.populate_connection_list()
        
        #self.btnRawAPIResponse.setEnabled(False)

        # load settings
        self.spnRecords.setValue(self.maxrecords)
        self.spnRecords.valueChanged.connect(_on_records_change)
        self.spnTimeout.setValue(self.timeout)
        self.spnTimeout.valueChanged.connect(_on_timeout_change)
        self.disableSSLVerification.setChecked(self.disable_ssl_verification)
        self.disableSSLVerification.stateChanged.connect(_on_ssl_state_change)
        self.logDebuggingMessages.setChecked(self.log_debugging_messages)
        #self.logDebuggingMessages.stateChanged.connect(_on_debugging_state_change)

        key = "/QarcConnect/%s" % self.cmbConnectionsSearch.currentText()
        self.catalog_url = self.settings.value("%s/url" % key)
        self.catalog_username = self.settings.value("%s/username" % key)
        self.catalog_password = self.settings.value("%s/password" % key)
        self.catalog_type = self.settings.value("%s/catalog-type" % key)

        self.set_bbox_global()

        self.reset_buttons()

        # install proxy handler if specified in QGIS settings
        self.install_proxy()

    # Services tab

    
        """populate select box with connections"""

        self.settings.beginGroup("/QarcConnect/")
        #self.cmbConnectionsServices.clear()
        #self.cmbConnectionsServices.addItems(self.settings.childGroups())
        #self.cmbConnectionsSearch.clear()
        #self.cmbConnectionsSearch.addItems(self.settings.childGroups())
        self.settings.endGroup()

        #self.set_connection_list_position()

        #if self.cmbConnectionsServices.count() == 0:
        #    # no connections - disable various buttons
        #    state_disabled = False
        #    self.btnSave.setEnabled(state_disabled)
            # and start with connection tab open
        #    self.tabWidget.setCurrentIndex(1)
            # tell the user to add services
        #    msg = self.tr(
        #        "No services/connections defined. To get "
        #        "started with QarcConnect, create a new "
        #        "connection by clicking 'New' or click "
        #        "'Add default services'."
        #    )
        #    self.textMetadata.setHtml("<p><h3>%s</h3></p>" % msg)
        #else:
            # connections - enable various buttons
        #    state_disabled = True

        #self.btnServerInfo.setEnabled(state_disabled)
        #self.btnEdit.setEnabled(state_disabled)
        #self.btnDelete.setEnabled(state_disabled)
    def toggle_password_visibility(self, state):
        if state == Qt.CheckState.Checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
    # Search tab

    def set_bbox_from_map(self):
        """set bounding box from map extent"""

        crs = self.map.mapSettings().destinationCrs()
        crsid = crs.authid()

        extent = self.map.extent()

        if crsid != "EPSG:4326":  # reproject to EPSG:4326
            src = QgsCoordinateReferenceSystem(crsid)
            dest = QgsCoordinateReferenceSystem("EPSG:4326")
            xform = QgsCoordinateTransform(src, dest, QgsProject.instance())
            minxy = xform.transform(
                QgsPointXY(
                    extent.xMinimum(),
                    extent.yMinimum()
                )
            )
            maxxy = xform.transform(
                QgsPointXY(
                    extent.xMaximum(),
                    extent.xMaximum()
                )
            )
            minx, miny = minxy
            maxx, maxy = maxxy
        else:  # EPSG:4326
            minx = extent.xMinimum()
            miny = extent.yMinimum()
            maxx = extent.xMaximum()
            maxy = extent.yMaximum()

        self.leNorth.setText(str(maxy)[0:9])
        self.leSouth.setText(str(miny)[0:9])
        self.leWest.setText(str(minx)[0:9])
        self.leEast.setText(str(maxx)[0:9])

    def set_bbox_global(self):
        """set global bounding box"""
        self.leNorth.setText("90")
        self.leSouth.setText("-90")
        self.leWest.setText("-180")
        self.leEast.setText("180")

    def search(self):
        """execute search"""

        self.catalog = None
        self.constraints = []

        # clear all fields and disable buttons
        self.clear_results()

        # set current catalog
        current_text = self.cmbConnectionsSearch.currentText()
        key = "/QarcConnect/%s" % current_text
        self.catalog_url = self.settings.value("%s/url" % key)
        self.catalog_username = self.settings.value("%s/username" % key)
        self.catalog_password = self.settings.value("%s/password" % key)
        self.catalog_type = self.settings.value("%s/catalog-type" % key)

        # start position and number of records to return
        self.startfrom = 1

        # bbox
        # CRS is WGS84 with axis order longitude, latitude
        # defined by 'urn:ogc:def:crs:OGC:1.3:CRS84'
        minx = self.leWest.text()
        miny = self.leSouth.text()
        maxx = self.leEast.text()
        maxy = self.leNorth.text()
        bbox = [minx, miny, maxx, maxy]
        keywords = self.leKeywords.text()

        # build request
        if not self._get_catalog():
            return

        # TODO: allow users to select resources types
        # to find ('service', 'dataset', etc.)
        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.catalog.query_records(
                    bbox, keywords, self.maxrecords, self.startfrom
                )

        except Exception as err:
            QMessageBox.warning(
                self, self.tr("Search error"),
                self.tr("Search error: {0}").format(err)
            )
            return

        if self.catalog.matches == 0:
            self.lblResults.setText(self.tr("0 results"))
            return

        self.display_results()

    def display_results(self):
        """display search results"""

        self.treeRecords.clear()

        position = self.catalog.returned + self.startfrom - 1

        msg = self.tr(
            "Showing {0} - {1} of %n result(s)",
            "number of results",
            self.catalog.matches,
        ).format(self.startfrom, position)

        self.lblResults.setText(msg)

        for rec in self.catalog.records():
            item = QTreeWidgetItem(self.treeRecords)
            if rec["type"]:
                item.setText(0, normalize_text(rec["type"]))
            else:
                item.setText(0, "unknown")
            if rec["title"]:
                item.setText(1, normalize_text(rec["title"]))
            if rec["identifier"]:
                set_item_data(item, "identifier", rec["identifier"])

        self.btnViewRawAPIResponse.setEnabled(True)

        if self.catalog.matches < self.maxrecords:
            disabled = False
        else:
            disabled = True

        self.btnFirst.setEnabled(disabled)
        self.btnPrev.setEnabled(disabled)
        self.btnNext.setEnabled(disabled)
        self.btnLast.setEnabled(disabled)
        self.btnRawAPIResponse.setEnabled(False)

    def clear_results(self):
        """clear search results"""

        self.lblResults.clear()
        self.treeRecords.clear()
        self.reset_buttons()

    def record_clicked(self):
        """record clicked signal"""

        # disable only service buttons
        self.reset_buttons(True, False, False)
        if not self.treeRecords.selectedItems():
            return

        item = self.treeRecords.currentItem()
        if not item:
            return

        identifier = get_item_data(item, "identifier")
        try:
            record = next(
                item
                for item in self.catalog.records()
                if item["identifier"] == identifier
            )
        except KeyError:
            QMessageBox.warning(
                self,
                self.tr("Record parsing error"),
                "Unable to locate record identifier",
            )
            return

        # if the record has a bbox, show a footprint on the map
        if record["bbox"] is not None:
            bx = record["bbox"]
            rt = QgsRectangle(
                float(bx["minx"]),
                float(bx["miny"]),
                float(bx["maxx"]),
                float(bx["maxy"]),
            )
            geom = QgsGeometry.fromRect(rt)

            if geom is not None:
                src = QgsCoordinateReferenceSystem("EPSG:4326")
                dst = self.map.mapSettings().destinationCrs()
                if src.postgisSrid() != dst.postgisSrid():
                    ctr = QgsCoordinateTransform(
                        src,
                        dst,
                        QgsProject.instance()
                    )
                    try:
                        geom.transform(ctr)
                    except Exception as err:
                        QMessageBox.warning(
                            self,
                            self.tr("Coordinate Transformation Error"),
                            str(err)
                        )
                self.rubber_band.setToGeometry(geom, None)

        # figure out if the data is interactive and can be operated on
        self.find_services(record, item)

    def find_services(self, record, item):
        """scan record for WMS/WMTS|WFS|WCS endpoints"""

        services = {}
        for link in record["links"]:
            link = self.catalog.parse_link(link)
            if "scheme" in link:
                link_type = link["scheme"]
            elif "protocol" in link:
                link_type = link["protocol"]
            else:
                link_type = None

            if link_type is not None:
                link_type = link_type.upper()

            wmswmst_link_types = list(map(str.upper, 
                                          link_types.WMSWMST_LINK_TYPES))
            wfs_link_types = list(map(str.upper, 
                                      link_types.WFS_LINK_TYPES))
            wcs_link_types = list(map(str.upper, 
                                      link_types.WCS_LINK_TYPES))
            ams_link_types = list(map(str.upper, 
                                      link_types.AMS_LINK_TYPES))
            afs_link_types = list(map(str.upper, 
                                      link_types.AFS_LINK_TYPES))
            gis_file_link_types = list(map(str.upper,
                                           link_types.GIS_FILE_LINK_TYPES))

            # if the link type exists, and it is one of the acceptable
            # interactive link types, then set
            all_link_types = (
                wmswmst_link_types
                + wfs_link_types
                + wcs_link_types
                + ams_link_types
                + afs_link_types
                + gis_file_link_types
            )

            if all([link_type is not None, link_type in all_link_types]):
                if link_type in wmswmst_link_types:
                    services["wms"] = link["url"]
                    self.mActionAddWms.setEnabled(True)
                if link_type in wfs_link_types:
                    services["wfs"] = link["url"]
                    self.mActionAddWfs.setEnabled(True)
                if link_type in wcs_link_types:
                    services["wcs"] = link["url"]
                    self.mActionAddWcs.setEnabled(True)
                if link_type in ams_link_types:
                    services["ams"] = link["url"]
                    self.mActionAddAms.setEnabled(True)
                if link_type in afs_link_types:
                    services["afs"] = link["url"]
                    self.mActionAddAfs.setEnabled(True)
                if link_type in gis_file_link_types:
                    services["gis_file"] = link["url"]
                    services["title"] = record.get("title", "")
                    self.mActionAddGisFile.setEnabled(True)
                self.tbAddData.setEnabled(True)

            set_item_data(item, "link", json.dumps(services))

    def navigate(self):
        """manage navigation / paging"""

        caller = self.sender().objectName()

        if caller == "btnFirst":
            self.startfrom = 1
        elif caller == "btnLast":
            self.startfrom = self.catalog.matches - self.maxrecords + 1
        elif caller == "btnNext":
            if self.startfrom > self.catalog.matches - self.maxrecords:
                msg = self.tr("End of results. Go to start?")
                res = QMessageBox.information(
                    self,
                    self.tr("Navigation"),
                    msg,
                    (QMessageBox.StandardButton.Ok |
                     QMessageBox.StandardButton.Cancel),
                )
                if res == QMessageBox.StandardButton.Ok:
                    self.startfrom = 1
                else:
                    return
            else:
                self.startfrom += self.maxrecords
        elif caller == "btnPrev":
            if self.startfrom == 1:
                msg = self.tr("Start of results. Go to end?")
                res = QMessageBox.information(
                    self,
                    self.tr("Navigation"),
                    msg,
                    (QMessageBox.StandardButton.Ok |
                     QMessageBox.StandardButton.Cancel),
                )
                if res == QMessageBox.StandardButton.Ok:
                    self.startfrom = self.catalog.matches - self.maxrecords + 1
                else:
                    return
            elif self.startfrom <= self.maxrecords:
                self.startfrom = 1
            else:
                self.startfrom -= self.maxrecords

        # bbox
        # CRS is WGS84 with axis order longitude, latitude
        # defined by 'urn:ogc:def:crs:OGC:1.3:CRS84'
        minx = self.leWest.text()
        miny = self.leSouth.text()
        maxx = self.leEast.text()
        maxy = self.leNorth.text()
        bbox = [minx, miny, maxx, maxy]
        keywords = self.leKeywords.text()

        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.catalog.query_records(
                    bbox,
                    keywords,
                    limit=self.maxrecords,
                    offset=self.startfrom
                )
        except Exception as err:
            QMessageBox.warning(
                self,
                self.tr("Search error"),
                self.tr("Search error: {0}").format(err)
            )
            return

        self.display_results()

    def add_to_ows(self):
        """add to OWS provider connection list"""

        conn_name_matches = []

        item = self.treeRecords.currentItem()

        if not item:
            return

        item_data = json.loads(get_item_data(item, "link"))

        caller = self.sender().objectName()

        if caller == "mActionAddWms":
            service_type = "OGC:WMS/OGC:WMTS"
            sname = "WMS"
            dyn_param = ["wms"]
            provider_name = "wms"
            setting_node = (
                QgsSettingsTree.node("connections")
                .childNode("ows")
                .childNode("connections")
            )
            data_url = item_data["wms"]
        elif caller == "mActionAddWfs":
            service_type = "OGC:WFS"
            sname = "WFS"
            dyn_param = ["wfs"]
            provider_name = "WFS"
            setting_node = (
                QgsSettingsTree.node("connections")
                .childNode("ows")
                .childNode("connections")
            )
            data_url = item_data["wfs"]
        elif caller == "mActionAddWcs":
            service_type = "OGC:WCS"
            sname = "WCS"
            dyn_param = ["wcs"]
            provider_name = "wcs"
            setting_node = (
                QgsSettingsTree.node("connections")
                .childNode("ows")
                .childNode("connections")
            )
            data_url = item_data["wcs"]
        elif caller == "mActionAddAfs":
            service_type = "ESRI:ArcGIS:FeatureServer"
            sname = "AFS"
            dyn_param = []
            provider_name = "arcgisfeatureserver"
            setting_node = QgsSettingsTree.node("connections").childNode(
                "arcgisfeatureserver"
            )
            data_url = item_data["afs"].split("FeatureServer")[0]
            + "FeatureServer"

        keys = setting_node.items(dyn_param)

        sname = "%s from QarcConnect" % sname
        for key in keys:
            if key.startswith(sname):
                conn_name_matches.append(key)
        if conn_name_matches:
            sname = conn_name_matches[-1]

        # check for duplicates
        if sname in keys:  # duplicate found
            msg = self.tr("Connection {0} exists. Overwrite?").format(sname)
            res = QMessageBox.warning(
                self,
                self.tr("Saving server"),
                msg,
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if res == QMessageBox.StandardButton.No:  # assign newname w serial
                sname = serialize_string(sname)
            elif res == QMessageBox.StandardButton.Cancel:
                return

        # no dups detected or overwrite is allowed
        dyn_param.append(sname)
        setting_node.childSetting("url").setValue(clean_ows_url(data_url),
                                                  dyn_param)

        # open provider window
        ows_provider = QgsGui.sourceSelectProviderRegistry().createSelectionWidget(
            provider_name,
            self,
            Qt.WindowType.Widget,
            QgsProviderRegistry.WidgetMode.Embedded,
        )

        # connect dialog signals to iface slots
        if service_type == "OGC:WMS/OGC:WMTS":
            ows_provider.addRasterLayer.connect(self.iface.addRasterLayer)
            conn_cmb = ows_provider.findChild(QWidget, "cmbConnections")
            connect = "btnConnect_clicked"
        elif service_type == "OGC:WFS":

            def addVectorLayer(path, name):
                self.iface.addVectorLayer(path, name, "WFS")

            ows_provider.addVectorLayer.connect(addVectorLayer)
            conn_cmb = ows_provider.findChild(QWidget, "cmbConnections")
            connect = "connectToServer"
        elif service_type == "OGC:WCS":
            ows_provider.addRasterLayer.connect(self.iface.addRasterLayer)
            conn_cmb = ows_provider.findChild(QWidget, "mConnectionsComboBox")
            connect = "mConnectButton_clicked"
        elif service_type == "ESRI:ArcGIS:FeatureServer":

            def addAfsLayer(path, name):
                self.iface.addVectorLayer(path, name, "afs")

            ows_provider.addVectorLayer.connect(addAfsLayer)
            conn_cmb = ows_provider.findChild(QComboBox)
            connect = "connectToServer"

        ows_provider.setModal(False)
        ows_provider.show()

        # open provider dialogue against added OWS
        index = conn_cmb.findText(sname)
        if index > -1:
            conn_cmb.setCurrentIndex(index)
            # only for wfs
            if service_type == "OGC:WFS":
                ows_provider.cmbConnections_activated(index)
            elif service_type == "ESRI:ArcGIS:FeatureServer":
                ows_provider.cmbConnections_activated(index)
        getattr(ows_provider, connect)()

    def add_gis_file(self):
        """add GIS file from result"""
        item = self.treeRecords.currentItem()

        if not item:
            return

        item_data = json.loads(get_item_data(item, "link"))
        gis_file = item_data["gis_file"]

        title = item_data["title"]

        layer = self.iface.addVectorLayer(gis_file, title, "ogr")
        if not layer:
            self.iface.messageBar().pushWarning(None, "Layer failed to load!")

    def show_metadata(self):
        """show record metadata"""

        if not self.treeRecords.selectedItems():
            return

        item = self.treeRecords.currentItem()
        if not item:
            return

        identifier = get_item_data(item, "identifier")

        auth = None

        if self.disable_ssl_verification:
            try:
                auth = Authentication(verify=False)
            except NameError:
                pass

        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                cat = get_catalog_service(
                    self.catalog_url,  # spellok
                    catalog_type=self.catalog_type,
                    timeout=self.timeout,
                    username=self.catalog_username or None,
                    password=self.catalog_password or None,
                    auth=auth,
                )
                record = cat.get_record(identifier)
                if cat.type == "OGC API - Records":
                    record["url"] = cat.conn.request
                elif cat.type == "OGC CSW 2.0.2":
                    record.url = cat.conn.request

        except Exception as err:
            QMessageBox.warning(
                self,
                self.tr("GetRecords error"),
                self.tr("Error getting response: {0}").format(err),
            )
            return
        except KeyError as err:
            QMessageBox.warning(
                self,
                self.tr("Record parsing error"),
                self.tr("Unable to locate record identifier: {0}").format(err),
            )
            return

        crd = RecordDialog()
        metadata = render_template(
            "en", self.context, record, self.catalog.record_info_template
        )

        style = QgsApplication.reportStyleSheet()
        crd.textMetadata.document().setDefaultStyleSheet(style)
        crd.textMetadata.setHtml(metadata)
        crd.exec()

    def reset_buttons(self, services=True, api=True, navigation=True):
        """Convenience function to disable WMS/WMTS|WFS|WCS buttons"""

        if services:
            self.tbAddData.setEnabled(False)
            self.mActionAddWms.setEnabled(False)
            self.mActionAddWfs.setEnabled(False)
            self.mActionAddWcs.setEnabled(False)
            self.mActionAddAms.setEnabled(False)
            self.mActionAddAfs.setEnabled(False)
            self.mActionAddGisFile.setEnabled(False)

        if api:
            self.btnViewRawAPIResponse.setEnabled(False)

        if navigation:
            self.btnFirst.setEnabled(False)
            self.btnPrev.setEnabled(False)
            self.btnNext.setEnabled(False)
            self.btnLast.setEnabled(False)

    def help(self):
        """launch help"""

        open_url(get_help_url())

    def reject(self):
        """back out of dialogue"""

        QDialog.reject(self)

    def _get_catalog(self):
        """convenience function to init catalog wrapper"""

        auth = None

        if self.disable_ssl_verification:
            try:
                auth = Authentication(verify=False)
            except NameError:
                pass

        # connect to the server
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            try:
                self.catalog = get_catalog_service(
                    self.catalog_url,
                    catalog_type=self.catalog_type,
                    timeout=self.timeout,
                    username=self.catalog_username or None,
                    password=self.catalog_password or None,
                    auth=auth,
                )
                return True
            except Exception as err:
                msg = self.tr("Error connecting to service: {0}").format(err)

        QMessageBox.warning(self, self.tr("CSW Connection error"), msg)
        return False

    def install_proxy(self):
        """set proxy if one is set in QGIS network settings"""

        # initially support HTTP for now
        if self.settings.value("/proxy/proxyEnabled") == "true":
            if self.settings.value("/proxy/proxyType") == "HttpProxy":
                ptype = "http"
            else:
                return

            user = self.settings.value("/proxy/proxyUser")
            password = self.settings.value("/proxy/proxyPassword")
            host = self.settings.value("/proxy/proxyHost")
            port = self.settings.value("/proxy/proxyPort")

            proxy_up = ""
            proxy_port = ""

            if all([user != "", password != ""]):
                proxy_up = f"{user}:{password}@"

            if port != "":
                proxy_port = ":%s" % port

            conn = f"{ptype}://{proxy_up}{host}{proxy_port}"
            install_opener(build_opener(ProxyHandler({ptype: conn})))


def get_item_data(item, field):
    """return identifier for a QTreeWidgetItem"""

    return item.data(_get_field_value(field), 32)


def set_item_data(item, field, value):
    """set identifier for a QTreeWidgetItem"""

    item.setData(_get_field_value(field), 32, value)


def _get_field_value(field):
    """convenience function to return field value integer"""

    value = 0

    if field == "identifier":
        value = 0
    if field == "link":
        value = 1

    return value
