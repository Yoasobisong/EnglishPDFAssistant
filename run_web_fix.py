#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Web应用程序的脚本，解决API路由问题
"""

import os
import sys
import time
import json
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect, Blueprint, send_file
from werkzeug.utils import secure_filename

# 确保当前目录在sys.path中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 直接导入PDFProcessor和TranslatorFactory，避免导入错误
from src.utils.pdf_processor import PDFProcessor
from src.utils.translator_factory import TranslatorFactory

# 创建Flask应用
app = Flask(__name__, 
            static_folder='src/web/static',
            template_folder='src/web/templates')

# 创建API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 配置
app.config['UPLOAD_FOLDER'] = os.path.join(current_dir, 'output')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制
app.config['SECRET_KEY'] = 'pdf_read_assistant_key'

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 任务状态字典
tasks = {}

def allowed_file(filename):
    """检查文件是否是允许的类型"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    # 检查是否是允许的文件类型
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 创建任务
        task_id = str(int(time.time()))
        tasks[task_id] = {
            'status': 'uploaded',
            'file': filepath,
            'filename': filename,
            'created': time.time(),
            'task_id': task_id  # 显式存储ID，方便传递
        }
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '文件上传成功',
            'next': url_for('process', task_id=task_id)
        })
    
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/process/<task_id>', methods=['GET'])
def process(task_id):
    """处理PDF页面"""
    if task_id not in tasks:
        return redirect(url_for('index'))
    
    return render_template('process.html', task=tasks[task_id])

# 重要：这里使用@app.route而不是@api_bp.route
@app.route('/api/process', methods=['POST'])
def api_process():
    """处理PDF API"""
    data = request.json
    task_id = data.get('task_id')
    extract_method = data.get('extract_method', PDFProcessor.EXTRACT_METHOD_IMAGE)
    translator_type = data.get('translator_type', TranslatorFactory.MODEL_AUTO)
    
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 启动处理线程
    thread = threading.Thread(
        target=process_pdf_thread,
        args=(task_id, task['file'], extract_method, translator_type),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'processing'
    })

# 诊断用API
@app.route('/api/debug', methods=['GET'])
def api_debug():
    """诊断用API"""
    return jsonify({
        'success': True,
        'message': 'API路由正常工作',
        'tasks': {k: {'status': v.get('status'), 'filename': v.get('filename')} 
                 for k, v in tasks.items()},
        'routes': [str(rule) for rule in app.url_map.iter_rules()]
    })

