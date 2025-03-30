#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于测试DeepseekReasonerModel和DeepseekChatModel翻译器
"""

import os
import sys
import time
import json
import argparse
import requests
from dotenv import load_dotenv

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# 导入翻译模型
from src.utils.translator_factory import (
    DeepseekReasonerModel,
    DeepseekChatModel,
    OpenRouterDeepseekModel
)

def test_translator(translator, text):
    """
    测试翻译器并打印结果
    
    Args:
        translator: 翻译器实例
        text (str): 测试文本
    """
    translator_name = translator.name
    print(f"\n{'='*20} 正在测试 {translator_name} {'='*20}")
    
    try:
        # 打印起始时间
        start_time = time.time()
        print(f"开始翻译... ({time.strftime('%H:%M:%S')})")
        
        # 执行翻译
        result = translator.translate(text)
        
        # 计算执行时间
        end_time = time.time()
        duration = end_time - start_time
        
        # 打印结果
        print(f"\n翻译完成，耗时 {duration:.2f} 秒")
        print(f"\n{'-'*50}\n结果:\n{'-'*50}\n")
        print(result)
        print(f"\n{'-'*50}\n")
        
        return True
    except Exception as e:
        print(f"翻译出错: {e}")
        return False

def create_translators():
    """
    创建所有可用的翻译器实例
    
    Returns:
        dict: 翻译器名称到实例的映射
    """
    # 加载环境变量
    load_dotenv(override=True)
    
    # 检查API密钥
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not deepseek_api_key and not openrouter_api_key:
        print("错误: 未找到任何API密钥。请在.env文件中设置DEEPSEEK_API_KEY或OPENROUTER_API_KEY。")
        return {}
    
    # 初始化翻译器
    translators = {}
    
    if deepseek_api_key:
        try:
            translators["deepseek-reasoner"] = DeepseekReasonerModel()
            translators["deepseek-chat"] = DeepseekChatModel()
        except Exception as e:
            print(f"初始化Deepseek翻译器时出错: {e}")
    
    if openrouter_api_key:
        try:
            translators["openrouter-deepseek"] = OpenRouterDeepseekModel()
        except Exception as e:
            print(f"初始化OpenRouter翻译器时出错: {e}")
    
    return translators

def chat_mode():
    """
    与模型进行对话模式
    """
    # 加载环境变量
    load_dotenv(override=True)
    
    # 获取API密钥
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        print("错误: 未找到Deepseek API密钥。请在.env文件中设置DEEPSEEK_API_KEY。")
        return
    
    print("\n欢迎使用Deepseek AI对话测试！")
    print("可用的模型:")
    print("1. deepseek-reasoner (推理模型)")
    print("2. deepseek-chat (聊天模型)")
    
    # 选择模型
    while True:
        choice = input("\n请选择模型 (1-2, 'q'退出): ")
        if choice.lower() == 'q':
            print("退出程序")
            return
        
        if choice == '1':
            model = "deepseek-reasoner"
            print(f"已选择: {model}")
            break
        elif choice == '2':
            model = "deepseek-chat"
            print(f"已选择: {model}")
            break
        else:
            print("错误: 无效的选择，请输入1-2或'q'。")
    
    # 对话历史
    messages = [{"role": "system", "content": "你是一个有用的AI助手。请用中文回复用户的问题。"}]
    
    print("\n开始对话! (输入'quit'或'exit'结束对话)")
    print("系统: 你好！我是Deepseek AI助手，有什么可以帮助你的吗？")
    
    while True:
        # 获取用户输入
        user_input = input("\n你: ")
        if user_input.lower() in ['quit', 'exit', '退出', 'q']:
            print("系统: 谢谢使用，再见！")
            break
        
        # 添加用户消息到历史
        messages.append({"role": "user", "content": user_input})
        
        try:
            # 调用API
            start_time = time.time()
            print("\n正在思考...")
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {deepseek_api_key}"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=60  # 60秒超时
            )
            
            # 计算响应时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"错误: API请求失败，状态码 {response.status_code}")
                print(f"详细信息: {response.text}")
                retry = input("是否重试? (y/n): ")
                if retry.lower() != 'y':
                    break
                continue
            
            # 解析响应
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # 添加到对话历史
                messages.append({"role": "assistant", "content": content})
                # 输出结果
                print(f"\n系统 ({duration:.2f}秒): {content}")
            else:
                print("错误: 无法从API响应中提取内容")
                print(f"API响应: {result}")
        
        except Exception as e:
            print(f"发生错误: {str(e)}")
            retry = input("是否重试? (y/n): ")
            if retry.lower() != 'y':
                break

def interactive_mode():
    """
    交互式测试模式
    """
    # 创建翻译器
    translators = create_translators()
    
    if not translators:
        print("错误: 无法初始化任何翻译器。请检查API密钥是否有效。")
        return
    
    print("\n欢迎使用翻译器测试程序!")
    print("可用的翻译模型:")
    
    # 显示可用的翻译器
    for i, (name, translator) in enumerate(translators.items(), 1):
        print(f"{i}. {translator.name}")
    
    # 模型选择循环
    while True:
        try:
            # 获取用户选择
            choice = input("\n请选择翻译模型 (输入编号, 'a'使用所有模型, 或 'q'退出): ")
            
            if choice.lower() == 'q':
                print("退出程序")
                break
            
            selected_translators = []
            
            if choice.lower() == 'a':
                selected_translators = list(translators.values())
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(translators):
                        selected_translators = [list(translators.values())[idx]]
                    else:
                        print(f"错误: 无效的选择。请输入1到{len(translators)}之间的数字。")
                        continue
                except ValueError:
                    print("错误: 请输入有效的数字、'a'或'q'。")
                    continue
            
            # 获取测试文本
            print("\n请输入要翻译的文本 (输入多行文本, 输入空行结束):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            text = "\n".join(lines)
            
            if not text.strip():
                print("错误: 没有输入任何文本。")
                continue
            
            # 测试选定的翻译器
            for translator in selected_translators:
                test_translator(translator, text)
            
            print("\n所有测试完成!")
            retry = input("是否继续测试? (y/n): ")
            if retry.lower() != 'y':
                print("退出程序")
                break
                
        except KeyboardInterrupt:
            print("\n收到中断信号，退出程序")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            retry = input("是否继续? (y/n): ")
            if retry.lower() != 'y':
                print("退出程序")
                break

def batch_test(text):
    """
    批量测试所有翻译器
    
    Args:
        text (str): 测试文本
    """
    translators = create_translators()
    
    if not translators:
        print("错误: 无法初始化任何翻译器。请检查API密钥是否有效。")
        return
    
    # 测试每个翻译器
    for translator in translators.values():
        test_translator(translator, text)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="翻译器测试工具")
    parser.add_argument("-i", "--interactive", action="store_true", help="启用交互式模式")
    parser.add_argument("-c", "--chat", action="store_true", help="启用对话模式")
    parser.add_argument("-t", "--text", help="要翻译的文本")
    args = parser.parse_args()
    
    if args.chat:
        chat_mode()
    elif args.interactive:
        interactive_mode()
    elif args.text:
        batch_test(args.text)
    else:
        # 提示用户选择模式
        print("请选择运行模式:")
        print("1. 翻译测试 (默认)")
        print("2. 交互式模式")
        print("3. 对话模式")
        
        try:
            mode = input("请输入模式编号 (1-3): ")
            if mode == "2":
                interactive_mode()
            elif mode == "3":
                chat_mode()
            else:
                # 默认测试文本
                default_text = """
                Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to human or animal intelligence. 
                The field draws heavily from computer science and mathematics. Major AI applications include natural language 
                processing, machine learning, computer vision, and robotics. AI technologies perform specific tasks that 
                traditionally required human intelligence, such as visual perception, speech recognition, decision-making, and 
                translation between languages.
                """
                batch_test(default_text)
        except KeyboardInterrupt:
            print("\n收到中断信号，退出程序")

if __name__ == "__main__":
    main() 