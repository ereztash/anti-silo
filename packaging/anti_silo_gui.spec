# PyInstaller recipe for a local-only Anti-Silo GUI executable.
#
# Build from the repository root:
#   python -m pip install -e ".[desktop]"
#   pyinstaller packaging/anti_silo_gui.spec

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = collect_submodules("anti_silo")

a = Analysis(
    ["packaging/run_gui.py"],
    pathex=[],
    binaries=[],
    datas=[("contracts/default_config.json", "contracts")],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name="Anti-Silo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
