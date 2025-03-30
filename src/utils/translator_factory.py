#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
from dotenv import load_dotenv
import re

class TranslationModel:
    """
    翻译模型的基类，定义模型的基本属性和方法
    """
    def __init__(self, name, api_url, api_key_env, model_name, temperature=0.5, max_tokens=4000):
        """
        初始化翻译模型
        
        Args:
            name (str): 模型名称
            api_url (str): API URL
            api_key_env (str): 环境变量中API密钥的名称
            model_name (str): 模型标识符
            temperature (float): 温度参数，控制输出的随机性
            max_tokens (int): 最大生成的令牌数
        """
        # 加载环境变量
        load_dotenv(override=True)
        
        # 获取API密钥
        self.api_key = os.getenv(api_key_env)
        if not self.api_key:
            raise ValueError(f"{api_key_env} API key not found in environment variables.")
        
        # 设置基本属性
        self.name = name
        self.api_url = api_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # HTTP请求头
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def translate(self, text):
        """
        翻译文本（子类需要实现）
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def _create_translation_prompt(self, text):
        """
        创建翻译提示词（子类需要实现）
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def _call_api(self, messages):
        """
        调用API，发送请求并返回响应
        
        Args:
            messages (list): 消息内容
            
        Returns:
            dict: API响应
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_message = f"API请求失败，状态码 {response.status_code}: {response.text}"
                if response.status_code == 429:
                    error_message = f"服务器繁忙 (429): {response.text}"
                elif response.status_code == 401:
                    error_message = f"API认证失败 (401): {response.text}"
                
                raise Exception(error_message)
            
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"网络请求错误: {str(e)}")
    
    def _extract_translation(self, response):
        """
        从API响应中提取翻译内容
        
        Args:
            response (dict): API响应
            
        Returns:
            str: 翻译文本
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise Exception(f"无法从API响应中提取翻译: {e}")
    
    def extract_vocabulary(self, text):
        """
        从文本中提取词汇（通用方法，子类可以重写）
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            str: 提取的词汇
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        vocabulary_sections = []
        
        try:
            print(f"[DEBUG] {self.name}: 开始提取词汇, 共分割为 {len(chunks)} 个块")
            
            for i, chunk in enumerate(chunks):
                print(f"[DEBUG] {self.name}: 处理第 {i+1}/{len(chunks)} 个块")
                prompt = self._create_vocabulary_prompt(chunk)
                print(f"[DEBUG] {self.name}: 创建提示词完成，准备调用API")
                
                try:
                    response = self._call_api(prompt)
                    print(f"[DEBUG] {self.name}: API调用成功，分析返回内容")
                    
                    # 从响应中提取词汇部分
                    vocabulary = self._extract_formatted_vocabulary(response)
                    print(f"[DEBUG] {self.name}: 提取词汇内容完成，长度: {len(vocabulary) if vocabulary else 0}")
                    
                    if vocabulary:
                        print(f"[DEBUG] {self.name}: 发现词汇")
                        vocabulary_sections.append(vocabulary)
                except Exception as e:
                    print(f"[DEBUG] {self.name}: 处理块 {i+1} 时出错: {str(e)}")
                    raise
            
            # 合并所有词汇部分
            if vocabulary_sections:
                print(f"[DEBUG] {self.name}: 成功提取 {len(vocabulary_sections)} 个词汇部分")
                result = "\n\n".join(vocabulary_sections)
                return result
            else:
                print(f"[DEBUG] {self.name}: 未能提取任何词汇部分")
                return "未找到词汇解析部分。"
        except Exception as e:
            print(f"[DEBUG] {self.name}: 词汇提取过程中发生错误: {str(e)}")
            raise
    
    def _extract_formatted_vocabulary(self, response):
        """
        从API响应中提取格式化的词汇部分
        
        Args:
            response (dict): API响应
            
        Returns:
            str: 提取的词汇文本
        """
        content = self._extract_translation(response)
        
        # 尝试查找"重点词汇解析"部分
        if "重点词汇解析" in content:
            parts = content.split("重点词汇解析", 1)
            return "重点词汇解析" + parts[1].strip()
        
        # 如果没有找到特定标记，检查内容是否包含词汇格式（数字+英文词汇+中文含义）
        if re.search(r"\d+\.\s+\w+[：:]\s*[\u4e00-\u9fff]", content):
            return "重点词汇解析：\n" + content.strip()
        
        # 如果以上都失败，返回空字符串
        return ""
    
    def _create_vocabulary_prompt(self, text):
        """
        创建词汇提取提示词（通用方法，子类可以重写）
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英语词汇分析专家，特别擅长分析英文文本中的重点词汇和晦涩难懂的词汇。请从文本中按照出现顺序提取重要词汇并给出详细解析，不要重复提取相同的词汇。"},
            {"role": "user", "content": f"""请从以下英文文本中提取重要词汇和专业词汇，并按照以下格式提供中文解释和例句：

原文：
{text}

请仅提取重点词汇并按照以下要求进行处理：
1. 按照词汇在原文中的出现顺序提取
2. 不要重复提取相同的词汇
3. 每个词汇只提取一次
4. 专注于提取较难、较专业的词汇

请按照以下格式回复：

重点词汇解析：
1. [英文词汇]：[中文含义] - [例句]
2. [英文词汇]：[中文含义] - [例句]
...

不要提供翻译，只需要提供词汇分析。请严格按照格式回复，确保回复内容包含"重点词汇解析："这个标记。
"""}
        ]
    
    def _split_text(self, text, max_chunk_size=3000):
        """
        将文本分割成小块，避免超出token限制
        
        Args:
            text (str): 要分割的文本
            max_chunk_size (int): 每块的最大大小
            
        Returns:
            list: 文本块列表
        """
        if not text or len(text) <= max_chunk_size:
            return [text]
            
        # 按段落分割以保持上下文
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果添加这个段落会超出最大大小，则开始一个新块
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:  # 只在非空时添加
                    chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # 添加最后一块（如果非空）
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks


