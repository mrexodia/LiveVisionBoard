# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        ('data/ffmpeg-darwin-arm64', 'data'),
        ('data/ffmpeg-darwin-x64', 'data'),
    ],
    datas=[
        ('data/icon.png', 'data'),
        ('data/black.jpg', 'data'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LiveVisionBoard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LiveVisionBoard',
)
app = BUNDLE(
    coll,
    name='LiveVisionBoard.app',
    icon='data/icon.icns',
    bundle_identifier='pl.ogilvie.LiveVisionBoard',
)
