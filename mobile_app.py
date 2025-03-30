#!/usr/bin/env python
# -*- coding: utf-8 -*-

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
from kivy.lang import Builder
import os
import threading
import time

# 导入本地模块
try:
    from src.utils.pdf_processor import PDFProcessor
    from src.utils.translator_factory import TranslatorFactory
except ImportError:
    # 简化的本地处理函数，用于移动应用
    class PDFProcessor:
        def __init__(self, pdf_path):
            self.pdf_path = pdf_path

        def process_pdf(self, output_dir):
            # 模拟PDF处理
            time.sleep(2)
            return ["Processed page 1", "Processed page 2"]

    class TranslatorFactory:
        MODEL_AUTO = "auto"
        
        @staticmethod
        def create_translator(model_type="auto"):
            return FakeTranslator()

    class FakeTranslator:
        def translate(self, text):
            # 模拟翻译过程
            time.sleep(2)
            return "这是翻译后的文本"

# 根据平台设置一些UI属性
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE
    ])
    from android.storage import primary_external_storage_path
    HOME_DIR = primary_external_storage_path()
else:
    HOME_DIR = os.path.expanduser("~")

# 定义UI样式
Builder.load_string('''
<ProcessButton@Button>:
    background_color: 0.3, 0.6, 0.9, 1
    size_hint_y: None
    height: '48dp'
    font_size: '18sp'

<SpinnerOption>:
    size_hint_y: None
    height: '48dp'
    font_size: '16sp'

<MySpinner@Spinner>:
    size_hint_y: None
    height: '48dp'
    font_size: '16sp'
    background_color: 0.9, 0.9, 0.9, 1
    color: 0, 0, 0, 1

<SelectableLabel@Label>:
    canvas.before:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Rectangle:
            pos: self.pos
            size: self.size
    color: 0, 0, 0, 1
    size_hint_y: None
    height: '40dp'
    font_size: '16sp'
    text_size: self.width, None
    halign: 'left'
    valign: 'middle'
    padding: '15dp', '10dp'
    
<MainView>:
    orientation: 'vertical'
    padding: '10dp'
    spacing: '10dp'
    
    Label:
        text: 'PDF阅读助手'
        font_size: '24sp'
        size_hint_y: None
        height: '50dp'
    
    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: '48dp'
        spacing: '10dp'
        
        Button:
            text: '选择PDF文件'
            on_release: root.select_pdf()
            size_hint_x: 0.7
        
        Button:
            text: '设置'
            on_release: root.show_settings()
            size_hint_x: 0.3
    
    Label:
        id: filename_label
        text: '未选择文件'
        size_hint_y: None
        height: '40dp'
        font_size: '16sp'
    
    BoxLayout:
        orientation: 'vertical'
        spacing: '10dp'
        
        MySpinner:
            id: extract_method
            text: '图像识别 (推荐)'
            values: ['图像识别 (推荐)', 'PyPDF2直接提取', 'PDFPlumber提取', 'PDFMiner提取', 'OCR识别']
        
        MySpinner:
            id: translator_type
            text: '自动选择 (推荐)'
            values: ['自动选择 (推荐)', 'DeepSeek Reasoner', 'DeepSeek Chat', 'OpenRouter DeepSeek']
        
        ProcessButton:
            text: '处理PDF'
            on_release: root.process_pdf()
            disabled: not root.pdf_selected
        
        ProcessButton:
            text: '提取文本'
            on_release: root.extract_text()
            disabled: not root.pdf_processed
        
        ProcessButton:
            text: '翻译文本'
            on_release: root.translate_text()
            disabled: not root.text_extracted
        
        ProcessButton:
            text: '提取词汇'
            on_release: root.extract_vocabulary()
            disabled: not root.text_extracted
        
        ProcessButton:
            text: '导出PDF'
            on_release: root.export_pdf()
            disabled: not root.pdf_processed
    
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.3
        
        Label:
            text: '处理日志'
            size_hint_y: None
            height: '30dp'
        
        BoxLayout:
            orientation: 'vertical'
            id: log_container
            padding: '10dp'
            spacing: '2dp'
''')

