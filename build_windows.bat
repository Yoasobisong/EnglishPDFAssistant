@echo off
echo === 开始打包PDF阅读助手为Windows可执行文件 ===

REM 确保安装了必要的依赖
echo 正在检查并安装依赖...
pip install -r requirements.txt
pip install pyinstaller

REM 清理旧的build和dist目录
echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 创建.env文件（如果不存在）
if not exist .env (
    echo 创建示例.env文件...
    copy .env.example .env
)

REM 运行PyInstaller
echo 开始打包...
pyinstaller --clean pdf_assistant.spec

echo === 打包完成! ===
echo 可执行文件位于 dist\PDF阅读助手 目录
echo - PDF阅读助手(GUI).exe: 图形界面应用
echo - PDF阅读助手(Web).exe: 网页应用

REM 打开输出目录
explorer dist\PDF阅读助手

pause 