class DeepseekReasonerModel(TranslationModel):
    """
    使用Deepseek Reasoner模型的翻译器
    """
    
    def __init__(self):
        """
        初始化Deepseek Reasoner翻译模型
        """
        super().__init__(
            name="Deepseek Reasoner",
            api_url="https://api.deepseek.com/v1/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            model_name="deepseek-reasoner",
            temperature=0.7,
            max_tokens=4096
        )
    
    def translate(self, text):
        """
        翻译英文文本为中文
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            str: 翻译后的文本
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        translations = []
        
        for chunk in chunks:
            prompt = self._create_translation_prompt(chunk)
            response = self._call_api(prompt)
            
            # 提取翻译部分
            translation = self._extract_formatted_translation(response)
            translations.append(translation)
        
        # 合并所有翻译
        result = "\n\n".join(translations)
        
        # 确保结果以"翻译："开头
        if not result.strip().startswith("翻译："):
            result = "翻译：\n" + result
        
        return result
    
    def extract_vocabulary(self, text):
        """
        从文本中提取词汇
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            str: 提取的词汇
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        vocabulary_sections = []
        
        try:
            print(f"[DEBUG] {self.name}: 开始提取词汇, 共分割为 {len(chunks)} 个块")
            
            for i, chunk in enumerate(chunks):
                print(f"[DEBUG] {self.name}: 处理第 {i+1}/{len(chunks)} 个块")
                # 使用专门的词汇提取提示词
                prompt = self._create_vocabulary_prompt(chunk)
                print(f"[DEBUG] {self.name}: 创建提示词完成，准备调用API")
                
                try:
                    response = self._call_api(prompt)
                    print(f"[DEBUG] {self.name}: API调用成功，分析返回内容")
                    
                    # 提取词汇部分
                    vocabulary = self._extract_formatted_vocabulary(response)
                    print(f"[DEBUG] {self.name}: 提取词汇内容完成，长度: {len(vocabulary) if vocabulary else 0}")
                    
                    if vocabulary:
                        vocabulary_sections.append(vocabulary)
                except Exception as e:
                    print(f"[DEBUG] {self.name}: 处理块 {i+1} 时出错: {str(e)}")
                    raise
            
            # 合并所有词汇部分
            if vocabulary_sections:
                print(f"[DEBUG] {self.name}: 成功提取 {len(vocabulary_sections)} 个词汇部分")
                return "\n\n".join(vocabulary_sections)
            else:
                print(f"[DEBUG] {self.name}: 未能提取任何词汇部分")
                return "未找到词汇解析部分。"
        except Exception as e:
            print(f"[DEBUG] {self.name}: 词汇提取过程中发生错误: {str(e)}")
            raise
    
    def _create_translation_prompt(self, text):
        """
        创建翻译提示词
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英译中翻译专家。请将以下英文文本翻译成流畅、自然的中文。同时，识别文本中的考研重点词汇和晦涩难懂的词汇，并在翻译后提供这些词汇的中文解释和例句。请严格按照指定格式回复。"},
            {"role": "user", "content": f"""请翻译以下文本，请务必按照以下格式回复：

