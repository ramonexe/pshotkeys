# build.spec — PSHotkeys v2
# Rodar: pyinstaller build.spec
# Antes do build, rode: python src/main.py uma vez para gerar assets/icon.ico

import os
block_cipher = None

from PyInstaller.building.build_main import Analysis, PYZ, EXE

_assets_src = os.path.join("assets")
_datas = []
if os.path.exists(_assets_src):
    _datas.append((_assets_src, "assets"))

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "win32com.client",
        "win32com.server",
        "pyautogui",
        "psutil",
        "psutil._pswindows",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageTk",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.simpledialog",
        "winreg",
    ],
    excludes=["matplotlib", "numpy", "scipy", "pandas"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="PSHotkeys",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=_icon,
    uac_admin=False,
    onefile=True,
)
