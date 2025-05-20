# myplugin/network.py

import os
import requests
from qgis.PyQt.QtCore import QSettings
#from .qarcconnect3_dialog_base import Ui_QarcConnect3Dialog

# (Optional) Set this to True to print resolved proxy info
DEBUG = True



import requests
from qgis.PyQt.QtCore import QSettings

session = requests.Session()
session.headers.update({'User-Agent': 'MyQGISPlugin/1.0'})

def set_proxy(proxy:str):
    if proxy:
        proxy_url = proxy
        proxies = {
            'http': proxy_url,
            'https': proxy_url,
        }
        session.proxies = proxies
        print(f"[network] Proxy set to {proxy_url}")
    else:
        session.proxies = {}  # no proxy
        print("[network] Proxy cleared (no host/port)")

def load_proxy_from_settings():
    settings = QSettings()
    proxy = settings.value("QarcConnect3/proxy_host", "")
    #port = settings.value("myplugin/proxy_port", "")
    set_proxy(proxy)

# Create a single session that respects system proxies
session = requests.Session()
session.proxies = load_proxy_from_settings()
print(session.proxies)
# Optional: set a User-Agent
session.headers.update({
    'User-Agent': 'QarcConnect3/1.0'
})

# Provide wrapped access
get = session.get
post = session.post
put = session.put
delete = session.delete