原文：
{text}

===开始翻译===
[在此处放置中文翻译，不要添加任何前缀]
===结束翻译===

===开始词汇解析===
重点词汇解析：
1. [英文词汇]：[中文含义] - [例句]
2. [英文词汇]：[中文含义] - [例句]
...
===结束词汇解析===
"""}
        ]
    
    def _extract_formatted_translation(self, response):
        """
        从格式化响应中提取翻译部分
        
        Args:
            response (dict): API响应
            
        Returns:
            str: 提取的翻译文本
        """
        content = self._extract_translation(response)
        
        # 尝试使用标记提取翻译部分
        if "===开始翻译===" in content and "===结束翻译===" in content:
            translation_start = content.find("===开始翻译===") + len("===开始翻译===")
            translation_end = content.find("===结束翻译===")
            if translation_end > translation_start:
                return content[translation_start:translation_end].strip()
        
        # 如果没有找到标记，尝试其他方法
        if "翻译：" in content and "重点词汇解析" in content:
            parts = content.split("重点词汇解析", 1)
            translation = parts[0].strip()
            # 如果以"翻译："开头，移除该前缀
            if translation.startswith("翻译："):
                translation = translation[len("翻译："):].strip()
            return translation
        
        # 如果以上都失败，返回整个内容
        return content
    
    def _extract_formatted_vocabulary(self, response):
        """
        从格式化响应中提取词汇部分
        
        Args:
            response (dict): API响应
            
        Returns:
            str: 提取的词汇文本
        """
        content = self._extract_translation(response)
        
        # 尝试使用标记提取词汇部分
        if "===开始词汇解析===" in content and "===结束词汇解析===" in content:
            vocab_start = content.find("===开始词汇解析===") + len("===开始词汇解析===")
            vocab_end = content.find("===结束词汇解析===")
            if vocab_end > vocab_start:
                return content[vocab_start:vocab_end].strip()
        
        # 如果没有找到标记，尝试其他方法
        if "重点词汇解析" in content:
            parts = content.split("重点词汇解析", 1)
            if len(parts) > 1:
                return "重点词汇解析" + parts[1].strip()
        
        # 如果以上都失败，返回空字符串
        return ""


class DeepseekChatModel(TranslationModel):
    """
    使用Deepseek Chat模型的翻译器
    """
    
    def __init__(self):
        """
        初始化Deepseek Chat翻译模型
        """
        super().__init__(
            name="Deepseek Chat",
            api_url="https://api.deepseek.com/v1/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=4096
        )
    
    def translate(self, text):
        """
        翻译英文文本为中文
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            str: 翻译后的文本
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        translations = []
        
        for chunk in chunks:
            prompt = self._create_translation_prompt(chunk)
            response = self._call_api(prompt)
            translation = self._extract_translation(response)
            translations.append(translation)
        
        # 合并所有翻译
        result = "\n\n".join(translations)
        
        # 确保结果以"翻译："开头
        if not result.strip().startswith("翻译："):
            result = "翻译：\n" + result
        
        return result
    
    def _create_translation_prompt(self, text):
        """
        创建翻译提示词
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英译中翻译专家。请将英文文本翻译成流畅、自然的中文。"},
            {"role": "user", "content": f"请将以下英文文本翻译成中文，保持专业、准确的翻译质量：\n\n{text}"}
        ]
    
    def extract_vocabulary(self, text):
        """
        从文本中提取词汇
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            str: 提取的词汇
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        vocabulary_sections = []
        
        try:
            print(f"[DEBUG] {self.name}: 开始提取词汇, 共分割为 {len(chunks)} 个块")
            
            for i, chunk in enumerate(chunks):
                print(f"[DEBUG] {self.name}: 处理第 {i+1}/{len(chunks)} 个块")
                prompt = self._create_vocabulary_prompt(chunk)
                print(f"[DEBUG] {self.name}: 创建提示词完成，准备调用API")
                
                try:
                    response = self._call_api(prompt)
                    print(f"[DEBUG] {self.name}: API调用成功，分析返回内容")
                    
                    # 直接使用返回内容
                    vocabulary = self._extract_translation(response)
                    print(f"[DEBUG] {self.name}: 提取词汇内容完成，长度: {len(vocabulary) if vocabulary else 0}")
                    
                    if vocabulary and "重点词汇解析" in vocabulary:
                        print(f"[DEBUG] {self.name}: 发现词汇标记")
                        vocabulary_sections.append(vocabulary)
                    elif vocabulary:
                        print(f"[DEBUG] {self.name}: 未找到词汇标记，添加标准前缀")
                        vocabulary_sections.append("重点词汇解析：\n" + vocabulary)
                except Exception as e:
                    print(f"[DEBUG] {self.name}: 处理块 {i+1} 时出错: {str(e)}")
                    raise
            
            # 合并所有词汇部分
            if vocabulary_sections:
                print(f"[DEBUG] {self.name}: 成功提取 {len(vocabulary_sections)} 个词汇部分")
                return "\n\n".join(vocabulary_sections)
            else:
                print(f"[DEBUG] {self.name}: 未能提取任何词汇部分")
                return "未找到词汇解析部分。"
        except Exception as e:
            print(f"[DEBUG] {self.name}: 词汇提取过程中发生错误: {str(e)}")
            raise
    
    def _create_vocabulary_prompt(self, text):
        """
        创建词汇提取提示词
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英语词汇分析专家，特别擅长分析英文文本中的重点词汇和晦涩难懂的词汇。请从文本中按照出现顺序提取重要词汇并给出详细解析，不要重复提取相同的词汇。"},
            {"role": "user", "content": f"""请从以下英文文本中提取重要词汇和专业词汇，并按照以下格式提供中文解释和例句：