def process_pdf_thread(task_id, pdf_path, extract_method, translator_type):
    """后台处理PDF线程"""
    try:
        task = tasks[task_id]
        task['status'] = 'processing'
        task['progress'] = []
        task['current_step'] = 0
        task['total_steps'] = 5  # PDF处理、文本提取、翻译、词汇、生成翻译PDF
        
        # 创建以时间戳命名的子目录
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 创建目录: output/PDF文件名_时间戳/
        task_output_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{pdf_basename}_{timestamp}")
        os.makedirs(task_output_dir, exist_ok=True)
        
        task['output_dir'] = task_output_dir
        
        # 步骤1: 处理PDF
        task['progress'].append("步骤1/5: 正在处理PDF并转换为图片...")
        task['current_step'] = 1
        
        pdf_processor = PDFProcessor(pdf_path)
        image_paths = pdf_processor.convert_to_images_with_notes(task_output_dir)
        
        task['image_paths'] = image_paths
        task['progress'].append(f"✓ PDF处理完成，已生成 {len(image_paths)} 页图片")
        
        # 步骤2: 提取文本
        task['progress'].append(f"步骤2/5: 正在使用 {extract_method} 方法提取文本...")
        task['current_step'] = 2
        
        text = pdf_processor.extract_text(extract_method)
        text_path = os.path.join(task_output_dir, f'{pdf_basename}.txt')
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        task['extracted_text'] = text
        task['text_path'] = text_path
        task['progress'].append(f"✓ 文本提取完成，已保存到 {os.path.basename(text_path)}")
        
        # 步骤3: 翻译文本
        task['progress'].append("步骤3/5: 正在翻译文本...")
        task['current_step'] = 3
        
        try:
            translator = TranslatorFactory.create_translator(translator_type)
            translation = translator.translate(text)
            
            translation_path = os.path.join(task_output_dir, f'{pdf_basename}_translation.txt')
            with open(translation_path, 'w', encoding='gbk', errors='replace') as f:
                f.write(translation)
            
            task['translation'] = translation
            task['translation_path'] = translation_path
            task['progress'].append(f"✓ 翻译完成，已保存到 {os.path.basename(translation_path)}")
            
            # 步骤5: 生成翻译图片和PDF
            task['progress'].append("步骤5/5: 正在生成翻译PDF...")
            task['current_step'] = 5
            
            # 修改：不生成翻译图片，直接使用文本生成PDF
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.units import inch
            from reportlab.platypus.flowables import Spacer
            from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # 设置输出PDF路径
            translation_pdf_path = os.path.join(task_output_dir, f'{pdf_basename}_translation.pdf')
            
            try:
                # 尝试注册中文字体
                try:
                    # 尝试使用常见的中文字体
                    font_paths = [
                        "C:\\Windows\\Fonts\\simhei.ttf",  # Windows黑体
                        "C:\\Windows\\Fonts\\simsun.ttc",  # Windows宋体
                        "C:\\Windows\\Fonts\\msyh.ttf",    # Windows微软雅黑
                        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux文泉驿微米黑
                        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",    # Linux文泉驿正黑
                        "/usr/share/fonts/truetype/arphic/uming.ttc",      # Linux文鼎明体
                        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Google Noto Sans CJK
                        "/System/Library/Fonts/PingFang.ttc",  # macOS苹方
                        "/System/Library/Fonts/STHeiti Light.ttc",  # macOS黑体
                        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS冬青黑体
                        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
                    ]
                    
                    font_registered = False
                    registered_fonts = []
                    
                    for path in font_paths:
                        if os.path.exists(path):
                            font_name = os.path.basename(path).split('.')[0]
                            try:
                                pdfmetrics.registerFont(TTFont(font_name, path))
                                registered_fonts.append(font_name)
                                font_registered = True
                                print(f"成功注册字体: {font_name}")
                            except Exception as font_err:
                                print(f"注册字体 {font_name} 失败: {font_err}")
                    
                    # 记录已注册的字体
                    if registered_fonts:
                        print(f"已注册字体: {', '.join(registered_fonts)}")
                    else:
                        print("未能注册任何字体")
                except Exception as e:
                    print(f"注册字体失败: {e}")
                    font_registered = False
                
                # 创建PDF文档
                doc = SimpleDocTemplate(
                    translation_pdf_path,
                    pagesize=A4,
                    rightMargin=72,
                    leftMargin=72,
                    topMargin=72,
                    bottomMargin=72
                )
                
                # 创建样式
                styles = getSampleStyleSheet()
                if font_registered and registered_fonts:
                    primary_font = registered_fonts[0]  # 使用第一个成功注册的字体
                    title_style = ParagraphStyle(
                        'Title',
                        parent=styles['Title'],
                        fontName=primary_font,
                        fontSize=18,
                        alignment=1,  # 居中
                        spaceAfter=20,
                        encoding='utf-8'  # 确保使用UTF-8编码
                    )
                    normal_style = ParagraphStyle(
                        'Normal',
                        parent=styles['Normal'],
                        fontName=primary_font,
                        fontSize=12,
                        alignment=TA_JUSTIFY,
                        firstLineIndent=20,
                        encoding='utf-8'  # 确保使用UTF-8编码
                    )
                else:
                    # 默认样式
                    title_style = styles['Title']
                    normal_style = styles['Normal']
                
                # 创建内容
                story = []
                
                # 添加标题
                story.append(Paragraph(f"《{pdf_basename}》翻译", title_style))
                story.append(Spacer(1, 0.2 * inch))
                
                # 处理翻译文本，添加段落
                paragraphs = translation.split('\n')
                for para in paragraphs:
                    if para.strip():
                        # 修改：确保文本正确编码，防止字符丢失
                        try:
                            # 确保所有字符都能被正确处理
                            para_text = para
                            # 使用XML转义处理特殊字符
                            from xml.sax.saxutils import escape
                            para_text = escape(para_text)
                            story.append(Paragraph(para_text, normal_style))
                            story.append(Spacer(1, 0.1 * inch))
                        except Exception as e:
                            print(f"处理段落时出错: {e}")
                            # 如果处理失败，尝试简单处理后添加
                            story.append(Paragraph(str(para.encode('utf-8', errors='replace').decode('utf-8', errors='replace')), normal_style))
                            story.append(Spacer(1, 0.1 * inch))
                
                # 生成PDF
                doc.build(story)
                
                task['translation_pdf_path'] = translation_pdf_path
                task['progress'].append(f"✓ 翻译PDF生成完成，已保存到 {os.path.basename(translation_pdf_path)}")
            except Exception as e:
                error_msg = str(e)
                task['progress'].append(f"❌ 翻译PDF生成失败: {error_msg}")
                try:
                    # 备用方案：使用更简单的方法生成PDF
                    task['progress'].append("尝试使用简易方法生成PDF...")
                    
                    # 导入所需模块
                    from fpdf import FPDF
                    
                    # 创建PDF对象 - 使用Unicode支持
                    pdf = FPDF(orientation='P', unit='mm', format='A4')
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    
                    # 设置中文支持 - 使用fpdf2的内置字体支持
                    try:
                        # 尝试加载系统中文字体
                        font_found = False
                        font_paths = [
                            '/usr/share/fonts/truetype/arphic/uming.ttc',  # Arphic
                            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # WQY
                            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Droid
                            'C:\\Windows\\Fonts\\simhei.ttf',  # Windows黑体
                            'C:\\Windows\\Fonts\\simsun.ttc',  # Windows宋体
                            'C:\\Windows\\Fonts\\msyh.ttf',    # Windows微软雅黑
                        ]
                        
                        for font_path in font_paths:
                            if os.path.exists(font_path):
                                font_name = os.path.basename(font_path).split('.')[0]
                                pdf.add_font(font_name, '', font_path, uni=True)
                                pdf.set_font(font_name, '', 12)
                                font_found = True
                                task['progress'].append(f"✓ 成功加载字体: {font_name}")
                                break
                        
                        if not font_found:
                            # 使用FPDF2的内置字体，支持基本拉丁文和一些非拉丁文字符
                            pdf.set_font("Helvetica", size=12)
                            task['progress'].append("⚠️ 未找到中文字体，使用Helvetica，可能无法正确显示中文")
                            
                    except Exception as font_error:
                        task['progress'].append(f"⚠️ 字体加载失败: {str(font_error)}，使用默认字体")
                        pdf.set_font("Helvetica", size=12)
                    
                    # 添加标题
                    original_font_size = pdf.font_size
                    pdf.set_font_size(18)
                    title = f"《{pdf_basename}》翻译"
                    
                    # 计算标题宽度并居中
                    title_width = pdf.get_string_width(title)
                    page_width = pdf.w - 2*pdf.l_margin
                    pdf.set_x((page_width - title_width) / 2 + pdf.l_margin)
                    
                    pdf.cell(title_width, 10, title, ln=1, align='C')
                    pdf.ln(10)
                    
                    # 重新设置正文字体大小
                    pdf.set_font_size(original_font_size)
                    
                    # 添加正文内容
                    paragraphs = translation.split('\n')
                    for para in paragraphs:
                        if para.strip():
                            # 确保参数是字符串类型
                            para_text = str(para)
                            # 多行文本
                            pdf.multi_cell(0, 8, para_text)
                            pdf.ln(4)
                    
                    # 保存PDF
                    pdf.output(translation_pdf_path)
                    
                    task['translation_pdf_path'] = translation_pdf_path
                    task['progress'].append(f"✓ 使用简易方法生成翻译PDF完成，已保存到 {os.path.basename(translation_pdf_path)}")
                except Exception as e2:
                    task['progress'].append(f"❌ 简易方法生成PDF也失败: {str(e2)}")
                    # 最后尝试原始图片转PDF方法
                    try:
                        task['progress'].append("尝试使用原始图片转PDF方法...")
                        # 将原文和翻译生成对照PDF
                        pdf_processor.translation_to_pdf(
                            text, 
                            translation, 
                            translation_pdf_path, 
                            title=f"《{pdf_basename}》翻译",
                            only_translation=True  # 只包含翻译内容，不包含原文
                        )
                        task['translation_pdf_path'] = translation_pdf_path
                        task['progress'].append(f"✓ 使用图片转PDF方法生成翻译完成，已保存到 {os.path.basename(translation_pdf_path)}")
                    except Exception as e3:
                        task['progress'].append(f"❌ 所有PDF生成方法均失败: {str(e3)}")
            
        except Exception as e:
            error_msg = str(e)
            task['progress'].append(f"❌ 翻译失败: {error_msg}")
            
            # 继续执行后续步骤
            task['progress'].append("继续执行下一步...")
        
        # 步骤4: 提取词汇
        task['progress'].append("步骤4/5: 正在提取词汇...")
        task['current_step'] = 4
        
        try:
            # 使用翻译器的词汇提取功能
            translator = TranslatorFactory.create_translator(translator_type)
            if hasattr(translator, 'extract_vocabulary'):
                vocabulary = translator.extract_vocabulary(text)
            else:
                # 使用通用的词汇提取器
                from src.utils.vocabulary_extractor import VocabularyExtractor
                vocabulary_extractor = VocabularyExtractor()
                vocabulary = vocabulary_extractor.extract(text)
            
            vocabulary_path = os.path.join(task_output_dir, f'{pdf_basename}_vocabulary.txt')
            with open(vocabulary_path, 'w', encoding='gbk', errors='replace') as f:
                f.write(vocabulary)
            
            task['vocabulary'] = vocabulary
            task['vocabulary_path'] = vocabulary_path
            task['progress'].append(f"✓ 词汇提取完成，已保存到 {os.path.basename(vocabulary_path)}")
        except Exception as e:
            task['progress'].append(f"❌ 词汇提取失败: {str(e)}")
        
        # 处理完成
        task['status'] = 'completed'
        task['completed'] = time.time()
        task['progress'].append("✓✓✓ 所有处理步骤已完成！✓✓✓")
    
    except Exception as e:
        task = tasks.get(task_id, {'status': 'error', 'error': str(e)})
        task['status'] = 'error'
        task['error'] = str(e)
        if 'progress' in task:
            task['progress'].append(f"❌ 处理过程中出错: {str(e)}")
        else:
            task['progress'] = [f"❌ 处理过程中出错: {str(e)}"]

