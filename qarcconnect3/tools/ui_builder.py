from PyQt6.uic import compileUi
in_file = r"C:\Users\ricca\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\QarcConnect3\QarcConnect3_dialog_base.ui"
out_file = r"C:\Users\ricca\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\QarcConnect3\QarcConnect3_dialog_base.py"
with open(in_file, 'r', encoding='utf-8') as ui_file:
    with open(out_file, 'w', encoding='utf-8') as py_file:compileUi(ui_file, py_file)