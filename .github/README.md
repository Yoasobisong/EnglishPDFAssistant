# PDF阅读助手 GitHub Actions

此目录包含自动构建脚本，用于生成可执行程序。

## 工作流说明

1. **Windows可执行文件构建** (build_windows.yml)
   - 构建Windows版可执行文件
   - 打包为ZIP文件
   - 上传到GitHub Releases

2. **Android APK构建** (build_android.yml)
   - 构建Android版APK
   - 上传到GitHub Releases

## 如何使用

1. 手动触发构建：
   - 访问项目的Actions标签页
   - 选择相应的工作流
   - 点击"Run workflow"

2. 发布新版本时自动构建：
   - 创建新的GitHub Release
   - 工作流会自动运行，并将构建结果上传到该Release

## 构建结果

- Windows: `EnglishPDFAssistant_Windows.zip`
- Android: `PDFAssistant-[日期]-[版本].apk` 