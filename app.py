#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Import project modules
from src.gui.gui import start_gui
from src.utils.pdf_processor import PDFProcessor
from src.utils.translator import DeepseekTranslator
from src.utils.vocabulary_extractor import VocabularyExtractor
from src.api.api_service import start_api_server
from src.utils.translator_factory import TranslatorFactory

def main():
    """
    Main entry point for the application.
    """
    # Load environment variables
    load_dotenv(override=True)
    
    # 检查并打印API密钥信息（只显示前几位和后几位）
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if api_key:
        key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        print(f"已加载DEEPSEEK API密钥: {key_preview}")
    else:
        print("警告: 未找到DEEPSEEK_API_KEY环境变量。DeepSeek翻译功能将无法正常工作。")
    
    # 检查OpenRouter API密钥
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if openrouter_api_key:
        key_preview = f"{openrouter_api_key[:4]}...{openrouter_api_key[-4:]}" if len(openrouter_api_key) > 8 else "***"
        print(f"已加载OPENROUTER API密钥: {key_preview}")
    else:
        print("警告: 未找到OPENROUTER_API_KEY环境变量。OpenRouter翻译功能将无法正常工作。")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PDF阅读助手 - 处理PDF文件、翻译和提取词汇')
    parser.add_argument('--gui', action='store_true', help='启动图形用户界面')
    parser.add_argument('--api', action='store_true', help='启动API服务器')
    parser.add_argument('--pdf', type=str, help='PDF文件路径')
    parser.add_argument('--translate', action='store_true', help='翻译提取的文本')
    parser.add_argument('--vocabulary', action='store_true', help='提取文本中的词汇')
    parser.add_argument('--margin', type=int, default=30, help='笔记空间宽度百分比')
    parser.add_argument('--output', type=str, default='output', help='输出目录')
    parser.add_argument('--extract-method', type=str, 
                        choices=['pypdf2', 'pdfplumber', 'pdfminer', 'ocr', 'image', 'all'], 
                        default='pypdf2', help='文本提取方法')
    parser.add_argument('--translate-engine', type=str,
                        choices=[
                            'auto', 'deepseek', 'openrouter',  # 向后兼容的选项
                            'deepseek-reasoner', 'deepseek-chat', 'openrouter-deepseek'  # 新的模型选项
                        ],
                        default='auto', help='翻译引擎选择')
    parser.add_argument('--compare', action='store_true', help='比较所有提取方法的结果')
    parser.add_argument('--create-pdf', action='store_true', help='将处理后的图片转回PDF')
    parser.add_argument('--output-pdf', type=str, help='输出PDF文件路径 (默认为原文件名.pdf)')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Start GUI if requested
    if args.gui:
        start_gui()
        return
    
    # Start API server if requested
    if args.api:
        print("启动API服务器...")
        start_api_server(debug=True)
        return
    
    # Process PDF if provided
    if args.pdf:
        if not os.path.exists(args.pdf):
            print(f"错误: PDF文件不存在 - {args.pdf}")
            return
        
        # Process the PDF file
        try:
            print(f"处理PDF文件: {args.pdf}")
            pdf_processor = PDFProcessor(args.pdf, args.margin)
            
            # Convert PDF to images with note space
            image_paths = pdf_processor.convert_to_images_with_notes(args.output)
            print(f"已生成 {len(image_paths)} 张图片")
            
            # Create PDF from images if requested
            if args.create_pdf:
                # 使用原文件名作为输出文件名
                if args.output_pdf:
                    output_pdf = args.output_pdf
                else:
                    base_filename = os.path.splitext(os.path.basename(args.pdf))[0]
                    output_pdf = os.path.join(args.output, f'{base_filename}.pdf')
                
                print(f"正在将图片转换为PDF: {output_pdf}")
                pdf_processor.images_to_pdf(image_paths, output_pdf)
                print(f"PDF已生成: {output_pdf}")
            
            # Extract text
            if args.compare or args.extract_method == 'all':
                print("比较所有文本提取方法...")
                results = pdf_processor.extract_text_all_methods()
                
                # 保存所有提取结果
                for method, text in results.items():
                    method_text_path = os.path.join(args.output, f'extracted_text_{method}.txt')
                    with open(method_text_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    print(f"使用 {method} 提取的文本已保存到 {method_text_path}")
                
                # 使用默认方法进行后续处理
                text = results[PDFProcessor.EXTRACT_METHOD_PYPDF2]
                text_path = os.path.join(args.output, 'extracted_text.txt')
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"默认文本已保存到 {text_path}")
            else:
                print(f"使用 {args.extract_method} 提取文本...")
                text = pdf_processor.extract_text(method=args.extract_method)
                text_path = os.path.join(args.output, 'extracted_text.txt')
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"已提取文本并保存到 {text_path}")
            
            # Translate text if requested
            if args.translate:
                print(f"正在使用 {args.translate_engine} 引擎翻译文本...")
                # 根据用户选择的引擎创建翻译器
                translator = TranslatorFactory.create_translator(args.translate_engine)
                translation = translator.translate(text)
                translation_path = os.path.join(args.output, 'translation.txt')
                with open(translation_path, 'w', encoding='utf-8') as f:
                    f.write(translation)
                print(f"翻译完成并保存到 {translation_path}")
            
            # Extract vocabulary if requested
            if args.vocabulary:
                print("正在提取词汇...")
                vocabulary_extractor = VocabularyExtractor()
                vocabulary = vocabulary_extractor.extract_vocabulary(text)
                vocabulary_path = os.path.join(args.output, 'vocabulary.txt')
                with open(vocabulary_path, 'w', encoding='utf-8') as f:
                    f.write(vocabulary)
                print(f"词汇提取完成并保存到 {vocabulary_path}")
            
            print("处理完成")
            
        except Exception as e:
            print(f"错误: {e}")
            return
    else:
        # If no arguments are provided, show help
        if not (args.gui or args.api):
            parser.print_help()

if __name__ == "__main__":
    main() 