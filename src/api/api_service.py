#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import tempfile
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import project modules
from utils.pdf_processor import PDFProcessor
from utils.translator import DeepseekTranslator
from utils.vocabulary_extractor import VocabularyExtractor

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='../../static')
CORS(app)  # Enable CORS for all routes

# Create a temporary directory for uploaded files
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create output directory if it doesn't exist
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return jsonify({"status": "ok"})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Endpoint for uploading PDF files.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "path": file_path
        })
    else:
        return jsonify({"error": "Only PDF files are allowed"}), 400

@app.route('/api/process', methods=['POST'])
def process_pdf():
    """
    Endpoint for processing PDF files.
    """
    # Get request data
    data = request.json
    file_path = data.get('file_path')
    margin = data.get('margin', 30)
    extract_method = data.get('extract_method', PDFProcessor.EXTRACT_METHOD_PYPDF2)
    compare_methods = data.get('compare_methods', False)
    
    # Validate input
    if not file_path:
        return jsonify({"error": "File path is required"}), 400
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    try:
        # 创建以时间戳命名的子目录
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
        
        # 创建目录: output/PDF文件名_时间戳/
        task_output_dir = os.path.join(OUTPUT_FOLDER, f"{pdf_basename}_{timestamp}")
        os.makedirs(task_output_dir, exist_ok=True)
        
        # Process the PDF file
        pdf_processor = PDFProcessor(file_path, margin)
        
        # Convert PDF to images with note space
        image_paths = pdf_processor.convert_to_images_with_notes(task_output_dir)
        
        # Extract text content from PDF
        text_results = {}
        text_content = ""
        
        if compare_methods:
            # Use all methods and compare results
            text_results = pdf_processor.extract_text_all_methods()
            text_content = text_results.get(PDFProcessor.EXTRACT_METHOD_PYPDF2, "")
            
            # Save all extraction results
            for method, text in text_results.items():
                method_text_path = os.path.join(task_output_dir, f'{pdf_basename}_{method}.txt')
                with open(method_text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
        else:
            # Use selected method
            text_content = pdf_processor.extract_text(method=extract_method)
            text_results[extract_method] = text_content
        
        # Save extracted text
        text_path = os.path.join(task_output_dir, f'{pdf_basename}.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Translate text
        translator = DeepseekTranslator()
        translation = translator.translate(text_content)
        
        # Save translated text
        translation_path = os.path.join(task_output_dir, f'{pdf_basename}_translation.txt')
        with open(translation_path, 'w', encoding='utf-8') as f:
            f.write(translation)
        
        # Extract vocabulary
        vocabulary_extractor = VocabularyExtractor()
        vocabulary = vocabulary_extractor.extract_vocabulary(text_content)
        
        # Save vocabulary
        vocabulary_path = os.path.join(task_output_dir, f'{pdf_basename}_vocabulary.txt')
        with open(vocabulary_path, 'w', encoding='utf-8') as f:
            f.write(vocabulary)
        
        # Return success response
        return jsonify({
            "success": True,
            "image_paths": image_paths,
            "text_path": text_path,
            "translation_path": translation_path,
            "vocabulary_path": vocabulary_path,
            "output_dir": task_output_dir
        })
    
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/extraction-methods', methods=['GET'])
def get_extraction_methods():
    """
    Endpoint to get available text extraction methods.
    """
    methods = [
        {"id": PDFProcessor.EXTRACT_METHOD_PYPDF2, "name": "PyPDF2 (默认)", "description": "快速但格式支持有限"},
        {"id": PDFProcessor.EXTRACT_METHOD_PDFPLUMBER, "name": "PDFPlumber", "description": "更好的格式支持"},
        {"id": PDFProcessor.EXTRACT_METHOD_PDFMINER, "name": "PDFMiner", "description": "较好的文本提取能力"},
        {"id": PDFProcessor.EXTRACT_METHOD_IMAGE, "name": "图片提取", "description": "通过PDF图片提取文本，跨平台友好"},
        {"id": PDFProcessor.EXTRACT_METHOD_OCR, "name": "OCR", "description": "光学字符识别，适用于扫描文档"}
    ]
    
    return jsonify({"methods": methods})

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """
    Endpoint for translating text.
    """
    # Get request data
    data = request.json
    file_path = data.get('file_path')
    text = data.get('text')
    
    # Validate input
    if not file_path and not text:
        return jsonify({"error": "Either file_path or text is required"}), 400
    
    try:
        # Get text from file if file_path is provided
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Translate the text
        translator = DeepseekTranslator()
        translation = translator.translate(text)
        
        # Save translation
        translation_path = os.path.join(OUTPUT_FOLDER, 'translation.txt')
        with open(translation_path, 'w', encoding='utf-8') as f:
            f.write(translation)
        
        return jsonify({
            "message": "Text translated successfully",
            "translation_path": translation_path,
            "translation": translation[:1000] + "..." if len(translation) > 1000 else translation
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vocabulary', methods=['POST'])
def extract_vocabulary():
    """
    Endpoint for extracting vocabulary.
    """
    # Get request data
    data = request.json
    file_path = data.get('file_path')
    text = data.get('text')
    
    # Validate input
    if not file_path and not text:
        return jsonify({"error": "Either file_path or text is required"}), 400
    
    try:
        # Get text from file if file_path is provided
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Extract vocabulary
        vocabulary_extractor = VocabularyExtractor()
        vocabulary = vocabulary_extractor.extract_vocabulary(text)
        
        # Save vocabulary
        vocabulary_path = os.path.join(OUTPUT_FOLDER, 'vocabulary.txt')
        with open(vocabulary_path, 'w', encoding='utf-8') as f:
            f.write(vocabulary)
        
        return jsonify({
            "message": "Vocabulary extracted successfully",
            "vocabulary_path": vocabulary_path,
            "vocabulary": vocabulary[:1000] + "..." if len(vocabulary) > 1000 else vocabulary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    Endpoint for downloading processed files.
    """
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/images-to-pdf', methods=['POST'])
def convert_images_to_pdf():
    """
    Endpoint for converting images to PDF.
    """
    # Get request data
    data = request.json
    image_paths = data.get('image_paths', [])
    custom_page_size = data.get('page_size')
    
    # Validate input
    if not image_paths or len(image_paths) == 0:
        return jsonify({"error": "No image paths provided"}), 400
    
    # Ensure all images exist
    missing_images = [path for path in image_paths if not os.path.exists(path)]
    if missing_images:
        return jsonify({
            "error": "Some images do not exist",
            "missing_images": missing_images
        }), 404
    
    try:
        # Create a PDF processor (use the first image for initialization)
        pdf_processor = PDFProcessor(image_paths[0])
        
        # Output PDF path
        output_pdf = os.path.join(OUTPUT_FOLDER, 'output.pdf')
        
        # Convert images to PDF
        page_size = tuple(custom_page_size) if custom_page_size else None
        pdf_path = pdf_processor.images_to_pdf(image_paths, output_pdf, page_size)
        
        return jsonify({
            "message": "Images converted to PDF successfully",
            "pdf_path": pdf_path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_api_server(host='0.0.0.0', port=5000, debug=False):
    """
    Start the Flask API server.
    """
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    start_api_server(debug=True) 