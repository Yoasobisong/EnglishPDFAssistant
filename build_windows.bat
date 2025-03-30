@echo off
echo === 开始打包PDF阅读助手为Windows可执行文件 ===

REM 设置代理（如果需要）
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
echo 已设置代理: %HTTP_PROXY%

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

REM 确保static目录存在
if not exist static mkdir static

REM 运行PyInstaller
echo 开始打包...
pyinstaller --clean pdf_assistant.spec

echo === 打包完成! ===

REM 检查构建目录是否存在
if exist dist\PDF阅读助手 (
    echo 可执行文件位于 dist\PDF阅读助手 目录
    echo - PDF阅读助手(GUI).exe: 图形界面应用
    echo - PDF阅读助手(Web).exe: 网页应用
    
    REM 打开输出目录(仅在本地环境)
    if "%CI%"=="" explorer dist\PDF阅读助手
    
    REM 创建ZIP压缩包
    echo 创建ZIP压缩包...
    cd dist
    if exist PDF阅读助手 (
        powershell -Command "Compress-Archive -Path 'PDF阅读助手\*' -DestinationPath 'EnglishPDFAssistant_Windows.zip' -Force"
        echo ZIP压缩包已创建: dist\EnglishPDFAssistant_Windows.zip
    ) else (
        echo 警告: PDF阅读助手目录不存在，无法创建ZIP
        dir
    )
    cd ..
) else (
    echo 警告: 构建目录不存在，请检查构建日志
    dir dist
)

if "%CI%"=="" pause 