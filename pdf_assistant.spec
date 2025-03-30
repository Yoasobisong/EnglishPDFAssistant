# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 添加静态文件和模板
added_files = []

# 检查目录是否存在并添加
if os.path.exists('static'):
    added_files.append(('static', 'static'))
if os.path.exists('src/web/static'):
    added_files.append(('src/web/static', 'src/web/static'))
if os.path.exists('src/web/templates'):
    added_files.append(('src/web/templates', 'src/web/templates'))
if os.path.exists('.env.example'):
    added_files.append(('.env.example', '.'))
if os.path.exists('桃花.png'):
    added_files.append(('桃花.png', '.'))
if os.path.exists('玫瑰.png'):
    added_files.append(('玫瑰.png', '.'))

print(f"Added files: {added_files}")

# 添加隐藏导入
hidden_imports = collect_submodules('tkinter') + [
    'PIL._tkinter_finder',
    'cv2',
    'numpy',
    'werkzeug.exceptions',
    'flask.cli',
    'flask_cors',
    'pdfplumber',
    'pdfminer',
    'pdfminer.high_level',
    'pytesseract',
    'pdf2image'
]

# 分析应用程序
a = Analysis(
    ['app.py'],  # 主程序入口
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 额外创建一个Web应用入口
b = Analysis(
    ['run_web_fix.py'],  # Web应用入口
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建PYZ归档
pyz_a = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
pyz_b = PYZ(b.pure, b.zipped_data, cipher=block_cipher)

# 设置图标路径
gui_icon = '桃花.png' if os.path.exists('桃花.png') else None
web_icon = '玫瑰.png' if os.path.exists('玫瑰.png') else None

# GUI应用可执行文件
exe_a = EXE(
    pyz_a,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDF Reading Assistant (GUI)',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=gui_icon,
)

# Web应用可执行文件
exe_b = EXE(
    pyz_b,
    b.scripts,
    [],
    exclude_binaries=True,
    name='PDF Reading Assistant (Web)',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Web应用保留控制台输出
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=web_icon,
)

# 收集所有文件到一个目录
coll = COLLECT(
    exe_a,
    a.binaries,
    a.zipfiles,
    a.datas,
    exe_b,
    b.binaries,
    b.zipfiles,
    b.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF Reading Assistant',
) 