#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF阅读助手 Web应用入口脚本
运行此脚本启动Web服务
"""

import os
import sys
from src.web.app import app

if __name__ == "__main__":
    # 确保Web应用目录存在
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'web')
    static_dir = os.path.join(web_dir, 'static')
    templates_dir = os.path.join(web_dir, 'templates')
    
    # 创建必要的目录
    for directory in [web_dir, static_dir, os.path.join(static_dir, 'css'), templates_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # 确保output目录存在
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 启动Web应用
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    print(f"启动Web应用，访问地址: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    app.run(host=host, port=port, debug=debug)