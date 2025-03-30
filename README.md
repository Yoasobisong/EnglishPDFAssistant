# EnglishPDFAssistant

一个功能强大的PDF阅读辅助工具，可自动提取文本、翻译内容、分析词汇并生成带有注释的PDF文件。

## 功能特点

- **自动文本提取**：支持多种提取方法（图像识别、PyPDF2、PDFPlumber、PDFMiner、OCR）
- **智能翻译**：集成多种翻译引擎（DeepSeek Reasoner、DeepSeek Chat、OpenRouter）
- **词汇分析**：自动识别重要词汇并提供中文解释和例句
- **页面注释**：在PDF页面上添加翻译和注释，方便阅读学习
- **导出功能**：将处理结果导出为新的PDF文件，保留原文格式
- **Web界面**：直观易用的Web界面，无需编程知识

## 使用方法

### 网页版

1. 运行应用程序：`python run_web_fix.py`
2. 在浏览器中访问：`http://localhost:5000`
3. 上传PDF文件并选择处理选项
4. 等待处理完成后查看结果

### GUI版

1. 运行GUI应用：`python app.py`
2. 从界面上传PDF文件
3. 配置处理选项并开始处理
4. 查看和导出处理结果

## 环境要求

- Python 3.8+
- 依赖库：Flask, PyPDF2, PDFPlumber, PDFMiner, PIL, OpenCV等
- API密钥：使用翻译功能需要配置相应的API密钥

## 安装说明

1. 克隆仓库：`git clone https://github.com/yourusername/EnglishPDFAssistant.git`
2. 进入目录：`cd EnglishPDFAssistant`
3. 创建虚拟环境：`python -m venv venv`
4. 激活环境：
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
5. 安装依赖：`pip install -r requirements.txt`
6. 配置API密钥：创建`.env`文件并设置所需的API密钥
7. 运行应用：`python run_web_fix.py`

## 许可证

本项目采用MIT许可证 

