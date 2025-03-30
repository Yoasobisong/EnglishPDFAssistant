#!/bin/bash

echo "=== PDF阅读助手移动应用打包工具 ==="
echo "此脚本将帮助您打包Android版本的PDF阅读助手"

# 设置HTTP代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
echo "已设置代理: $HTTP_PROXY"

# 确保有正确的Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3"
    exit 1
fi

# 确保安装了依赖
echo "安装必要的依赖..."
pip install -r requirements.txt
pip install kivy buildozer

# 确保有Buildozer配置文件
if [ ! -f "buildozer.spec" ]; then
    echo "错误: 未找到buildozer.spec文件"
    exit 1
fi

# 创建虚拟环境(可选)
if [ ! -d "venv_mobile" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv_mobile
    source venv_mobile/bin/activate
    pip install kivy buildozer pillow
fi

# 确保正确的Android SDK/NDK设置
if [ -z "$ANDROID_HOME" ]; then
    echo "警告: ANDROID_HOME环境变量未设置"
    echo "      Buildozer将尝试自动下载Android SDK，这可能需要一些时间"
    read -p "是否继续? (y/n): " choice
    if [ "$choice" != "y" ]; then
        exit 0
    fi
fi

# 准备图标文件夹
if [ ! -d "assets" ]; then
    mkdir -p assets
fi

# 拷贝图标文件(如果有)
if [ -f "static/icon.png" ]; then
    cp static/icon.png assets/
fi

# 主入口文件设置
echo "设置移动应用入口..."
if [ ! -f "main.py" ]; then
    echo "创建main.py入口文件，指向mobile_app.py..."
    echo '#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from mobile_app import PDFAssistantApp

if __name__ == "__main__":
    PDFAssistantApp().run()
' > main.py
    chmod +x main.py
fi

# 运行Buildozer
echo "开始构建APK..."
buildozer android debug

# 检查结果
if [ $? -eq 0 ]; then
    echo "===== 构建成功! ====="
    echo "APK文件位于 bin/pdfassistant-0.1-debug.apk"
    echo "您可以将APK文件安装到Android设备上"
    
    # 可选：显示adb命令安装
    echo "使用以下命令安装APK:"
    echo "adb install -r bin/pdfassistant-0.1-debug.apk"
    
    # 可选：直接安装到设备
    read -p "是否直接安装到已连接设备? (y/n): " install
    if [ "$install" == "y" ]; then
        adb install -r bin/pdfassistant-0.1-debug.apk
    fi
else
    echo "===== 构建失败 ====="
    echo "请检查错误信息"
fi

echo "完成!" 