@app.route('/api/task/<task_id>', methods=['GET'])
def api_task_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    return jsonify({
        'task_id': task_id,
        'status': task.get('status'),
        'progress': task.get('progress', []),
        'current_step': task.get('current_step', 0),
        'total_steps': task.get('total_steps', 4),
        'has_translation': 'translation' in task,
        'has_vocabulary': 'vocabulary' in task,
        'image_count': len(task.get('image_paths', [])) if 'image_paths' in task else 0
    })

@app.route('/result/<task_id>', methods=['GET'])
def result(task_id):
    """结果页面"""
    if task_id not in tasks:
        return redirect(url_for('index'))
    
    task = tasks[task_id]
    if task['status'] != 'completed' and task['status'] != 'error':
        return redirect(url_for('process', task_id=task_id))
    
    return render_template('result.html', task=task)

@app.route('/api/image/<task_id>/<int:index>', methods=['GET'])
def api_get_image(task_id, index):
    """获取处理后的图片"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    if 'image_paths' not in task or index >= len(task['image_paths']):
        return jsonify({'error': '图片不存在'}), 404
    
    image_path = task['image_paths'][index]
    directory, filename = os.path.split(image_path)
    return send_from_directory(directory, filename)

@app.route('/api/text/<task_id>/<text_type>', methods=['GET'])
def api_get_text(task_id, text_type):
    """获取处理后的文本"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    if text_type == 'extracted' and 'extracted_text' in task:
        return jsonify({'text': task['extracted_text']})
    elif text_type == 'translation' and 'translation' in task:
        return jsonify({'text': task['translation']})
    elif text_type == 'vocabulary' and 'vocabulary' in task:
        return jsonify({'text': task['vocabulary']})
    
    return jsonify({'error': '文本不存在'}), 404

