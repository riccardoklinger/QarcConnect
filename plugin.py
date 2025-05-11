###############################################################################
#
# QarcConnect - QGIS Plugin
# Copyright (C) 2025 Riccardo Klinger (riccardoklinger.xyz)
#
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

import logging

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from qgis.core import Qgis, QgsApplication
from QarcConnect.dialogs.maindialog import QarcConnectDialog
from QarcConnect.util import get_help_url, log_message, open_url, StaticContext


class QarcConnectPlugin:
    """base plugin"""

    def __init__(self, iface):
        """init"""

        self.iface = iface
        self.context = StaticContext()
        self.action_run = None
        self.action_help = None
        self.dialog = None
        self.web_menu = "&QarcConnect"

    def initGui(self):
        """startup"""

        # run
        log_message("Initializing plugin", Qgis.MessageLevel.Info)

        run_icon = QIcon("{}/{}".format(self.context.ppath, "images/QarcConnect.svg"))
        self.action_run = QAction(run_icon, "QarcConnect", self.iface.mainWindow())
        self.action_run.setWhatsThis(
            QCoreApplication.translate("QarcConnect", "QarcConnect plugin")
        )
        self.action_run.setStatusTip(
            QCoreApplication.translate("QarcConnect", "Search Metadata Catalogs")
        )

        self.action_run.triggered.connect(self.run)

        self.iface.addWebToolBarIcon(self.action_run)
        self.iface.addPluginToWebMenu(self.web_menu, self.action_run)

        # help
        help_icon = QgsApplication.getThemeIcon("/mActionHelpContents.svg")
        self.action_help = QAction(help_icon, "Help", self.iface.mainWindow())
        self.action_help.setWhatsThis(
            QCoreApplication.translate("QarcConnect", "QarcConnect plugin help")
        )
        self.action_help.setStatusTip(
            QCoreApplication.translate("QarcConnect", "Get Help on QarcConnect")
        )
        self.action_help.triggered.connect(self.help)

        self.iface.addPluginToWebMenu(self.web_menu, self.action_help)

        # prefab the dialog but not open it yet
        self.dialog = QarcConnectDialog(self.iface)

    def unload(self):
        """teardown"""

        log_message("Unloading plugin", Qgis.MessageLevel.Info)

        # remove the plugin menu item and icon
        self.iface.removePluginWebMenu(self.web_menu, self.action_run)
        self.iface.removePluginWebMenu(self.web_menu, self.action_help)
        self.iface.removeWebToolBarIcon(self.action_run)

    def run(self):
        """open QarcConnect"""

        log_message("Running plugin", Qgis.MessageLevel.Info)

        self.dialog.exec()

    def help(self):
        """open help in user's default web browser"""

        open_url(get_help_url())
