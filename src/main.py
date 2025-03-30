#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from dotenv import load_dotenv

# Import project modules
from utils.pdf_processor import PDFProcessor
from utils.translator import DeepseekTranslator
from utils.vocabulary_extractor import VocabularyExtractor
from api.api_service import start_api_server

def main():
    """
    Main entry point for the PDF processing application
    """
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PDF Processing and Translation Tool')
    parser.add_argument('--pdf', type=str, help='Path to PDF file', default="America is facing a beef deficit.pdf")
    parser.add_argument('--api', action='store_true', help='Start API server')
    parser.add_argument('--margin', type=int, help='Note margin width percentage', 
                        default=int(os.getenv('NOTE_MARGIN_WIDTH_PERCENTAGE', 30)))
    parser.add_argument('--output', type=str, help='Output directory', default='output')
    parser.add_argument('--extract-method', type=str, choices=['pypdf2', 'pdfplumber', 'pdfminer', 'ocr', 'all'], 
                        default='pypdf2', help='Text extraction method')
    parser.add_argument('--compare', action='store_true', help='Compare all extraction methods')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    if args.api:
        # Start API server
        start_api_server()
    else:
        # Process the PDF file
        pdf_processor = PDFProcessor(args.pdf, args.margin)
        
        # Convert PDF to images with note space
        image_paths = pdf_processor.convert_to_images_with_notes()
        
        # Extract text content from PDF
        if args.compare or args.extract_method == 'all':
            print("Comparing all text extraction methods...")
            results = pdf_processor.extract_text_all_methods()
            
            # Save all extraction results
            for method, text in results.items():
                method_text_path = os.path.join(args.output, f'extracted_text_{method}.txt')
                with open(method_text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"Text extracted using {method} saved to {method_text_path}")
            
            # Use default method for further processing
            text_content = results[PDFProcessor.EXTRACT_METHOD_PYPDF2]
        else:
            print(f"Extracting text using {args.extract_method}...")
            text_content = pdf_processor.extract_text(method=args.extract_method)
        
        # Translate content using Deepseek API
        translator = DeepseekTranslator()
        translation = translator.translate(text_content)
        
        # Extract vocabulary
        vocabulary_extractor = VocabularyExtractor()
        vocabulary = vocabulary_extractor.extract_vocabulary(text_content)
        
        # Save results
        with open(os.path.join(args.output, 'translation.txt'), 'w', encoding='utf-8') as f:
            f.write(translation)
        
        with open(os.path.join(args.output, 'vocabulary.txt'), 'w', encoding='utf-8') as f:
            f.write(vocabulary)
        
        print(f"Processing complete. Results saved to {args.output} directory")
        print(f"Generated {len(image_paths)} page images with note space")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 