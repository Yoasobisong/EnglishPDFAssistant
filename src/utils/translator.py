#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 导入翻译工厂
from .translator_factory import (
    TranslatorFactory, 
    DeepseekReasonerModel,
    DeepseekChatModel,
    OpenRouterDeepseekModel,
    DeepseekTranslator,  # 向后兼容
    OpenRouterTranslator  # 向后兼容
)

# 为了向后兼容，保留原来的类名
Translator = TranslatorFactory

# 导出更多的类以便其他模块使用
__all__ = [
    'TranslatorFactory',
    'DeepseekTranslator',
    'DeepseekReasonerModel',
    'DeepseekChatModel',
    'OpenRouterDeepseekModel',
    'OpenRouterTranslator',
    'Translator'
] 