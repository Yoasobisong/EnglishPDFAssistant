#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from utils.pdf_processor import PDFProcessor
from utils.translator import DeepseekTranslator
from utils.vocabulary_extractor import VocabularyExtractor
from utils.translator_factory import TranslatorFactory

class PDFGUI:
    """
    A simple GUI for the PDF processing application.
    """
    
    def __init__(self, root):
        """
        Initialize the GUI.
        
        Args:
            root (tk.Tk): The root Tkinter window
        """
        self.root = root
        self.root.title("PDF阅读助手")
        self.root.geometry("800x600")
        
        # Instance variables
        self.pdf_path = None
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'output')
        self.image_paths = []
        self.current_image_index = 0
        self.extracted_text = ""
        self.translation_text = ""
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Create the main frame
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the menu
        self.create_menu()
        
        # Create the top frame
        self.top_frame = ttk.Frame(self.main_frame)
        self.top_frame.pack(fill=tk.X, pady=5)
        
        # Create the file selection elements
        self.create_file_selection()
        
        # Create the image display area
        self.create_image_display()
        
        # Create the control buttons
        self.create_control_buttons()
        
        # Create the text display area
        self.create_text_display()
        
        # Create the status bar
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_menu(self):
        """
        Create the application menu.
        """
        menu_bar = tk.Menu(self.root)
        
        # 简化文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="打开PDF", command=self.select_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_file_selection(self):
        """
        Create the file selection elements.
        """
        ttk.Label(self.top_frame, text="PDF文件:").pack(side=tk.LEFT, padx=5)
        
        self.file_var = tk.StringVar()
        ttk.Entry(self.top_frame, textvariable=self.file_var, width=50).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.top_frame, text="浏览", command=self.select_pdf).pack(side=tk.LEFT, padx=5)
        
        # 添加提取方法选择
        ttk.Label(self.top_frame, text="提取方法:").pack(side=tk.LEFT, padx=5)
        self.extract_method_var = tk.StringVar(value=PDFProcessor.EXTRACT_METHOD_PYPDF2)
        extract_methods = ttk.Combobox(self.top_frame, textvariable=self.extract_method_var, width=10)
        extract_methods['values'] = [
            PDFProcessor.EXTRACT_METHOD_PYPDF2,
            PDFProcessor.EXTRACT_METHOD_PDFPLUMBER,
            PDFProcessor.EXTRACT_METHOD_PDFMINER,
            PDFProcessor.EXTRACT_METHOD_IMAGE,
            PDFProcessor.EXTRACT_METHOD_OCR
        ]
        extract_methods.pack(side=tk.LEFT, padx=5)
        
        # 只保留一键整合按钮
        ttk.Button(self.top_frame, text="一键整合", command=self.one_click_process).pack(side=tk.LEFT, padx=5)
    
    def create_image_display(self):
        """
        Create the image display area.
        """
        # Create a frame for the image
        self.image_frame = ttk.LabelFrame(self.main_frame, text="图片预览")
        self.image_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a canvas with scrollbars for the image
        self.canvas_frame = ttk.Frame(self.image_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add horizontal and vertical scrollbars
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create the canvas with scrollbar support
        self.canvas = tk.Canvas(
            self.canvas_frame, 
            bg="white",
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure the scrollbars
        self.h_scrollbar.config(command=self.canvas.xview)
        self.v_scrollbar.config(command=self.canvas.yview)
        
        # Create a placeholder for the image
        self.image_label = ttk.Label(self.canvas, text="选择一个PDF文件进行处理")
        self.canvas.create_window(300, 200, window=self.image_label)
        
        # Bind resize event to update image display
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        
        # Current zoom level and image reference
        self.zoom_level = 1.0
        self.current_image = None  # Store the PIL image
    
    def _on_canvas_resize(self, event):
        """
        Handle canvas resize events to redisplay the image.
        """
        if hasattr(self, 'current_image') and self.current_image:
            self.show_current_image()
    
    def create_control_buttons(self):
        """
        Create the control buttons.
        """
        # Create a frame for the buttons
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)
        
        # Create a frame for page navigation buttons
        nav_frame = ttk.Frame(self.button_frame)
        nav_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 只保留图片导航和缩放按钮
        ttk.Button(nav_frame, text="上一页", command=self.show_previous_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="下一页", command=self.show_next_image).pack(side=tk.LEFT, padx=5)
        
        # Page indicator
        self.page_var = tk.StringVar()
        self.page_var.set("0/0")
        ttk.Label(nav_frame, textvariable=self.page_var).pack(side=tk.LEFT, padx=10)
        
        # Zoom buttons
        ttk.Button(nav_frame, text="放大", command=self.zoom_in).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="缩小", command=self.zoom_out).pack(side=tk.LEFT, padx=5)
        
        # 保留导出PDF按钮，方便用户在需要时手动导出
        ttk.Button(nav_frame, text="导出PDF", command=self.export_to_pdf).pack(side=tk.LEFT, padx=5)
        
        # Create a frame for translation buttons
        translate_frame = ttk.Frame(self.button_frame)
        translate_frame.pack(side=tk.RIGHT, fill=tk.X)
        
        # 添加翻译引擎选择
        ttk.Label(translate_frame, text="翻译引擎:").pack(side=tk.LEFT, padx=5)
        self.translator_var = tk.StringVar(value=TranslatorFactory.MODEL_AUTO)
        translator_combo = ttk.Combobox(translate_frame, textvariable=self.translator_var, width=15)
        translator_combo['values'] = [
            TranslatorFactory.MODEL_AUTO,
            TranslatorFactory.MODEL_DEEPSEEK_REASONER,
            TranslatorFactory.MODEL_DEEPSEEK_CHAT,
            TranslatorFactory.MODEL_OPENROUTER_DEEPSEEK,
        ]
        translator_combo.pack(side=tk.LEFT, padx=5)
    
    def create_text_display(self):
        """
        Create the text display area.
        """
        # Create a notebook for the text displays
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a frame for the translation text
        self.translation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translation_frame, text="翻译")
        
        # Create a text widget for the translation
        self.translation_text = tk.Text(self.translation_frame, wrap=tk.WORD, font=("Helvetica", 12), bg="#f8f8f8")
        self.translation_text.pack(fill=tk.BOTH, expand=True)
        
        # Add a scrollbar to the translation text
        translation_scrollbar = ttk.Scrollbar(self.translation_text, command=self.translation_text.yview)
        translation_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.translation_text.config(yscrollcommand=translation_scrollbar.set)
        
        # Create a frame for the vocabulary text
        self.vocabulary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.vocabulary_frame, text="词汇")
        
        # Create a text widget for the vocabulary
        self.vocabulary_text = tk.Text(self.vocabulary_frame, wrap=tk.WORD, font=("Helvetica", 12), bg="#f8f8f8")
        self.vocabulary_text.pack(fill=tk.BOTH, expand=True)
        
        # Add a scrollbar to the vocabulary text
        vocabulary_scrollbar = ttk.Scrollbar(self.vocabulary_text, command=self.vocabulary_text.yview)
        vocabulary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vocabulary_text.config(yscrollcommand=vocabulary_scrollbar.set)
    
    def select_pdf(self):
        """
        Select a PDF file.
        """
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.pdf_path = file_path
            self.file_var.set(file_path)
            self.status_var.set(f"已选择文件: {os.path.basename(file_path)}")
    
    def process_pdf(self):
        """
        Process the PDF file.
        """
        if not self.pdf_path:
            messagebox.showerror("错误", "请先选择一个PDF文件")
            return
        
        self.status_var.set("正在处理PDF...")
        
        # Start processing in a separate thread
        threading.Thread(target=self._process_pdf_thread, daemon=True).start()
    
    def _process_pdf_thread(self):
        """
        Thread function for processing PDF.
        """
        try:
            # Process the PDF file
            pdf_processor = PDFProcessor(self.pdf_path)
            
            # Convert PDF to images with note space
            self.image_paths = pdf_processor.convert_to_images_with_notes(self.output_dir)
            
            # Update UI in the main thread
            self.root.after(0, self._update_ui_after_processing)
            
        except Exception as e:
            # Update UI in the main thread
            self.root.after(0, lambda: self._show_error(f"处理PDF时出错: {e}"))
    
    def _update_ui_after_processing(self):
        """
        Update UI after processing the PDF.
        """
        if self.image_paths:
            self.current_image_index = 0
            self.show_current_image()
            self.page_var.set(f"1/{len(self.image_paths)}")
            self.status_var.set(f"已生成 {len(self.image_paths)} 页图片")
        else:
            self.status_var.set("处理PDF失败")
    
    def show_current_image(self):
        """
        Show the current image.
        """
        if not self.image_paths or self.current_image_index >= len(self.image_paths):
            return
        
        # Load the image
        image_path = self.image_paths[self.current_image_index]
        try:
            # Open the image and keep a reference
            self.current_image = Image.open(image_path)
            
            # Get the canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Ensure we have valid dimensions
            if canvas_width <= 1:
                canvas_width = 600
            if canvas_height <= 1:
                canvas_height = 400
            
            # Calculate the scaling factor based on zoom level
            img_width = int(self.current_image.width * self.zoom_level)
            img_height = int(self.current_image.height * self.zoom_level)
            
            # Resize the image for display
            display_image = self.current_image.resize((img_width, img_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(display_image)
            
            # Update the canvas
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor="center")
            self.canvas.image = photo  # Keep a reference
            
            # Configure the canvas scrolling region
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
            # Update status bar
            self.status_var.set(f"显示图片 {self.current_image_index + 1}/{len(self.image_paths)}")
            
        except Exception as e:
            self._show_error(f"显示图片时出错: {e}")
    
    def show_previous_image(self):
        """
        Show the previous image.
        """
        if self.image_paths:
            self.current_image_index = max(0, self.current_image_index - 1)
            self.show_current_image()
            self.page_var.set(f"{self.current_image_index + 1}/{len(self.image_paths)}")
    
    def show_next_image(self):
        """
        Show the next image.
        """
        if self.image_paths:
            self.current_image_index = min(len(self.image_paths) - 1, self.current_image_index + 1)
            self.show_current_image()
            self.page_var.set(f"{self.current_image_index + 1}/{len(self.image_paths)}")
    
    def zoom_in(self):
        """
        Zoom in the current image.
        """
        self.zoom_level *= 1.2
        self.show_current_image()
    
    def zoom_out(self):
        """
        Zoom out the current image.
        """
        self.zoom_level /= 1.2
        if self.zoom_level < 0.1:  # Prevent zooming out too far
            self.zoom_level = 0.1
        self.show_current_image()
    
    def extract_text(self):
        """
        Extract text from the PDF.
        """
        if not self.pdf_path:
            messagebox.showerror("错误", "请先选择一个PDF文件")
            return
        
        self.status_var.set("正在提取文本...")
        
        # Start extraction in a separate thread
        threading.Thread(target=self._extract_text_thread, daemon=True).start()
    
    def _extract_text_thread(self):
        """
        Thread function for extracting text.
        """
        try:
            # 更新状态
            self.status_var.set("正在提取文本...")
            
            # 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 创建PDF处理器
            pdf_processor = PDFProcessor(self.pdf_path)
            
            # 获取选择的提取方法
            extract_method = self.extract_method_var.get()
            print(f"使用 {extract_method} 方法提取文本")
            
            # 提取文本
            text = pdf_processor.extract_text(extract_method)
            
            # 保存文本
            text_path = os.path.join(self.output_dir, 'extracted_text.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # 保存文本到实例变量
            self.extracted_text = text
            
            # 更新UI
            self.root.after(0, lambda: self._update_extracted_text(text))
            self.root.after(0, lambda: self._update_status(f"文本提取完成并保存到 {text_path}"))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"提取文本时出错: {e}"))
    
    def _update_extracted_text(self, text):
        """
        更新提取的文本显示
        """
        self.translation_text.delete(1.0, tk.END)
        self.translation_text.insert(tk.END, text)
        self.extracted_text = text  # 更新提取的文本属性
    
    def translate_text(self):
        """
        Translate the extracted text.
        """
        # Check if text has been extracted
        text_path = os.path.join(self.output_dir, 'extracted_text.txt')
        if not os.path.exists(text_path):
            # Try to extract text first
            self.extract_text()
            messagebox.showinfo("提示", "请等待文本提取完成后再进行翻译")
            return
        
        self.status_var.set("正在翻译文本...")
        
        # Start translation in a separate thread
        threading.Thread(target=self._translate_text_thread, daemon=True).start()
    
    def _translate_text_thread(self):
        """
        Thread function for translating text.
        """
        try:
            # Read the extracted text
            text_path = os.path.join(self.output_dir, 'extracted_text.txt')
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 根据用户选择的翻译引擎创建翻译器
            translator_type = self.translator_var.get()
            translator = TranslatorFactory.create_translator(translator_type)
            
            # 翻译文本，如果是auto模式会自动尝试不同的翻译器
            translation = translator.translate(text)
            
            # Save the translation
            translation_path = os.path.join(self.output_dir, 'translation.txt')
            with open(translation_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            
            # Update UI in the main thread
            self.root.after(0, lambda: self._update_translation_text(translation))
            self.root.after(0, lambda: self._update_status(f"翻译完成并保存到 {translation_path}"))
            
        except Exception as e:
            error_msg = str(e)
            
            # 根据错误类型提供友好提示
            message = f"翻译文本时出错: {error_msg}"
            
            if "429" in error_msg or "busy" in error_msg.lower() or "服务器繁忙" in error_msg:
                message = "翻译服务器当前繁忙，这是临时性问题，与您的API密钥无关。\n请稍后再试。"
            elif "Authentication fails" in error_msg or "401" in error_msg:
                message = "API密钥认证失败，请检查您的.env文件中的API密钥是否正确。"
            
            # Update UI in the main thread
            self.root.after(0, lambda: self._show_error_with_retry(message))
    
    def _update_translation_text(self, text):
        """
        Update the translation text widget.
        """
        self.translation_text.delete(1.0, tk.END)
        self.translation_text.insert(tk.END, text)
        self.notebook.select(0)  # Switch to translation tab
    
    def extract_vocabulary(self):
        """
        Extract vocabulary from the extracted text.
        """
        # 检查是否已有提取的文本，没有则尝试从文件读取
        if not hasattr(self, 'extracted_text') or not self.extracted_text:
            # 尝试从文件读取提取的文本
            text_path = os.path.join(self.output_dir, 'extracted_text.txt')
            if os.path.exists(text_path):
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        self.extracted_text = f.read()
                except Exception as e:
                    self._show_error(f"读取文本文件失败: {e}")
                    return
            else:
                self._show_error("请先提取文本")
                return
        
        self.status_var.set("正在提取词汇...")
        
        # Start vocabulary extraction in a separate thread
        threading.Thread(
            target=self._extract_vocabulary_thread, 
            args=(self.extracted_text,), 
            daemon=True
        ).start()
    
    def _extract_vocabulary_thread(self, text, progress_text=None, progress_window=None):
        """
        在单独的线程中提取词汇
        """
        # 尝试的翻译器类型列表（按优先级排序）
        translator_types = [
            self.translator_var.get(),  # 首先使用用户选择的
            TranslatorFactory.MODEL_DEEPSEEK_CHAT,  # 然后使用DeepseekChat
            TranslatorFactory.MODEL_OPENROUTER_DEEPSEEK  # 最后使用OpenRouter
        ]
        
        # 确保不重复尝试相同的翻译器
        translator_types = list(dict.fromkeys(translator_types))
        
        last_error = None
        
        for translator_type in translator_types:
            try:
                print(f"尝试使用翻译器: {translator_type}")
                # 创建翻译器实例
                translator = TranslatorFactory.create_translator(translator_type)
                
                # 使用专门的词汇提取方法
                if hasattr(translator, 'extract_vocabulary'):
                    # 如果翻译器有专门的词汇提取方法，则使用它
                    vocabulary = translator.extract_vocabulary(text)
                else:
                    # 否则，使用通用翻译方法并尝试提取词汇部分
                    full_content = translator.translate(text)
                    # 尝试从翻译结果中提取词汇部分
                    if "重点词汇解析" in full_content:
                        parts = full_content.split("重点词汇解析", 1)
                        vocabulary = "重点词汇解析" + parts[1]
                    else:
                        vocabulary = "未能提取词汇，请检查翻译引擎是否支持词汇提取功能。"
                
                # 检查结果是否有效
                if vocabulary and "重点词汇解析" in vocabulary and len(vocabulary) > 50:
                    # 成功提取词汇，保存结果
                    vocabulary_path = os.path.join(self.output_dir, 'vocabulary.txt')
                    with open(vocabulary_path, 'w', encoding='utf-8') as f:
                        f.write(vocabulary)
                    
                    # 更新UI
                    self.root.after(0, lambda: self._update_vocabulary_text(vocabulary))
                    
                    # 更新进度
                    if progress_text and progress_window:
                        self._update_progress(
                            progress_text, 
                            f"✓ 词汇提取完成，已保存到 {vocabulary_path}", 
                            None, 
                            None
                        )
                    
                    self.status_var.set("词汇提取完成")
                    
                    # 如果不是用户选择的翻译器，显示提示
                    if translator_type != self.translator_var.get():
                        self.root.after(0, lambda: self._show_info(
                            f"已自动切换到 {translator_type} 进行词汇提取，因为首选翻译器遇到了问题: {last_error}"
                        ))
                    
                    # 成功完成，退出循环
                    return
                else:
                    # 结果无效，继续尝试下一个翻译器
                    last_error = "翻译结果不符合预期格式"
                    continue
            
            except Exception as e:
                error_message = str(e)
                last_error = error_message
                print(f"使用翻译器 {translator_type} 提取词汇失败: {error_message}")
                # 继续尝试下一个翻译器
                continue
        
        # 如果所有翻译器都失败
        error_message = f"所有翻译器都失败了，最后一个错误: {last_error}"
        self.status_var.set(f"词汇提取失败: {error_message}")
        
        # 在进度窗口中更新错误
        if progress_text and progress_window:
            self._update_progress(progress_text, f"❌ 词汇提取失败: {error_message}")
        
        # 在主窗口显示错误
        self.root.after(0, lambda: self._show_error(f"词汇提取失败: {error_message}"))
    
    def _update_vocabulary_text(self, text):
        """
        Update the vocabulary text widget.
        """
        self.vocabulary_text.delete(1.0, tk.END)
        self.vocabulary_text.insert(tk.END, text)
        self.notebook.select(1)  # Switch to vocabulary tab
    
    def save_translation(self):
        """
        Save the translation to a file.
        """
        # Check if translation exists
        translation_path = os.path.join(self.output_dir, 'translation.txt')
        if not os.path.exists(translation_path):
            messagebox.showerror("错误", "翻译文件不存在")
            return
        
        # Get the save file path
        save_path = filedialog.asksaveasfilename(
            title="保存翻译",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if save_path:
            # Copy the file
            with open(translation_path, 'r', encoding='utf-8') as src:
                with open(save_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            self.status_var.set(f"翻译已保存到 {save_path}")
    
    def save_vocabulary(self):
        """
        Save the vocabulary to a file.
        """
        # Check if vocabulary exists
        vocabulary_path = os.path.join(self.output_dir, 'vocabulary.txt')
        if not os.path.exists(vocabulary_path):
            messagebox.showerror("错误", "词汇文件不存在")
            return
        
        # Get the save file path
        save_path = filedialog.asksaveasfilename(
            title="保存词汇",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if save_path:
            # Copy the file
            with open(vocabulary_path, 'r', encoding='utf-8') as src:
                with open(save_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            self.status_var.set(f"词汇已保存到 {save_path}")
    
    def show_about(self):
        """
        Show the about dialog.
        """
        messagebox.showinfo(
            "关于",
            "PDF阅读助手\n\n"
            "功能：\n"
            "1. 将PDF转换为带笔记空间的图片\n"
            "2. 使用AI翻译英文文章（支持多个翻译引擎）\n"
            "3. 提取文章中的重要词汇并解释\n"
            "4. 提供一键整合功能，简化操作流程\n\n"
            "使用说明：\n"
            "1. 点击「浏览」选择PDF文件\n"
            "2. 选择翻译引擎\n"
            "3. 点击「一键整合」开始处理\n\n"
            "版本：1.1.0"
        )
    
    def _update_status(self, message):
        """
        Update the status bar.
        """
        self.status_var.set(message)
    
    def _show_error(self, message):
        """
        Show an error message.
        """
        messagebox.showerror("错误", message)
        self.status_var.set("出错")
    
    def _show_info(self, message):
        """
        Show an information message.
        """
        messagebox.showinfo("信息", message)
    
    def _show_error_with_retry(self, message):
        """
        显示带有重试选项的错误消息
        """
        # 创建自定义对话框
        error_window = tk.Toplevel(self.root)
        error_window.title("错误")
        error_window.geometry("400x200")
        error_window.grab_set()  # 模态对话框
        
        # 添加错误图标
        try:
            error_icon = tk.Label(error_window, text="❌", font=("Helvetica", 48), fg="red")
            error_icon.pack(pady=(10, 5))
        except:
            pass  # 如果无法显示图标，则忽略
        
        # 错误消息
        message_label = ttk.Label(error_window, text=message, wraplength=350, justify="center")
        message_label.pack(pady=10, padx=20)
        
        # 按钮框架
        button_frame = ttk.Frame(error_window)
        button_frame.pack(pady=10)
        
        # 添加重试按钮
        ttk.Button(
            button_frame,
            text="重试",
            command=lambda: [error_window.destroy(), self.translate_text()]
        ).pack(side=tk.LEFT, padx=5)
        
        # 添加检查API按钮
        ttk.Button(
            button_frame,
            text="检查API密钥",
            command=lambda: [error_window.destroy(), self._check_api_key(self.root)]
        ).pack(side=tk.LEFT, padx=5)
        
        # 添加关闭按钮
        ttk.Button(
            button_frame,
            text="关闭",
            command=error_window.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        self.status_var.set("翻译出错")
    
    def compare_extraction_methods(self):
        """
        Compare all text extraction methods.
        """
        if not self.pdf_path:
            messagebox.showerror("错误", "请先选择一个PDF文件")
            return
        
        self.status_var.set("正在比较所有文本提取方法...")
        
        # Start comparison in a separate thread
        threading.Thread(target=self._compare_methods_thread, daemon=True).start()
    
    def _compare_methods_thread(self):
        """
        Thread function for comparing extraction methods.
        """
        try:
            # Process the PDF file
            pdf_processor = PDFProcessor(self.pdf_path)
            
            # Compare all methods
            results = pdf_processor.extract_text_all_methods()
            
            # Save all extraction results
            method_texts = {}
            for method, text in results.items():
                method_text_path = os.path.join(self.output_dir, f'extracted_text_{method}.txt')
                with open(method_text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                method_texts[method] = text
            
            # Update UI in the main thread
            self.root.after(0, lambda: self._show_comparison_results(method_texts))
            self.root.after(0, lambda: self._update_status("所有文本提取方法比较完成"))
            
        except Exception as e:
            # Update UI in the main thread
            self.root.after(0, lambda: self._show_error(f"比较文本提取方法时出错: {e}"))
    
    def _show_comparison_results(self, method_texts):
        """
        Show the comparison results.
        """
        # Create a new window to show the comparison results
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title("文本提取方法比较")
        comparison_window.geometry("800x600")
        
        # Create a notebook for the method tabs
        notebook = ttk.Notebook(comparison_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a tab for each method
        for method, text in method_texts.items():
            # Create a frame for the method
            method_frame = ttk.Frame(notebook)
            notebook.add(method_frame, text=method)
            
            # Create a text widget for the method text
            method_text = tk.Text(method_frame, wrap=tk.WORD, font=("Helvetica", 12), bg="#f8f8f8")
            method_text.pack(fill=tk.BOTH, expand=True)
            
            # Add a scrollbar to the method text
            method_scrollbar = ttk.Scrollbar(method_text, command=method_text.yview)
            method_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            method_text.config(yscrollcommand=method_scrollbar.set)
            
            # Insert the method text
            method_text.delete(1.0, tk.END)
            method_text.insert(tk.END, text)
            
            # Add a button to use this method
            ttk.Button(
                method_frame, 
                text=f"使用{method}方法", 
                command=lambda m=method: self._select_extraction_method(m)
            ).pack(side=tk.BOTTOM, pady=5)
        
        # Add a close button
        ttk.Button(comparison_window, text="关闭", command=comparison_window.destroy).pack(side=tk.BOTTOM, pady=10)
    
    def _select_extraction_method(self, method):
        """
        Select the extraction method.
        """
        self.extract_method_var.set(method)
        messagebox.showinfo("提示", f"已选择 {method} 作为文本提取方法")
        # Optionally extract text immediately
        self.extract_text()

    def export_to_pdf(self):
        """
        导出选定的页面到PDF
        """
        if not self.image_paths:
            messagebox.showerror("错误", "未找到图片文件")
            return
        
        # 创建页面选择对话框
        self._create_page_selection_dialog()
    
    def _create_page_selection_dialog(self):
        """
        创建页面选择对话框，让用户选择要保存的页面
        """
        if not self.image_paths:
            return
        
        # 创建对话框
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("选择要保存的页面")
        select_dialog.geometry("500x400")
        select_dialog.grab_set()  # 模态对话框
        
        # 页面选择说明
        ttk.Label(
            select_dialog, 
            text="请选择需要导出到PDF的页面：",
            font=("Helvetica", 12)
        ).pack(pady=(10, 5))
        
        # 创建框架包含滚动视图
        main_frame = ttk.Frame(select_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(main_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Canvas用于滚动
        canvas = tk.Canvas(main_frame, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 设置滚动条命令
        scrollbar.config(command=canvas.yview)
        
        # 创建内部框架放置复选框
        checkbox_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=checkbox_frame, anchor=tk.NW)
        
        # 用于存储页面选择状态
        page_vars = []
        
        # 全选/全不选变量及复选框
        all_var = tk.BooleanVar(value=True)
        all_check = ttk.Checkbutton(
            checkbox_frame, 
            text="全选/取消全选", 
            variable=all_var,
            command=lambda: self._toggle_all_pages(all_var, page_vars)
        )
        all_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 在滚动框架内添加每个页面的复选框
        for i, image_path in enumerate(self.image_paths):
            var = tk.BooleanVar(value=True)
            page_vars.append(var)
            
            # 创建预览图片的小缩略图
            try:
                img = Image.open(image_path)
                img = img.resize((60, 80), Image.LANCZOS)  # 缩小图片
                photo = ImageTk.PhotoImage(img)
                
                # 创建包含复选框和预览图的框架
                page_frame = ttk.Frame(checkbox_frame)
                page_frame.grid(row=i+1, column=0, sticky=tk.W, padx=5, pady=5)
                
                # 添加复选框
                ttk.Checkbutton(
                    page_frame, 
                    text=f"第 {i+1} 页", 
                    variable=var,
                    command=lambda all_var=all_var, page_vars=page_vars: self._update_all_checkbox(all_var, page_vars)
                ).pack(side=tk.LEFT, padx=5)
                
                # 添加预览图
                preview = ttk.Label(page_frame, image=photo)
                preview.image = photo  # 保持引用
                preview.pack(side=tk.LEFT, padx=5)
            except Exception as e:
                # 如果无法加载图片，则只显示复选框
                ttk.Checkbutton(
                    checkbox_frame, 
                    text=f"第 {i+1} 页", 
                    variable=var,
                    command=lambda all_var=all_var, page_vars=page_vars: self._update_all_checkbox(all_var, page_vars)
                ).grid(row=i+1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 更新Canvas的滚动区域
        checkbox_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        
        # 按钮框架
        button_frame = ttk.Frame(select_dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 取消按钮
        ttk.Button(
            button_frame, 
            text="取消", 
            command=select_dialog.destroy
        ).pack(side=tk.RIGHT, padx=10)
        
        # 确定按钮
        ttk.Button(
            button_frame, 
            text="导出PDF", 
            command=lambda: self._export_selected_pages(page_vars, select_dialog)
        ).pack(side=tk.RIGHT, padx=10)
    
    def _toggle_all_pages(self, all_var, page_vars):
        """
        全选或取消全选所有页面
        """
        is_selected = all_var.get()
        for var in page_vars:
            var.set(is_selected)
    
    def _update_all_checkbox(self, all_var, page_vars):
        """
        更新全选复选框状态
        """
        all_selected = all(var.get() for var in page_vars)
        all_var.set(all_selected)
    
    def _export_selected_pages(self, page_vars, dialog):
        """
        导出选中的页面到PDF
        """
        # 获取选中的页面索引
        selected_indices = [i for i, var in enumerate(page_vars) if var.get()]
        
        if not selected_indices:
            messagebox.showwarning("警告", "未选择任何页面")
            return
        
        # 获取选中的图片路径
        selected_images = [self.image_paths[i] for i in selected_indices]
        
        # 设置默认文件名为输入PDF的文件名
        default_filename = "output.pdf"
        if self.pdf_path:
            default_filename = os.path.splitext(os.path.basename(self.pdf_path))[0] + ".pdf"
        
        # 获取保存路径
        save_path = filedialog.asksaveasfilename(
            title="保存PDF",
            defaultextension=".pdf",
            initialfile=default_filename,
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if not save_path:
            return  # 用户取消
        
        # 检查文件是否已存在
        if os.path.exists(save_path):
            try:
                # 尝试删除现有文件
                os.remove(save_path)
                print(f"已删除现有文件: {save_path}")
            except Exception as e:
                print(f"无法删除现有文件: {e}")
                # 如果无法删除，询问用户是否继续
                response = messagebox.askyesno(
                    "文件已存在", 
                    f"文件 {save_path} 已存在但无法覆盖：{e}\n是否尝试使用不同的文件名？"
                )
                if response:
                    # 再次打开文件对话框，让用户选择新的文件名
                    save_path = filedialog.asksaveasfilename(
                        title="选择不同的文件名",
                        defaultextension=".pdf",
                        initialfile=f"{os.path.splitext(default_filename)[0]}_new.pdf",
                        filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
                    )
                    if not save_path:
                        return  # 用户取消
                else:
                    return  # 用户选择不继续
        
        # 确保目标目录存在
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
                print(f"创建目录: {save_dir}")
            except Exception as e:
                print(f"无法创建目录: {e}")
                messagebox.showerror("错误", f"无法创建目标目录: {e}")
                return
        
        # 关闭选择对话框
        dialog.destroy()
        
        self.status_var.set("正在创建PDF...")
        
        # 启动导出线程
        threading.Thread(
            target=self._export_to_pdf_thread, 
            args=(save_path, selected_images),
            daemon=True
        ).start()

    def _export_to_pdf_thread(self, save_path, selected_images=None):
        """
        将选定的图片导出为PDF的线程函数
        
        Args:
            save_path: PDF保存路径
            selected_images: 可选，要保存的图片列表。如果为None，则保存所有图片
        """
        try:
            # 检查图像列表是否有效
            if not selected_images or len(selected_images) == 0:
                raise ValueError("没有可用的图像文件")
            
            # 确保所有图像路径存在
            missing_files = [img for img in selected_images if not os.path.exists(img)]
            if missing_files:
                raise ValueError(f"找不到以下图像文件:\n{', '.join(missing_files)}")
            
            # 创建PDF处理器
            if self.pdf_path:
                pdf_processor = PDFProcessor(self.pdf_path)
            else:
                # 使用第一个图片路径初始化
                pdf_processor = PDFProcessor(selected_images[0])
            
            # 转换图片为PDF
            result_path = pdf_processor.images_to_pdf(selected_images, save_path)
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self._update_status(f"PDF已成功保存到: {result_path}"))
            
        except Exception as e:
            # 记录错误
            print(f"创建PDF时出错: {e}")
            # 在主线程中更新UI
            self.root.after(0, lambda: self._show_error(f"创建PDF时出错: {e}"))

    def one_click_process(self):
        """
        One-click process to execute all operations in sequence using the image method.
        """
        if not self.pdf_path:
            messagebox.showerror("错误", "请先选择一个PDF文件")
            return
        
        # 设置使用image方法
        self.extract_method_var.set(PDFProcessor.EXTRACT_METHOD_IMAGE)
        
        # 创建处理进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("处理进度")
        progress_window.geometry("400x300")
        
        # 添加进度文本框
        progress_text = tk.Text(progress_window, wrap=tk.WORD, font=("Helvetica", 12), bg="#f8f8f8")
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加滚动条
        progress_scrollbar = ttk.Scrollbar(progress_text, command=progress_text.yview)
        progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        progress_text.config(yscrollcommand=progress_scrollbar.set)
        
        # 添加进度条
        progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=380, mode="determinate")
        progress_bar.pack(pady=10, padx=10)
        
        # 启动处理线程
        threading.Thread(
            target=self._one_click_process_thread, 
            args=(progress_text, progress_bar, progress_window),
            daemon=True
        ).start()
    
    def _update_progress(self, progress_text, message, progress_bar=None, value=None):
        """
        Update the progress text and progress bar.
        """
        self.root.after(0, lambda: self._do_update_progress(progress_text, message, progress_bar, value))
    
    def _do_update_progress(self, progress_text, message, progress_bar=None, value=None):
        """
        Actual update of progress UI elements in the main thread.
        """
        # 更新进度文本
        progress_text.insert(tk.END, f"{message}\n")
        progress_text.see(tk.END)  # 滚动到底部
        
        # 更新进度条
        if progress_bar is not None and value is not None:
            progress_bar["value"] = value
        
        # 更新状态栏
        self.status_var.set(message)
    
    def _one_click_process_thread(self, progress_text, progress_bar, progress_window):
        """
        Thread function for one-click processing.
        """
        try:
            # 设置总步骤数（移除导出PDF步骤）
            total_steps = 4  # 处理PDF、提取文本、翻译文本、提取词汇
            current_step = 0
            
            # 在函数开始时初始化这些路径变量，避免引用错误
            text_path = os.path.join(self.output_dir, 'extracted_text.txt')
            translation_path = os.path.join(self.output_dir, 'translation.txt')
            vocabulary_path = os.path.join(self.output_dir, 'vocabulary.txt')
            
            # 步骤1: 处理PDF
            self._update_progress(progress_text, "第1步/4: 正在处理PDF并转换为图片...", progress_bar, (current_step / total_steps) * 100)
            
            # 处理PDF文件
            pdf_processor = PDFProcessor(self.pdf_path)
            
            # 转换PDF为带笔记空间的图片
            self.image_paths = pdf_processor.convert_to_images_with_notes(self.output_dir)
            
            current_step += 1
            self._update_progress(
                progress_text, 
                f"✓ PDF处理完成，已生成 {len(self.image_paths)} 页图片", 
                progress_bar, 
                (current_step / total_steps) * 100
            )
            
            # 更新UI显示第一页图片
            self.root.after(0, self._update_ui_after_processing)
            
            # 步骤2: 提取文本
            self._update_progress(progress_text, f"第2步/4: 正在使用 {PDFProcessor.EXTRACT_METHOD_IMAGE} 方法提取文本...", progress_bar, (current_step / total_steps) * 100)
            
            # 提取文本
            text = pdf_processor.extract_text(PDFProcessor.EXTRACT_METHOD_IMAGE)
            
            # 保存文本
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # 保存文本到实例变量
            self.extracted_text = text
            
            # 更新UI显示
            self.root.after(0, lambda: self._update_extracted_text(text))
            
            current_step += 1
            self._update_progress(
                progress_text, 
                f"✓ 文本提取完成，已保存到 {text_path}", 
                progress_bar, 
                (current_step / total_steps) * 100
            )
            
            # 步骤3: 翻译文本
            self._update_progress(progress_text, "第3步/4: 正在翻译文本...", progress_bar, (current_step / total_steps) * 100)
            
            # 翻译文本
            try:
                # 根据用户选择的翻译引擎创建翻译器
                translator_type = self.translator_var.get()
                translator = TranslatorFactory.create_translator(translator_type)
                
                # 翻译文本，如果是auto模式会自动尝试不同的翻译器
                translation = translator.translate(text)
                
                # Save the translation
                translation_path = os.path.join(self.output_dir, 'translation.txt')
                with open(translation_path, 'w', encoding='utf-8') as f:
                    f.write(translation)
                
                # Update UI in the main thread
                self.root.after(0, lambda: self._update_translation_text(translation))
                
                current_step += 1
                self._update_progress(
                    progress_text, 
                    f"✓ 翻译完成，已保存到 {translation_path}", 
                    progress_bar, 
                    (current_step / total_steps) * 100
                )
            except Exception as e:
                error_msg = str(e)
                self._update_progress(progress_text, f"❌ 翻译失败: {error_msg}")
                
                # 根据错误类型提供友好提示
                if "429" in error_msg or "busy" in error_msg.lower() or "服务器繁忙" in error_msg:
                    self._update_progress(
                        progress_text, 
                        "翻译服务器当前繁忙，这是临时性问题，与您的API密钥无关。\n"
                        "请稍后再试，或继续执行后续步骤。"
                    )
                    
                    # 添加重试按钮
                    self.root.after(0, lambda: self._add_retry_button_to_progress(
                        progress_window, 
                        "重试翻译", 
                        lambda: self._retry_translation_in_progress(progress_text, text, progress_window)
                    ))
                elif "Authentication fails" in error_msg or "401" in error_msg or "invalid_request_error" in error_msg:
                    self._update_progress(
                        progress_text, 
                        "API密钥认证失败，请检查您的.env文件中的API密钥是否正确。\n"
                        "1. 确保.env文件位于项目根目录\n"
                        "2. 确保API密钥格式正确，没有多余的空格\n"
                        "3. 确保API密钥仍然有效且有足够的余额"
                    )
                    
                    # 添加检查API密钥按钮
                    self.root.after(0, lambda: self._add_retry_button_to_progress(
                        progress_window, 
                        "检查API密钥", 
                        lambda: self._check_api_key(progress_window)
                    ))
                
                # 继续执行其他步骤
                current_step += 1
                self._update_progress(
                    progress_text, 
                    "继续执行下一步...", 
                    progress_bar, 
                    (current_step / total_steps) * 100
                )
            
            # 步骤4: 提取词汇
            self._update_progress(progress_text, "第4步/4: 正在提取词汇...", progress_bar, (current_step / total_steps) * 100)
            
            # 提取词汇
            try:
                # 直接传递文本内容和进度窗口信息
                self._extract_vocabulary_thread(text, progress_text, progress_window)
                # 由于_extract_vocabulary_thread会自行更新进度，这里无需额外更新
                current_step += 1
            except Exception as e:
                self._update_progress(progress_text, f"❌ 词汇提取失败: {e}")
                current_step += 1
            
            # 全部完成
            self._update_progress(
                progress_text, 
                "✓✓✓ 所有处理步骤已完成！✓✓✓\n\n"
                f"图片保存在: {self.output_dir}\n"
                f"提取的文本: {os.path.exists(text_path) and text_path or '未生成'}\n"
                f"翻译: {os.path.exists(translation_path) and translation_path or '未生成'}\n"
                f"词汇表: {os.path.exists(vocabulary_path) and vocabulary_path or '未生成'}",
                progress_bar,
                100
            )
            
            # 添加关闭按钮和导出PDF按钮
            button_frame = ttk.Frame(progress_window)
            button_frame.pack(pady=10)
            
            # 添加导出PDF按钮选项
            ttk.Button(
                button_frame,
                text="导出为PDF",
                command=lambda: [progress_window.destroy(), self.export_to_pdf()]
            ).pack(side=tk.LEFT, padx=5)
            
            # 添加关闭按钮
            ttk.Button(
                button_frame,
                text="关闭",
                command=progress_window.destroy
            ).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            # 异常处理
            error_message = f"处理过程中出错: {e}"
            self._update_progress(progress_text, f"❌ {error_message}")
            self.root.after(0, lambda: self._show_error(error_message))

    def _add_retry_button_to_progress(self, progress_window, button_text, command):
        """
        Add a retry button to the progress window.
        """
        button_frame = ttk.Frame(progress_window)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text=button_text,
            command=command
        ).pack(side=tk.LEFT, padx=5)

    def _retry_translation_in_progress(self, progress_text, text, progress_window):
        """
        在一键处理流程中重试翻译
        """
        self._update_progress(progress_text, "正在重新尝试翻译...", None, None)
        
        try:
            # 创建翻译器
            translator_type = self.translator_var.get()
            translator = TranslatorFactory.create_translator(translator_type)
            
            # 翻译文本
            translation = translator.translate(text)
            
            # 保存翻译
            translation_path = os.path.join(self.output_dir, 'translation.txt')
            with open(translation_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            
            # 更新UI
            self.root.after(0, lambda: self._update_translation_text(translation))
            
            # 更新进度
            self._update_progress(
                progress_text, 
                f"✓ 翻译重试成功，已保存到 {translation_path}", 
                None, 
                None
            )
        except Exception as e:
            error_msg = str(e)
            self._update_progress(progress_text, f"❌ 翻译重试失败: {error_msg}")
            # 不再添加重试按钮，避免无限循环

    def _check_api_key(self, parent_window=None):
        """
        检查并重新加载API密钥
        """
        try:
            # 重新加载.env文件
            load_dotenv(override=True)
            
            # 检查API密钥
            deepseek_key = os.getenv('DEEPSEEK_API_KEY', '')
            openrouter_key = os.getenv('OPENROUTER_API_KEY', '')
            
            # 创建消息
            message = "API密钥检查结果：\n"
            
            if deepseek_key:
                masked_key = f"{deepseek_key[:4]}...{deepseek_key[-4:]}" if len(deepseek_key) > 8 else "***"
                message += f"\nDeepSeek API密钥: {masked_key} (已加载)"
            else:
                message += "\nDeepSeek API密钥: 未设置或为空"
            
            if openrouter_key:
                masked_key = f"{openrouter_key[:4]}...{openrouter_key[-4:]}" if len(openrouter_key) > 8 else "***"
                message += f"\nOpenRouter API密钥: {masked_key} (已加载)"
            else:
                message += "\nOpenRouter API密钥: 未设置或为空"
            
            # 显示结果
            if parent_window:
                # 在进度窗口中显示
                result_window = tk.Toplevel(parent_window)
                result_window.title("API密钥检查结果")
                result_window.geometry("400x200")
                
                # 消息标签
                ttk.Label(result_window, text=message, wraplength=350, justify="left").pack(pady=20, padx=20)
                
                # 关闭按钮
                ttk.Button(result_window, text="关闭", command=result_window.destroy).pack(pady=10)
            else:
                # 直接显示消息框
                messagebox.showinfo("API密钥检查结果", message)
            
            return bool(deepseek_key or openrouter_key)
            
        except Exception as e:
            error_msg = str(e)
            if parent_window:
                # 在子窗口中显示错误
                error_window = tk.Toplevel(parent_window)
                error_window.title("错误")
                error_window.geometry("400x200")
                ttk.Label(error_window, text=f"检查API密钥时出错: {error_msg}", wraplength=350).pack(pady=20)
                ttk.Button(error_window, text="关闭", command=error_window.destroy).pack()
            else:
                # 直接显示错误消息框
                self._show_error(f"检查API密钥时出错: {error_msg}")
            return False

def start_gui():
    """
    Start the GUI application.
    """
    root = tk.Tk()
    app = PDFGUI(root)
    root.mainloop()

if __name__ == "__main__":
    start_gui() 