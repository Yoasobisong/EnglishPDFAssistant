#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect
from werkzeug.utils import secure_filename

# 添加父目录到 path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from utils.pdf_processor import PDFProcessor
from utils.translator_factory import TranslatorFactory
from utils.vocabulary_extractor import VocabularyExtractor

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 配置
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'output')
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
            'created': time.time()
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

def process_pdf_thread(task_id, pdf_path, extract_method, translator_type):
    """后台处理PDF线程"""
    task = tasks[task_id]
    task['status'] = 'processing'
    task['progress'] = []
    task['current_step'] = 0
    task['total_steps'] = 4  # PDF处理、文本提取、翻译、词汇
    
    output_dir = app.config['UPLOAD_FOLDER']
    
    try:
        # 步骤1: 处理PDF
        task['progress'].append("步骤1/4: 正在处理PDF并转换为图片...")
        task['current_step'] = 1
        
        pdf_processor = PDFProcessor(pdf_path)
        image_paths = pdf_processor.convert_to_images_with_notes(output_dir)
        
        task['image_paths'] = image_paths
        task['progress'].append(f"✓ PDF处理完成，已生成 {len(image_paths)} 页图片")
        
        # 步骤2: 提取文本
        task['progress'].append(f"步骤2/4: 正在使用 {extract_method} 方法提取文本...")
        task['current_step'] = 2
        
        text = pdf_processor.extract_text(extract_method)
        text_path = os.path.join(output_dir, f'{task_id}_extracted_text.txt')
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        task['extracted_text'] = text
        task['text_path'] = text_path
        task['progress'].append(f"✓ 文本提取完成，已保存到 {os.path.basename(text_path)}")
        
        # 步骤3: 翻译文本
        task['progress'].append("步骤3/4: 正在翻译文本...")
        task['current_step'] = 3
        
        try:
            translator = TranslatorFactory.create_translator(translator_type)
            translation = translator.translate(text)
            
            translation_path = os.path.join(output_dir, f'{task_id}_translation.txt')
            with open(translation_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            
            task['translation'] = translation
            task['translation_path'] = translation_path
            task['progress'].append(f"✓ 翻译完成，已保存到 {os.path.basename(translation_path)}")
        except Exception as e:
            error_msg = str(e)
            task['progress'].append(f"❌ 翻译失败: {error_msg}")
            
            # 继续执行后续步骤
            task['progress'].append("继续执行下一步...")
        
        # 步骤4: 提取词汇
        task['progress'].append("步骤4/4: 正在提取词汇...")
        task['current_step'] = 4
        
        try:
            # 使用翻译器的词汇提取功能
            translator = TranslatorFactory.create_translator(translator_type)
            if hasattr(translator, 'extract_vocabulary'):
                vocabulary = translator.extract_vocabulary(text)
            else:
                # 使用通用的词汇提取器
                vocabulary_extractor = VocabularyExtractor()
                vocabulary = vocabulary_extractor.extract(text)
            
            vocabulary_path = os.path.join(output_dir, f'{task_id}_vocabulary.txt')
            with open(vocabulary_path, 'w', encoding='utf-8') as f:
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
        task['status'] = 'error'
        task['error'] = str(e)
        task['progress'].append(f"❌ 处理过程中出错: {str(e)}")

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
        
        # 设置PDF保存路径
        pdf_filename = f"{task_id}_export.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        # 创建PDF处理器
        pdf_processor = PDFProcessor(task['file'])
        
        # 转换图片为PDF
        result_path = pdf_processor.images_to_pdf(selected_images, pdf_path)
        
        # 更新任务信息
        task['export_pdf'] = result_path
        
        return jsonify({
            'success': True,
            'message': 'PDF导出成功',
            'pdf_path': os.path.basename(result_path),
            'download_url': url_for('download_file', filename=os.path.basename(result_path))
        })
    
    except Exception as e:
        return jsonify({'error': f'PDF导出失败: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 