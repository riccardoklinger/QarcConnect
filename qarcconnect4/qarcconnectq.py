import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from .qarcconnectq_dialog import QarcConnectQDialog


class QarcConnectQ:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "images", "QarcConnect.svg")
        icon = QIcon(icon_path)

        # Add toolbar icon WITHOUT text label
        self.action = QAction(icon, "", self.iface.mainWindow())
        self.action.setToolTip("QarcConnectQ")  # tooltip on hover
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

        # Add the action also to the Plugins menu with a name
        self.iface.addPluginToMenu("&QarcConnectQ", self.action)

    def unload(self):
        self.iface.removePluginMenu("&QarcConnectQ", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        dlg = QarcConnectQDialog()
        dlg.exec()