原文：
{text}

请仅提取重点词汇并按照以下要求进行处理：
1. 按照词汇在原文中的出现顺序提取
2. 不要重复提取相同的词汇
3. 每个词汇只提取一次
4. 专注于提取较难、较专业的词汇

请按照以下格式回复：

重点词汇解析：
1. [英文词汇]：[中文含义] - [例句]
2. [英文词汇]：[中文含义] - [例句]
...

不要提供翻译，只需要提供词汇分析。请严格按照格式回复，确保回复内容包含"重点词汇解析："这个标记。
"""}
        ]


class OpenRouterDeepseekModel(TranslationModel):
    """
    通过OpenRouter API使用Deepseek模型的翻译器
    """
    
    def __init__(self):
        """
        初始化OpenRouter Deepseek翻译模型
        """
        super().__init__(
            name="OpenRouter Deepseek",
            api_url="https://openrouter.ai/api/v1/chat/completions",
            api_key_env="OPENROUTER_API_KEY",
            model_name="deepseek/deepseek-chat",
            temperature=0.3,
            max_tokens=4000
        )
        
        # 添加OpenRouter特定的头信息
        self.headers.update({
            "HTTP-Referer": "https://pdf-reader-assistant.com",
            "X-Title": "PDF Reader Assistant"
        })
    
    def translate(self, text):
        """
        翻译英文文本为中文
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            str: 翻译后的文本
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        translations = []
        
        for chunk in chunks:
            prompt = self._create_translation_prompt(chunk)
            response = self._call_api(prompt)
            translation = self._extract_translation(response)
            translations.append(translation)
        
        # 合并所有翻译
        result = "\n\n".join(translations)
        
        # 确保结果以"翻译："开头
        if not result.strip().startswith("翻译："):
            result = "翻译：\n" + result
        
        return result
    
    def _create_translation_prompt(self, text):
        """
        创建翻译提示词
        
        Args:
            text (str): 要翻译的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英译中翻译专家。请将英文文本翻译成流畅、自然的中文。"},
            {"role": "user", "content": f"请将以下英文文本翻译成中文，保持专业、准确的翻译质量：\n\n{text}"}
        ]
    
    def extract_vocabulary(self, text):
        """
        从文本中提取词汇
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            str: 提取的词汇
        """
        # 分割文本为小块
        chunks = self._split_text(text)
        vocabulary_sections = []
        
        try:
            print(f"[DEBUG] {self.name}: 开始提取词汇, 共分割为 {len(chunks)} 个块")
            
            for i, chunk in enumerate(chunks):
                print(f"[DEBUG] {self.name}: 处理第 {i+1}/{len(chunks)} 个块")
                prompt = self._create_vocabulary_prompt(chunk)
                print(f"[DEBUG] {self.name}: 创建提示词完成，准备调用API")
                
                try:
                    response = self._call_api(prompt)
                    print(f"[DEBUG] {self.name}: API调用成功，分析返回内容")
                    
                    # 直接使用返回内容
                    vocabulary = self._extract_translation(response)
                    print(f"[DEBUG] {self.name}: 提取词汇内容完成，长度: {len(vocabulary) if vocabulary else 0}")
                    
                    if vocabulary and "重点词汇解析" in vocabulary:
                        print(f"[DEBUG] {self.name}: 发现词汇标记")
                        vocabulary_sections.append(vocabulary)
                    elif vocabulary:
                        print(f"[DEBUG] {self.name}: 未找到词汇标记，添加标准前缀")
                        vocabulary_sections.append("重点词汇解析：\n" + vocabulary)
                except Exception as e:
                    print(f"[DEBUG] {self.name}: 处理块 {i+1} 时出错: {str(e)}")
                    raise
            
            # 合并所有词汇部分
            if vocabulary_sections:
                print(f"[DEBUG] {self.name}: 成功提取 {len(vocabulary_sections)} 个词汇部分")
                return "\n\n".join(vocabulary_sections)
            else:
                print(f"[DEBUG] {self.name}: 未能提取任何词汇部分")
                return "未找到词汇解析部分。"
        except Exception as e:
            print(f"[DEBUG] {self.name}: 词汇提取过程中发生错误: {str(e)}")
            raise
    
    def _create_vocabulary_prompt(self, text):
        """
        创建词汇提取提示词
        
        Args:
            text (str): 要提取词汇的文本
            
        Returns:
            list: 格式化的提示词
        """
        return [
            {"role": "system", "content": "你是一个专业的英语词汇分析专家，特别擅长分析英文文本中的重点词汇和晦涩难懂的词汇。请从文本中按照出现顺序提取重要词汇并给出详细解析，不要重复提取相同的词汇。"},
            {"role": "user", "content": f"""请从以下英文文本中提取重要词汇和专业词汇，并按照以下格式提供中文解释和例句：

