#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from dotenv import load_dotenv

class VocabularyExtractor:
    """
    Class for extracting important vocabulary from text.
    """
    
    def __init__(self):
        """
        Initialize the VocabularyExtractor.
        Loads necessary API keys from environment variables.
        """
        load_dotenv()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("Deepseek API key not found in environment variables.")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Common words to exclude (could be extended)
        self.common_words = set([
            "the", "and", "for", "that", "with", "this", "from", "have", "has", "had",
            "not", "are", "were", "was", "will", "would", "should", "could", "been", "being"
        ])
    
    def extract_vocabulary(self, text):
        """
        Extract important vocabulary from the text.
        
        Args:
            text (str): Text to extract vocabulary from
            
        Returns:
            str: Formatted vocabulary list with explanations
        """
        try:
            # Split text into chunks if it's too long (max 4096 tokens approx)
            max_chunk_size = 3000  # characters, not tokens
            chunks = self._split_text(text, max_chunk_size)
            
            all_vocabulary = []
            for chunk in chunks:
                # Prepare the prompt
                prompt = self._create_vocabulary_prompt(chunk)
                
                # Make API request
                response = self._call_api(prompt)
                
                # Extract vocabulary from response
                chunk_vocabulary = self._extract_vocabulary_from_response(response)
                all_vocabulary.append(chunk_vocabulary)
            
            # Combine all vocabulary
            full_vocabulary = "\n\n".join(all_vocabulary)
            return full_vocabulary
            
        except Exception as e:
            raise Exception(f"Vocabulary extraction failed: {e}")
    
    def _split_text(self, text, max_chunk_size):
        """
        Split text into smaller chunks to avoid token limits.
        
        Args:
            text (str): Text to split
            max_chunk_size (int): Maximum size of each chunk
            
        Returns:
            list: List of text chunks
        """
        # Split by paragraph to maintain context
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size, start a new chunk
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:  # Only append if not empty
                    chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _create_vocabulary_prompt(self, text):
        """
        Create a prompt for vocabulary extraction API.
        
        Args:
            text (str): Text to extract vocabulary from
            
        Returns:
            list: Formatted prompt for API
        """
        return [
            {"role": "system", "content": "你是一个专业的英语词汇分析专家，特别擅长分析学术文章中的考研重点词汇和晦涩难懂的专业词汇。请从给定的英文文本中识别并提取重要的词汇，尤其是考研词汇和专业词汇，并提供其中文解释和英文例句。"},
            {"role": "user", "content": f"请从以下文本中提取重要的考研词汇和专业词汇，并按照以下格式提供中文解释和例句：\n\n{text}\n\n请按照以下格式回复：\n\n重要词汇列表：\n\n1. [英文词汇]：[中文解释]\n例句：[包含该词的英文例句]\n解析：[详细语法或用法解释]\n\n2. [英文词汇]：[中文解释]\n例句：[包含该词的英文例句]\n解析：[详细语法或用法解释]\n\n..."}
        ]
    
    def _call_api(self, messages):
        """
        Call the Deepseek API.
        
        Args:
            messages (list): Messages to send to API
            
        Returns:
            dict: API response
        """
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            data=json.dumps(payload)
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
        
        return response.json()
    
    def _extract_vocabulary_from_response(self, response):
        """
        Extract vocabulary from API response.
        
        Args:
            response (dict): API response
            
        Returns:
            str: Extracted vocabulary
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to extract vocabulary from API response: {e}")
    
    def extract_vocabulary_manually(self, text):
        """
        Simple rule-based extraction of potentially important vocabulary.
        This is a fallback method if API fails or for development/testing.
        
        Args:
            text (str): Text to extract vocabulary from
            
        Returns:
            list: List of potentially important words
        """
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = text.split()
        
        # Filter out common words and short words
        potential_vocabulary = [word for word in words if word not in self.common_words and len(word) > 3]
        
        # Count frequency
        word_freq = {}
        for word in potential_vocabulary:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # Sort by frequency
        sorted_vocab = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top words
        top_words = [word for word, freq in sorted_vocab[:30]]
        
        return top_words 