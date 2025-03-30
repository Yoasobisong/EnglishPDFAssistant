#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
极简测试服务器，专门用于测试API路由问题
"""

import os
import sys
import json
from flask import Flask, request, jsonify, render_template

# 创建Flask应用
app = Flask(__name__)

# 简单任务字典
tasks = {}

@app.route('/')
def index():
    """首页"""
    return "测试服务器正常运行中，API路由测试页面 <a href='/test'>点击这里</a>"

@app.route('/test')
def test_page():
    """测试页面"""
    return """
    <html>
    <head>
        <title>API测试</title>
    </head>
    <body>
        <h1>API测试页面</h1>
        <button onclick="testApi()">测试API</button>
        <div id="result"></div>
        
        <script>
        function testApi() {
            fetch('/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task_id: '123',
                    extract_method: 'image',
                    translator_type: 'auto'
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').innerText = JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('result').innerText = 'Error: ' + error;
            });
        }
        </script>
    </body>
    </html>
    """

@app.route('/api/process', methods=['POST'])
def api_process():
    """处理API"""
    data = request.json
    task_id = data.get('task_id', 'unknown')
    
    # 存储任务信息
    tasks[task_id] = {
        'status': 'processing',
        'extract_method': data.get('extract_method', 'image'),
        'translator_type': data.get('translator_type', 'auto')
    }
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'processing',
        'message': '请求已成功处理！'
    })

@app.route('/api/task/<task_id>', methods=['GET'])
def task_status(task_id):
    """任务状态API"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
        
    return jsonify({
        'task_id': task_id,
        'status': tasks[task_id].get('status', 'unknown'),
        'details': tasks[task_id]
    })

if __name__ == '__main__':
    print("启动测试服务器...")
    print("访问 http://localhost:5001/ 查看首页")
    print("访问 http://localhost:5001/test 进行API测试")
    app.run(debug=True, host='0.0.0.0', port=5001) 