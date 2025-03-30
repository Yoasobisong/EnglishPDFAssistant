#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import tempfile
import cv2
import numpy as np
import re
from PIL import Image
from PyPDF2 import PdfReader
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pytesseract

class PDFProcessor:
    """
    Class for processing PDF files - converting to images with note space,
    detecting QR codes, and extracting text.
    """
    
    # 提取方法枚举
    EXTRACT_METHOD_PYPDF2 = 'pypdf2'
    EXTRACT_METHOD_PDFPLUMBER = 'pdfplumber'
    EXTRACT_METHOD_PDFMINER = 'pdfminer'
    EXTRACT_METHOD_OCR = 'ocr'
    EXTRACT_METHOD_IMAGE = 'image'  # 新增：使用图片提取文本
    
    def __init__(self, pdf_path, note_margin_width_percentage=30):
        """
        Initialize PDFProcessor.
        
        Args:
            pdf_path (str): Path to the PDF file
            note_margin_width_percentage (int): Percentage of the image width to be used for notes
        """
        self.pdf_path = pdf_path
        self.note_margin_width_percentage = note_margin_width_percentage
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def extract_text(self, method=EXTRACT_METHOD_PYPDF2):
        """
        Extract text content from the PDF using the specified method.
        
        Args:
            method (str): Method to use for text extraction. 
                          Options: 'pypdf2', 'pdfplumber', 'pdfminer', 'ocr', 'image'
            
        Returns:
            str: Extracted and normalized text from the PDF
        """
        try:
            if method == self.EXTRACT_METHOD_OCR:
                # Use OCR to extract text
                return self._extract_text_with_ocr()
            elif method == self.EXTRACT_METHOD_PDFPLUMBER:
                # Use pdfplumber to extract text
                return self._extract_text_with_pdfplumber()
            elif method == self.EXTRACT_METHOD_PDFMINER:
                # Use pdfminer.six to extract text
                return self._extract_text_with_pdfminer()
            elif method == self.EXTRACT_METHOD_IMAGE:
                # Use images to extract text
                return self._extract_text_from_images()
            else:
                # Default to PyPDF2
                return self._extract_text_with_pypdf2()
                
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {e}")
    
    def _extract_text_with_pypdf2(self):
        """
        Extract text from PDF using PyPDF2.
        
        Returns:
            str: Extracted text using PyPDF2
        """
        reader = PdfReader(self.pdf_path)
        text = ""
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                # Post-process the text to fix spacing issues
                page_text = self._normalize_text(page_text)
                text += page_text + "\n\n"
        
        return text
    
    def _extract_text_with_pdfplumber(self):
        """
        Extract text from PDF using pdfplumber.
        
        Returns:
            str: Extracted text using pdfplumber
        """
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Post-process the text to fix spacing issues
                        page_text = self._normalize_text(page_text)
                        text += page_text + "\n\n"
                        
            return text
        except Exception as e:
            print(f"Error with pdfplumber extraction: {e}")
            # Fallback to PyPDF2 if pdfplumber fails
            return self._extract_text_with_pypdf2()
    
    def _extract_text_with_pdfminer(self):
        """
        Extract text from PDF using pdfminer.six.
        
        Returns:
            str: Extracted text using pdfminer.six
        """
        try:
            # Extract text with pdfminer
            text = pdfminer_extract_text(self.pdf_path)
            
            # Post-process the text to fix spacing issues
            text = self._normalize_text(text)
            
            return text
        except Exception as e:
            print(f"Error with pdfminer extraction: {e}")
            # Fallback to pdfplumber if pdfminer fails
            return self._extract_text_with_pdfplumber()
    
    def _extract_text_from_images(self):
        """
        Extract text from PDF by first converting to images.
        This method does not use OCR directly but uses the built-in image conversion.
        
        Returns:
            str: Extracted text from PDF images
        """
        try:
            # Convert PDF to images
            images = convert_from_path(self.pdf_path, dpi=300)
            
            # Extract text from each image
            full_text = ""
            for i, img in enumerate(images):
                # Convert to OpenCV format for QR detection
                cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                # Check if the image has a QR code and crop if needed
                if self.has_qr_code(cv_image):
                    print(f"QR code detected in page {i+1}, cropping for text extraction")
                    cv_image = self.crop_image_at_qr_code(cv_image)
                
                # Convert back to PIL Image
                pil_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
                
                # Create a temporary file for the image
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_path = temp_file.name
                    pil_image.save(temp_path)
                
                # Extract text from the image
                # Use basic pytesseract without full OCR processing
                try:
                    img_text = pytesseract.image_to_string(
                        pil_image, 
                        lang='eng',
                        config='--psm 1'  # Automatic page segmentation with OSD
                    )
                    
                    # Clean up the temporary file
                    os.unlink(temp_path)
                    
                    # Post-process the text
                    img_text = self._normalize_text(img_text)
                    full_text += img_text + "\n\n"
                except Exception as e:
                    print(f"Error extracting text from image {i+1}: {e}")
                    # Skip this image and continue with the next one
                    continue
            
            return full_text.strip()
            
        except Exception as e:
            print(f"Error extracting text from PDF images: {e}")
            # Fallback to PyPDF2 if image extraction fails
            return self._extract_text_with_pypdf2()
    
    def _extract_text_with_ocr(self):
        """
        Extract text from PDF using OCR.
        
        Returns:
            str: Extracted text using OCR
        """
        try:
            # Convert PDF to images
            images = convert_from_path(self.pdf_path, dpi=300)
            
            # Extract text from each image
            full_text = ""
            for i, img in enumerate(images):
                # Convert to OpenCV format
                cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                # Check if the image has a QR code and crop if needed
                if self.has_qr_code(cv_image):
                    print(f"QR code detected in page {i+1}, cropping for OCR")
                    cv_image = self.crop_image_at_qr_code(cv_image)
                
                # Convert back to PIL Image
                pil_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
                
                # Perform OCR
                text = pytesseract.image_to_string(pil_image, lang='eng')
                
                # Post-process the text
                text = self._normalize_text(text)
                
                full_text += text + "\n\n"
            
            return full_text.strip()
            
        except Exception as e:
            print(f"Error performing OCR on PDF: {e}")
            # Fallback to PyPDF2 if OCR fails
            return self._extract_text_with_pypdf2()
    
    def extract_text_all_methods(self):
        """
        Extract text using all available methods and return results.
        
        Returns:
            dict: Dictionary containing extracted text for each method
        """
        results = {}
        
        try:
            results[self.EXTRACT_METHOD_PYPDF2] = self._extract_text_with_pypdf2()
        except Exception as e:
            results[self.EXTRACT_METHOD_PYPDF2] = f"提取失败: {str(e)}"
            
        try:
            results[self.EXTRACT_METHOD_PDFPLUMBER] = self._extract_text_with_pdfplumber()
        except Exception as e:
            results[self.EXTRACT_METHOD_PDFPLUMBER] = f"提取失败: {str(e)}"
            
        try:
            results[self.EXTRACT_METHOD_PDFMINER] = self._extract_text_with_pdfminer()
        except Exception as e:
            results[self.EXTRACT_METHOD_PDFMINER] = f"提取失败: {str(e)}"
            
        try:
            results[self.EXTRACT_METHOD_IMAGE] = self._extract_text_from_images()
        except Exception as e:
            results[self.EXTRACT_METHOD_IMAGE] = f"提取失败: {str(e)}"
            
        try:
            results[self.EXTRACT_METHOD_OCR] = self._extract_text_with_ocr()
        except Exception as e:
            results[self.EXTRACT_METHOD_OCR] = f"提取失败: {str(e)}"
            
        return results
    
    def _normalize_text(self, text):
        """
        Normalize text extracted from PDF by fixing common spacing issues.
        
        Args:
            text (str): The raw text extracted from PDF
            
        Returns:
            str: Normalized text with proper spacing
        """
        # 如果文本为空则直接返回
        if not text or len(text.strip()) == 0:
            return ""
            
        # First handle the special case of missing spaces between words
        # This is a common issue with PDFs where words are run together
        
        # Step 1: Insert space between lowercase and uppercase letters (camelCase)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Step 2: Insert space after punctuation if followed by a letter
        text = re.sub(r'([.,!?;:])([a-zA-Z])', r'\1 \2', text)
        
        # Step 3: Fix spacing around quotes
        text = re.sub(r'(["])(\w)', r'\1 \2', text)
        text = re.sub(r'(\w)(["])', r'\1 \2', text)
        
        # Step 4: Fix spacing around parentheses
        text = re.sub(r'(\))(\w)', r'\1 \2', text)
        text = re.sub(r'(\w)(\()', r'\1 \2', text)
        
        # Step 5: Special case for numbers followed by words or words followed by numbers
        text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
        
        # Step 6: Fix multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Step 7: Fix paragraph spacing
        text = re.sub(r'\n+', '\n\n', text)
        
        # Step 8: Remove spaces at beginning of lines
        text = re.sub(r'\n ', '\n', text)
        
        return text.strip()
    
    def has_qr_code(self, image):
        """
        Detect if an image contains a QR code.
        
        Args:
            image (numpy.ndarray): The image to check for QR codes
            
        Returns:
            bool: True if a QR code is detected, False otherwise
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use QR code detector
        qr_detector = cv2.QRCodeDetector()
        retval, points, _ = qr_detector.detectAndDecode(gray)
        
        return points is not None and len(points) > 0
    
    def crop_image_at_qr_code(self, image):
        """
        Crop the image at the QR code position.
        
        Args:
            image (numpy.ndarray): Image to crop
            
        Returns:
            numpy.ndarray: Cropped image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use QR code detector
        qr_detector = cv2.QRCodeDetector()
        retval, points, _ = qr_detector.detectAndDecode(gray)
        
        if points is not None and len(points) > 0:
            # Get the QR code's y-coordinate
            qr_y = int(points[0][0][1])  # Top-left corner Y of the QR code
            
            # Crop the image
            return image[:qr_y, :]
        
        return image
    
    def add_note_space(self, image):
        """
        Add note space to the right side of the image.
        
        Args:
            image (PIL.Image): Image to add note space to
            
        Returns:
            PIL.Image: Image with note space added
        """
        # Get original dimensions
        width, height = image.size
        
        # Calculate the width for the note margin
        note_width = int(width * (self.note_margin_width_percentage / 100))
        
        # Create a new image with additional width for notes
        new_width = width + note_width
        new_image = Image.new('RGB', (new_width, height), (255, 255, 255))
        
        # Paste the original image
        new_image.paste(image, (0, 0))
        
        return new_image
    
    def convert_to_images_with_notes(self, output_dir="output"):
        """
        Convert PDF to images with note space added.
        
        Args:
            output_dir (str): Directory to save output images
            
        Returns:
            list: Paths to the output images
        """
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Convert PDF to images
        print(f"Converting PDF to images: {self.pdf_path}")
        images = convert_from_path(self.pdf_path, dpi=200)
        
        output_paths = []
        for i, image in enumerate(images):
            # Convert PIL image to OpenCV format for QR detection
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Check if the image has a QR code and crop if needed
            if self.has_qr_code(cv_image):
                print(f"QR code detected in page {i+1}")
                cv_image = self.crop_image_at_qr_code(cv_image)
                image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Add note space
            image_with_notes = self.add_note_space(image)
            
            # Save the image
            output_path = os.path.join(output_dir, f"page_{i+1}.png")
            image_with_notes.save(output_path)
            output_paths.append(output_path)
            
        return output_paths
    
    def create_pdf_with_notes(self, output_path):
        """
        Create a new PDF with note space added.
        
        Args:
            output_path (str): Path to save the output PDF
            
        Returns:
            str: Path to the output PDF
        """
        # First convert to images with note space
        image_paths = self.convert_to_images_with_notes(tempfile.mkdtemp())
        
        # Create a new PDF with the images
        c = canvas.Canvas(output_path, pagesize=letter)
        
        for img_path in image_paths:
            img = Image.open(img_path)
            width, height = img.size
            
            # Calculate scaling factors
            page_width, page_height = letter
            scale = min(page_width / width, page_height / height)
            
            # Create PDF page
            c.setPageSize((width * scale, height * scale))
            c.drawImage(img_path, 0, 0, width=width * scale, height=height * scale)
            c.showPage()
        
        c.save()
        
        # Clean up temporary images
        for img_path in image_paths:
            os.remove(img_path)
        
        return output_path

    def images_to_pdf(self, image_paths, output_path, page_size=None):
        """
        Convert a list of images to a PDF file.
        
        Args:
            image_paths (list): List of paths to the images
            output_path (str): Path to save the output PDF
            page_size (tuple): Optional custom page size (width, height) in points
            
        Returns:
            str: Path to the output PDF
        """
        try:
            # Check if we have images
            if not image_paths or len(image_paths) == 0:
                raise ValueError("没有提供图像文件")
            
            # 确保所有图像路径存在
            for img_path in image_paths:
                if not os.path.exists(img_path):
                    raise ValueError(f"图像文件不存在: {img_path}")
            
            # 创建输出目录（如果不存在）
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 打开第一个图像来确定PDF页面大小
            try:
                first_img = Image.open(image_paths[0])
                width, height = first_img.size
                first_img.close()  # 及时关闭以释放资源
            except Exception as e:
                print(f"打开首个图像失败: {e}")
                # 如果无法获取第一张图片尺寸，使用默认A4尺寸
                width, height = letter
            
            # 创建一个新的PDF
            if page_size:
                c = canvas.Canvas(output_path, pagesize=page_size)
            else:
                c = canvas.Canvas(output_path, pagesize=(width, height))
            
            # 逐个处理图像
            for img_path in image_paths:
                try:
                    # 打开并处理图像
                    img = Image.open(img_path)
                    
                    # 如果是RGBA模式（带透明通道），转换为RGB
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                        
                    width, height = img.size
                    
                    # 设置页面大小
                    c.setPageSize((width, height))
                    
                    # 添加图像到页面
                    c.drawImage(img_path, 0, 0, width=width, height=height)
                    c.showPage()
                    
                    # 关闭图像以释放资源
                    img.close()
                except Exception as e:
                    print(f"处理图像时出错 {img_path}: {e}")
                    # 继续处理其他图像，而不是终止整个过程
                    continue
            
            # 保存PDF
            c.save()
            
            return output_path
        except Exception as e:
            # 在发生异常时，尝试删除可能部分创建的PDF文件
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except:
                pass
            # 重新抛出异常，附带更多上下文
            raise Exception(f"创建PDF时出错: {str(e)}") 