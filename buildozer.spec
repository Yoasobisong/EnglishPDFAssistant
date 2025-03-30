[app]

# 应用程序名称
title = PDF阅读助手

# 应用程序包名
package.name = pdfassistant

# 应用程序包域
package.domain = org.pdfassistant

# 源码所在文件夹
source.dir = .

# 应用入口文件
source.include_exts = py,png,jpg,kv,atlas

# 忽略的文件模式
source.exclude_dirs = tests, bin, .git, __pycache__, venv

# 忽略的文件扩展名
source.exclude_patterns = license,README.md,*.spec,*.bat,*.sh,*.txt

# 需要包含的文件/文件夹
source.include_patterns = assets/*,src/*,*.kv

# 程序版本
version = 0.1

# 程序需要的权限
permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 应用程序要求
requirements = python3,kivy,pillow,requests,pyjnius

# 图标
icon.filename = static/icon.png

# 方向
orientation = portrait

# 全屏
fullscreen = 0

# Android版本
android.api = 33

# MinAPI
android.minapi = 21

# NDK版本
android.ndk = 25b

# SDK
android.sdk = 33

# 签署应用程序
android.keystore = pdf_assistant.keystore
android.keyalias = pdfassistant

# 自动生成keystore
android.accept_sdk_license = True

# 预编译的依赖项
#p4a.local_recipes = 

# 额外的构建配置
#p4a.hook =

# 部署目标
#p4a.bootstrap = sdl2

[buildozer]
# 构建输出目录
build_dir = ./.buildozer

# 详细日志
log_level = 2

# 警告
warn_on_root = 1

# 安装APK
install_timeout = 60 