# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import sys

hidden = collect_submodules("pygame")
a = Analysis(["game.py"], pathex=[], binaries=[], datas=[("assets/fonts", "assets/fonts"), ("assets/loading", "assets/loading")], hiddenimports=hidden,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Numbermill",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False)
if sys.platform == "darwin":
    app = BUNDLE(exe, name="Numbermill.app", icon=None,
                 bundle_identifier="com.numbermill.game")
