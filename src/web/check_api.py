#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单测试脚本，检查API路由是否能正确访问
"""

import os
import sys
import json
from flask import Flask, request, jsonify

# 创建Flask应用
app = Flask(__name__)

# 路由测试
@app.route('/api/test', methods=['GET'])
def api_test():
    """简单测试API端点"""
    return jsonify({
        'status': 'success',
        'message': 'API测试成功'
    })

@app.route('/api/process', methods=['POST'])
def api_process():
    """模拟处理API"""
    data = request.json
    return jsonify({
        'success': True,
        'task_id': data.get('task_id', 'unknown'),
        'status': 'processing'
    })

if __name__ == '__main__':
    print("启动测试API服务器...")
    app.run(debug=True, host='0.0.0.0', port=5000) 