@app.route('/api/export/<task_id>', methods=['POST'])
def api_export_pdf(task_id):
    """导出PDF API"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    if 'image_paths' not in task:
        return jsonify({'error': '没有可用的图片'}), 404
    
    data = request.json
    selected_indices = data.get('selected_indices', [])
    
    if not selected_indices:
        return jsonify({'error': '未选择任何页面'}), 400
    
    try:
        # 获取选中的图片路径
        selected_images = [task['image_paths'][i] for i in selected_indices if i < len(task['image_paths'])]
        
        if not selected_images:
            return jsonify({'error': '选择的页面无效'}), 400
        
        # 验证所有图片是否存在
        missing_images = [img for img in selected_images if not os.path.exists(img)]
        if missing_images:
            error_msg = f"以下图片文件不存在: {', '.join(missing_images)}"
            print(error_msg)
            return jsonify({'error': error_msg}), 404
            
        # 使用PDF文件名和时间戳作为导出文件名
        if 'output_dir' in task and os.path.exists(task['output_dir']):
            output_dir = task['output_dir']
        else:
            output_dir = app.config['UPLOAD_FOLDER']
            os.makedirs(output_dir, exist_ok=True)
            
        # 提取原始PDF文件名
        pdf_path = task.get('file', '')  # 使用'file'字段获取原始文件路径
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0] if pdf_path else 'output'
        
        output_path = os.path.join(output_dir, f'{pdf_basename}_export.pdf')
        
        # 调试信息
        print(f"创建PDF文件: {output_path}")
        print(f"使用以下图片: {selected_images}")
        
        # 使用PDFProcessor将图像导出为PDF
        from reportlab.lib.pagesizes import letter
        
        # 直接使用reportlab创建PDF
        try:
            from reportlab.pdfgen import canvas
            from PIL import Image
            
            # 创建输出目录（如果不存在）
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 获取第一张图片的尺寸
            first_img = Image.open(selected_images[0])
            img_width, img_height = first_img.size
            first_img.close()
            
            # 创建PDF画布
            c = canvas.Canvas(output_path, pagesize=(img_width, img_height))
            
            # 添加每张图片到PDF
            for img_path in selected_images:
                img = Image.open(img_path)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                width, height = img.size
                c.setPageSize((width, height))
                c.drawImage(img_path, 0, 0, width=width, height=height)
                c.showPage()
                img.close()
            
            # 保存PDF
            c.save()
            result_path = output_path
            
            print(f"PDF已保存到: {result_path}")
        except Exception as e:
            print(f"直接创建PDF失败: {e}")
            # 尝试使用PDFProcessor
            pdf_processor = PDFProcessor('')
            result_path = pdf_processor.images_to_pdf(selected_images, output_path)
        
        # 确保文件存在
        if not os.path.exists(result_path):
            error_msg = f"PDF文件未找到: {result_path}"
            print(error_msg)
            return jsonify({'error': error_msg}), 500
        
        # 更新任务信息
        task['export_pdf'] = result_path
        
        # 调试信息
        print(f"PDF导出成功: {result_path}")
        print(f"文件大小: {os.path.getsize(result_path)} 字节")
        
        return jsonify({
            'success': True,
            'message': 'PDF导出成功',
            'pdf_path': os.path.basename(result_path),
            'download_url': url_for('download_file', task_id=task_id, file_type='pdf')
        })
    
    except Exception as e:
        import traceback
        print(f"PDF导出错误: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'PDF导出失败: {str(e)}'}), 500

@app.route('/download/<task_id>/<file_type>', methods=['GET'])
def download_file(task_id, file_type):
    """下载任务生成的文件"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    if task['status'] != 'completed':
        return jsonify({'error': '任务尚未完成'}), 400
    
    file_path = None
    filename = None
    
    if file_type == 'text':
        # 下载提取的文本
        file_path = task.get('text_path')
        filename = os.path.basename(file_path) if file_path else 'extracted_text.txt'
    elif file_type == 'translation':
        # 下载翻译文本
        file_path = task.get('translation_path')
        filename = os.path.basename(file_path) if file_path else 'translation.txt'
    elif file_type == 'translation_img':
        # 下载翻译图片
        file_path = task.get('translation_img_path')
        filename = os.path.basename(file_path) if file_path else 'translation.png'
    elif file_type == 'translation_pdf':
        # 下载翻译PDF
        file_path = task.get('translation_pdf_path')
        filename = os.path.basename(file_path) if file_path else 'translation.pdf'
    elif file_type == 'vocabulary':
        # 下载词汇表
        file_path = task.get('vocabulary_path')
        filename = os.path.basename(file_path) if file_path else 'vocabulary.txt'
    elif file_type == 'pdf':
        # 下载导出的PDF
        file_path = task.get('export_pdf')
        filename = os.path.basename(file_path) if file_path else 'exported.pdf'
    else:
        return jsonify({'error': '不支持的文件类型'}), 400
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

