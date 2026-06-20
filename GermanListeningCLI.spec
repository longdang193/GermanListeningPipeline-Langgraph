# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\HOANG PHI LONG DANG\\repos\\German_Listening\\Tools\\src\\glist_pipeline_entry.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('C:\\Users\\HOANG PHI LONG DANG\\repos\\German_Listening\\configs\\policy.toml', 'configs'),
        ('C:\\Users\\HOANG PHI LONG DANG\\repos\\German_Listening\\configs\\labels.toml', 'configs'),
        ('C:\\Users\\HOANG PHI LONG DANG\\repos\\German_Listening\\configs\\runtime.toml', 'configs'),
    ],
    hiddenimports=['glist_pipeline.legacy.generate_listening_2', 'glist_pipeline.legacy.generate_listening_4', 'glist_pipeline.legacy.check_listening_2', 'glist_pipeline.legacy.check_listening_4', 'glist_pipeline.legacy.split_and_subtitle', 'glist_pipeline.legacy.split_and_subtitle_4'],
    hookspath=[],
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
    a.binaries,
    a.datas,
    [],
    name='GermanListeningCLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