原文：
{text}

请仅提取重点词汇并按照以下要求进行处理：
1. 按照词汇在原文中的出现顺序提取
2. 不要重复提取相同的词汇
3. 每个词汇只提取一次
4. 专注于提取较难、较专业的词汇

请按照以下格式回复：

重点词汇解析：
1. [英文词汇]：[中文含义] - [例句]
2. [英文词汇]：[中文含义] - [例句]
...

不要提供翻译，只需要提供词汇分析。请严格按照格式回复，确保回复内容包含"重点词汇解析："这个标记。
"""}
        ]


class TranslatorFactory:
    """
    翻译器工厂类，用于创建不同的翻译模型实例
    """
    # 模型类型常量
    MODEL_DEEPSEEK_REASONER = "deepseek-reasoner"
    MODEL_DEEPSEEK_CHAT = "deepseek-chat"
    MODEL_OPENROUTER_DEEPSEEK = "openrouter-deepseek"
    MODEL_AUTO = "auto"
    
    # 向后兼容的翻译器类型常量
    TRANSLATOR_DEEPSEEK = "deepseek"
    TRANSLATOR_OPENROUTER = "openrouter"
    TRANSLATOR_AUTO = "auto"
    
    @staticmethod
    def create_translator(model_type=MODEL_AUTO):
        """
        创建翻译器实例
        
        Args:
            model_type (str): 模型类型
            
        Returns:
            TranslationModel: 翻译模型实例
        """
        # 处理向后兼容性
        if model_type == TranslatorFactory.TRANSLATOR_DEEPSEEK:
            model_type = TranslatorFactory.MODEL_DEEPSEEK_REASONER
        elif model_type == TranslatorFactory.TRANSLATOR_OPENROUTER:
            model_type = TranslatorFactory.MODEL_OPENROUTER_DEEPSEEK
        
        # 创建对应的模型实例
        if model_type == TranslatorFactory.MODEL_DEEPSEEK_REASONER:
            return DeepseekReasonerModel()
        elif model_type == TranslatorFactory.MODEL_DEEPSEEK_CHAT:
            return DeepseekChatModel()
        elif model_type == TranslatorFactory.MODEL_OPENROUTER_DEEPSEEK:
            return OpenRouterDeepseekModel()
        elif model_type == TranslatorFactory.MODEL_AUTO:
            # 为了保持简单，Auto现在直接返回Deepseek Reasoner
            # 如果需要自动故障转移，应用程序可以自行处理异常并切换模型
            return DeepseekReasonerModel()
        else:
            raise ValueError(f"未知的模型类型: {model_type}")

# 为保持向后兼容性
DeepseekTranslator = DeepseekReasonerModel
OpenRouterTranslator = OpenRouterDeepseekModel 