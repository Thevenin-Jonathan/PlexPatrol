# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config', 'config'), ('assets', 'assets'), ('utils', 'utils'), ('data', 'data'), ('ui', 'ui'), ('core', 'core'), ('data/GeoLite2-City.mmdb', 'data')],
    hiddenimports=['pkgutil', 'utils.constants', 'config.config_manager', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtCore', 'PyQt5.QtWidgets.QSystemTrayIcon', 'PyQt5.QtWidgets.QMenu', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngine', 'PyQt5.QtChart', 'geoip2', 'geoip2.database', 'sqlite3', 'json', 'datetime', 'tempfile', 'PyQt5.QtChart.QChart', 'PyQt5.QtChart.QPieSeries', 'PyQt5.QtChart.QPieSlice', 'PyQt5.QtChart.QChartView', 'PyQt5.QtChart.QBarSeries', 'PyQt5.QtChart.QBarSet'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PlexPatrol',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\plexpatrol.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PlexPatrol',
)
