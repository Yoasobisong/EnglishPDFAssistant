# PDF阅读助手 GitHub Actions

此目录包含Windows可执行文件的构建配置，但我们不使用GitHub Actions进行自动构建。

## Windows可执行文件构建

您可以在本地运行`build_windows.bat`脚本来构建Windows可执行文件：

```bat
.\build_windows.bat
```

### 构建结果

- Windows可执行文件位于`dist\PDF阅读助手`目录
- 包含两个可执行文件：
  - `PDF阅读助手(GUI).exe` - 图形界面版本
  - `PDF阅读助手(Web).exe` - Web服务器版本 