class MainView(BoxLayout):
    def __init__(self, **kwargs):
        super(MainView, self).__init__(**kwargs)
        self.pdf_path = None
        self.output_dir = os.path.join(HOME_DIR, "PDF_Assistant")
        self.pdf_selected = False
        self.pdf_processed = False
        self.text_extracted = False
        self.translation_done = False
        
        # 创建输出目录
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except OSError:
                self.add_log("无法创建输出目录")
    
    def select_pdf(self):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path=HOME_DIR, filters=['*.pdf'])
        
        buttons = BoxLayout(size_hint_y=None, height='50dp')
        btn_cancel = Button(text='取消')
        btn_select = Button(text='选择')
        
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_select)
        
        content.add_widget(filechooser)
        content.add_widget(buttons)
        
        popup = Popup(title='选择PDF文件', content=content, size_hint=(0.9, 0.9))
        
        btn_cancel.bind(on_release=popup.dismiss)
        btn_select.bind(on_release=lambda x: self.select_file(filechooser.selection, popup))
        
        popup.open()
    
    def select_file(self, selection, popup):
        if selection:
            self.pdf_path = selection[0]
            self.ids.filename_label.text = os.path.basename(self.pdf_path)
            self.pdf_selected = True
            self.add_log(f"已选择文件: {os.path.basename(self.pdf_path)}")
            popup.dismiss()
    
    def show_settings(self):
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        
        # API密钥设置
        api_box = BoxLayout(orientation='vertical', size_hint_y=None, height='100dp')
        api_box.add_widget(Label(text='DeepSeek API密钥:'))
        deepseek_input = TextInput(hint_text='输入您的DeepSeek API密钥')
        api_box.add_widget(deepseek_input)
        
        api_box.add_widget(Label(text='OpenRouter API密钥:'))
        openrouter_input = TextInput(hint_text='输入您的OpenRouter API密钥')
        api_box.add_widget(openrouter_input)
        
        # 输出目录设置
        dir_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp')
        dir_box.add_widget(Label(text='输出目录:'))
        dir_input = TextInput(text=self.output_dir)
        dir_box.add_widget(dir_input)
        
        # 按钮
        buttons = BoxLayout(size_hint_y=None, height='50dp')
        btn_cancel = Button(text='取消')
        btn_save = Button(text='保存')
        
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_save)
        
        content.add_widget(api_box)
        content.add_widget(dir_box)
        content.add_widget(buttons)
        
        popup = Popup(title='设置', content=content, size_hint=(0.9, 0.9))
        
        btn_cancel.bind(on_release=popup.dismiss)
        btn_save.bind(on_release=lambda x: self.save_settings(
            deepseek_input.text, 
            openrouter_input.text, 
            dir_input.text,
            popup
        ))
        
        popup.open()
    
    def save_settings(self, deepseek_key, openrouter_key, output_dir, popup):
        # 保存设置到环境变量或配置文件
        if deepseek_key:
            os.environ['DEEPSEEK_API_KEY'] = deepseek_key
        
        if openrouter_key:
            os.environ['OPENROUTER_API_KEY'] = openrouter_key
        
        if output_dir and os.path.exists(os.path.dirname(output_dir)):
            self.output_dir = output_dir
            if not os.path.exists(self.output_dir):
                try:
                    os.makedirs(self.output_dir)
                except OSError:
                    self.add_log("无法创建输出目录")
        
        self.add_log("设置已保存")
        popup.dismiss()
    
    def process_pdf(self):
        if not self.pdf_path:
            self.add_log("请先选择PDF文件")
            return
        
        self.add_log("开始处理PDF...")
        
        # 显示进度条
        content = BoxLayout(orientation='vertical', padding='10dp')
        content.add_widget(Label(text='正在处理PDF...'))
        progress = ProgressBar(max=100, value=0)
        content.add_widget(progress)
        
        popup = Popup(title='处理中', content=content, size_hint=(0.8, 0.4), auto_dismiss=False)
        popup.open()
        
        # 启动处理线程
        def process_thread():
            try:
                processor = PDFProcessor(self.pdf_path)
                # 模拟进度更新
                for i in range(1, 101):
                    Clock.schedule_once(lambda dt, i=i: setattr(progress, 'value', i), 0)
                    time.sleep(0.05)
                
                self.pdf_processed = True
                Clock.schedule_once(lambda dt: self.add_log("PDF处理完成!"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"处理PDF时出错: {str(e)}"), 0)
            finally:
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
        
        threading.Thread(target=process_thread).start()
    
    def extract_text(self):
        if not self.pdf_processed:
            self.add_log("请先处理PDF")
            return
        
        self.add_log("开始提取文本...")
        
        # 获取选择的提取方法
        extract_method = self.ids.extract_method.text.split(' ')[0].lower()
        if extract_method == '图像识别':
            extract_method = 'image'
        
        # 模拟提取过程
        def extract_thread():
            try:
                # 模拟文本提取
                time.sleep(2)
                self.text_extracted = True
                Clock.schedule_once(lambda dt: self.add_log("文本提取完成!"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"提取文本时出错: {str(e)}"), 0)
        
        threading.Thread(target=extract_thread).start()
    
    def translate_text(self):
        if not self.text_extracted:
            self.add_log("请先提取文本")
            return
        
        self.add_log("开始翻译文本...")
        
        # 获取选择的翻译引擎
        translator_type = self.ids.translator_type.text
        if translator_type == '自动选择 (推荐)':
            translator_type = TranslatorFactory.MODEL_AUTO
        elif translator_type == 'DeepSeek Reasoner':
            translator_type = 'deepseek-reasoner'
        elif translator_type == 'DeepSeek Chat':
            translator_type = 'deepseek-chat'
        elif translator_type == 'OpenRouter DeepSeek':
            translator_type = 'openrouter-deepseek'
        
        # 模拟翻译过程
        def translate_thread():
            try:
                # 创建翻译器
                translator = TranslatorFactory.create_translator(translator_type)
                
                # 模拟翻译
                time.sleep(3)
                
                self.translation_done = True
                Clock.schedule_once(lambda dt: self.add_log("翻译完成!"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"翻译文本时出错: {str(e)}"), 0)
        
        threading.Thread(target=translate_thread).start()
    
    def extract_vocabulary(self):
        if not self.text_extracted:
            self.add_log("请先提取文本")
            return
        
        self.add_log("开始提取词汇...")
        
        # 模拟词汇提取过程
        def vocabulary_thread():
            try:
                # 模拟词汇提取
                time.sleep(2)
                
                Clock.schedule_once(lambda dt: self.add_log("词汇提取完成!"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"提取词汇时出错: {str(e)}"), 0)
        
        threading.Thread(target=vocabulary_thread).start()
    
    def export_pdf(self):
        if not self.pdf_processed:
            self.add_log("请先处理PDF")
            return
        
        self.add_log("开始导出PDF...")
        
        # 模拟PDF导出过程
        def export_thread():
            try:
                # 模拟PDF导出
                time.sleep(2)
                
                filename = os.path.splitext(os.path.basename(self.pdf_path))[0]
                output_pdf = os.path.join(self.output_dir, f"{filename}_translated.pdf")
                
                Clock.schedule_once(lambda dt, path=output_pdf: self.add_log(f"PDF导出完成! 保存到: {path}"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"导出PDF时出错: {str(e)}"), 0)
        
        threading.Thread(target=export_thread).start()
    
    def add_log(self, message):
        log_label = Label(
            text=message,
            size_hint_y=None,
            height='30dp',
            font_size='14sp',
            text_size=(self.width, None),
            halign='left'
        )
        
        self.ids.log_container.add_widget(log_label)
        
        # 自动滚动到底部
        from kivy.animation import Animation
        anim = Animation(scroll_y=0, duration=0.1)
        anim.start(self.ids.log_container)

class PDFAssistantApp(App):
    def build(self):
        self.title = 'PDF阅读助手'
        return MainView()

if __name__ == '__main__':
    from kivy.config import Config
    Config.set('graphics', 'width', '480')
    Config.set('graphics', 'height', '800')
    PDFAssistantApp().run() 