# 注册简单测试API路由
@app.route('/api/test', methods=['GET'])
def api_test():
    """简单测试API端点"""
    return jsonify({
        'status': 'success',
        'message': 'API测试成功'
    })

@app.route('/test', methods=['GET'])
def test_page():
    """测试页面"""
    return """
    <html>
    <head>
        <title>API测试</title>
    </head>
    <body>
        <h1>API测试页面</h1>
        <p>可以直接测试 API 路由</p>
        <button onclick="testApi()">测试 API</button>
        <div id="result" style="margin-top: 20px; padding: 10px; background-color: #f0f0f0;"></div>
        
        <script>
        function testApi() {
            fetch('/api/test')
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').innerText = JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('result').innerText = 'Error: ' + error;
            });
        }
        </script>
    </body>
    </html>
    """

# 添加调试信息的路由
@app.route('/debug')
def debug_info():
    """显示调试信息"""
    route_info = []
    for rule in app.url_map.iter_rules():
        route_info.append({
            'endpoint': rule.endpoint,
            'methods': [m for m in rule.methods if m not in ('HEAD', 'OPTIONS')],
            'rule': str(rule)
        })
    
    return jsonify({
        'routes': route_info,
        'tasks': {k: {'status': v.get('status'), 'filename': v.get('filename')} 
                 for k, v in tasks.items()},
    })

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    # 打印所有注册的路由
    print("已注册的路由:")
    for rule in app.url_map.iter_rules():
        methods = [m for m in rule.methods if m not in ('HEAD', 'OPTIONS')]
        print(f"{rule} - {methods}")
    
    print(f"启动修复版Web应用，访问地址: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"访问 http://{host if host != '0.0.0.0' else 'localhost'}:{port}/test 进行API测试")
    print(f"访问 http://{host if host != '0.0.0.0' else 'localhost'}:{port}/debug 查看调试信息")
    
    app.run(host=host, port=port, debug=debug) 