import os
import csv
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.utils import platform
from PIL import Image, ImageDraw, ImageFont
import tempfile
import datetime

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from androidstorage4kivy import SharedStorage, Chooser
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

class ImageGeneratorApp(App):
    def build(self):
        self.title = '批量图片生成器'
        self.selected_color = 'red'
        self.pattern_path = None
        self.output_dir = None
        self.batch_mode = False

        # 主布局
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 模式切换
        mode_layout = BoxLayout(size_hint_y=0.1)
        self.mode_spinner = Spinner(text='单张模式', values=('单张模式', '批量模式'), size_hint=(0.5,1))
        self.mode_spinner.bind(text=self.on_mode_change)
        mode_layout.add_widget(Label(text='模式：'))
        mode_layout.add_widget(self.mode_spinner)
        layout.add_widget(mode_layout)

        # 单张模式界面
        self.single_layout = BoxLayout(orientation='vertical', size_hint_y=0.8)
        self.create_single_ui(self.single_layout)
        layout.add_widget(self.single_layout)

        # 批量模式界面（初始隐藏）
        self.batch_layout = BoxLayout(orientation='vertical', size_hint_y=0.8)
        self.create_batch_ui(self.batch_layout)
        self.batch_layout.opacity = 0
        self.batch_layout.disabled = True
        layout.add_widget(self.batch_layout)

        # 结果标签
        self.result_label = Label(text='', size_hint_y=0.1)
        layout.add_widget(self.result_label)

        return layout

    def create_single_ui(self, parent):
        # 背景颜色
        color_layout = BoxLayout(size_hint_y=0.15)
        color_layout.add_widget(Label(text='背景：'))
        self.color_spinner = Spinner(text='红色', values=('红色', '蓝色'), size_hint=(0.5,1))
        self.color_spinner.bind(text=self.on_color_change)
        color_layout.add_widget(self.color_spinner)
        parent.add_widget(color_layout)

        # 图案选择
        self.pattern_btn = Button(text='选择图案', size_hint_y=0.15)
        self.pattern_btn.bind(on_press=self.choose_pattern)
        parent.add_widget(self.pattern_btn)
        self.pattern_preview = KivyImage(size_hint_y=0.3, allow_stretch=True)
        parent.add_widget(self.pattern_preview)

        # 四角文本输入
        parent.add_widget(Label(text='左上角文本:', size_hint_y=0.05))
        self.text_tl = TextInput(text='', multiline=False, size_hint_y=0.1)
        parent.add_widget(self.text_tl)

        parent.add_widget(Label(text='右上角文本:', size_hint_y=0.05))
        self.text_tr = TextInput(text='', multiline=False, size_hint_y=0.1)
        parent.add_widget(self.text_tr)

        parent.add_widget(Label(text='左下角文本:', size_hint_y=0.05))
        self.text_bl = TextInput(text='', multiline=False, size_hint_y=0.1)
        parent.add_widget(self.text_bl)

        parent.add_widget(Label(text='右下角文本:', size_hint_y=0.05))
        self.text_br = TextInput(text='', multiline=False, size_hint_y=0.1)
        parent.add_widget(self.text_br)

        # 字体大小
        size_layout = BoxLayout(size_hint_y=0.1)
        size_layout.add_widget(Label(text='字体大小:'))
        self.font_size = TextInput(text='40', multiline=False, input_filter='int', size_hint=(0.3,1))
        size_layout.add_widget(self.font_size)
        parent.add_widget(size_layout)

        # 生成按钮
        self.gen_single_btn = Button(text='生成单张图片', size_hint_y=0.15)
        self.gen_single_btn.bind(on_press=self.generate_single)
        parent.add_widget(self.gen_single_btn)

    def create_batch_ui(self, parent):
        # 选择CSV文件
        self.csv_btn = Button(text='选择CSV表格文件', size_hint_y=0.15)
        self.csv_btn.bind(on_press=self.choose_csv)
        parent.add_widget(self.csv_btn)

        # CSV格式说明
        info = """
CSV格式要求：
第一行表头：左上,右上,左下,右下,图案,背景
图案列可用：trapezoid, diamond, 或图片路径
背景列：red 或 blue
示例：
左上,右上,左下,右下,图案,背景
A,B,C,d,diamond,red
E,F,G,H,/sdcard/logo.png,blue
        """
        self.info_label = Label(text=info, size_hint_y=0.3, halign='left', valign='top')
        parent.add_widget(self.info_label)

        # 批量生成按钮
        self.gen_batch_btn = Button(text='批量生成图片', size_hint_y=0.15)
        self.gen_batch_btn.bind(on_press=self.generate_batch)
        parent.add_widget(self.gen_batch_btn)

        # 进度显示
        self.progress_label = Label(text='', size_hint_y=0.1)
        parent.add_widget(self.progress_label)

    def on_mode_change(self, spinner, text):
        if text == '单张模式':
            self.single_layout.opacity = 1
            self.single_layout.disabled = False
            self.batch_layout.opacity = 0
            self.batch_layout.disabled = True
        else:
            self.single_layout.opacity = 0
            self.single_layout.disabled = True
            self.batch_layout.opacity = 1
            self.batch_layout.disabled = False

    def on_color_change(self, spinner, text):
        self.selected_color = 'red' if text == '红色' else 'blue'

    def choose_pattern(self, instance):
        if platform == 'android':
            Chooser(choice=self.pattern_chosen).choose_content()
        else:
            from kivy.uix.filechooser import FileChooserListView
            from kivy.uix.modalview import ModalView
            fc = FileChooserListView(path='/sdcard')
            view = ModalView(size_hint=(0.9,0.9))
            view.add_widget(fc)
            fc.bind(selection=lambda x, y: self.pattern_chosen(y[0]) if y else None)
            view.open()

    def pattern_chosen(self, path):
        self.pattern_path = path
        self.pattern_preview.source = path
        print('图案已选择')

    def choose_csv(self, instance):
        if platform == 'android':
            Chooser(choice=self.csv_chosen).choose_content()
        else:
            from kivy.uix.filechooser import FileChooserListView
            from kivy.uix.modalview import ModalView
            fc = FileChooserListView(path='/sdcard', filters=['*.csv'])
            view = ModalView(size_hint=(0.9,0.9))
            view.add_widget(fc)
            fc.bind(selection=lambda x, y: self.csv_chosen(y[0]) if y else None)
            view.open()

    def csv_chosen(self, path):
        self.csv_path = path
        self.csv_btn.text = f'已选: {os.path.basename(path)}'

    def generate_single(self, instance):
        # 获取四角文本
        texts = {
            'tl': self.text_tl.text,
            'tr': self.text_tr.text,
            'bl': self.text_bl.text,
            'br': self.text_br.text,
        }
        try:
            font_size = int(self.font_size.text)
        except:
            font_size = 40
        color = self.selected_color
        pattern = self.pattern_path

        # 调用核心生成函数
        try:
            img = self.create_image(texts, font_size, color, pattern)
            self.save_image(img)
            self.result_label.text = '单张图片生成成功！'
        except Exception as e:
            self.result_label.text = f'生成失败: {str(e)}'

    def generate_batch(self, instance):
        if not hasattr(self, 'csv_path') or not self.csv_path:
            self.progress_label.text = '请先选择CSV文件'
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                total = len(rows)
                if total == 0:
                    self.progress_label.text = 'CSV文件无数据'
                    return

                # 创建输出目录
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = tempfile.mkdtemp(prefix='batch_')
                success = 0

                for i, row in enumerate(rows):
                    # 提取数据
                    texts = {
                        'tl': row.get('左上', ''),
                        'tr': row.get('右上', ''),
                        'bl': row.get('左下', ''),
                        'br': row.get('右下', ''),
                    }
                    try:
                        font_size = int(row.get('字体大小', 40))
                    except:
                        font_size = 40
                    color = row.get('背景', 'red').strip().lower()
                    pattern_spec = row.get('图案', '').strip()

                    # 处理图案：如果是内置形状关键字，则不传入路径
                    if pattern_spec in ('trapezoid', 'diamond', 'none'):
                        pattern_path = None
                        shape = pattern_spec
                    else:
                        pattern_path = pattern_spec
                        shape = None

                    img = self.create_image(texts, font_size, color, pattern_path, shape)
                    out_path = os.path.join(output_dir, f'image_{i+1:03d}.png')
                    img.save(out_path, dpi=(300,300))
                    success += 1
                    self.progress_label.text = f'进度: {i+1}/{total}'

                # 批量生成完成后，提示用户保存到共享存储
                if platform == 'android':
                    from androidstorage4kivy import SharedStorage
                    shared = SharedStorage()
                    # 将整个目录复制到共享存储（可能需要逐文件处理）
                    for fname in os.listdir(output_dir):
                        src = os.path.join(output_dir, fname)
                        shared.copy_to_shared(src)
                    self.progress_label.text = f'成功生成{success}张图片，已保存到手机存储'
                else:
                    self.progress_label.text = f'成功生成{success}张图片，保存在{output_dir}'
        except Exception as e:
            self.progress_label.text = f'批量处理失败: {str(e)}'

    def create_image(self, texts, font_size, bg_color, pattern_path=None, shape=None):
        # 固定尺寸（可改为从设置获取）
        width_px, height_px = 1200, 1600  # 300DPI下约10x13cm
        dpi = 300

        # 背景颜色
        if bg_color == 'red':
            bg = (255,0,0,255)
        else:
            bg = (0,0,255,255)
        img = Image.new('RGBA', (width_px, height_px), bg)
        draw = ImageDraw.Draw(img)

        # 处理图案
        if pattern_path and os.path.exists(pattern_path):
            pattern = Image.open(pattern_path).convert('RGBA')
            max_w = int(width_px * 0.6)
            max_h = int(height_px * 0.6)
            pattern.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            paste_x = (width_px - pattern.width)//2
            paste_y = (height_px - pattern.height)//2
            img.paste(pattern, (paste_x, paste_y), pattern)
        elif shape and shape != 'none':
            # 绘制内置形状
            shape_color = (255,255,255,255)
            if shape == 'trapezoid':
                top_width = width_px * 0.4
                bottom_width = width_px * 0.6
                top_y = height_px * 0.3
                bottom_y = height_px * 0.7
                points = [
                    ((width_px - top_width)/2, top_y),
                    ((width_px + top_width)/2, top_y),
                    ((width_px + bottom_width)/2, bottom_y),
                    ((width_px - bottom_width)/2, bottom_y)
                ]
                draw.polygon(points, fill=shape_color)
            elif shape == 'diamond':
                cx, cy = width_px/2, height_px/2
                dx = width_px * 0.2
                dy = height_px * 0.2
                points = [
                    (cx, cy - dy*1.5),
                    (cx + dx, cy),
                    (cx, cy + dy*1.5),
                    (cx - dx, cy)
                ]
                draw.polygon(points, fill=shape_color)

        # 绘制四角文本
        try:
            font = ImageFont.truetype('/system/fonts/DroidSansFallback.ttf', font_size)
        except:
            font = ImageFont.load_default()

        margin = 40
        positions = [
            (texts['tl'], (margin, margin)),                     # 左上
            (texts['tr'], (width_px - margin, margin)),          # 右上
            (texts['bl'], (margin, height_px - margin)),         # 左下
            (texts['br'], (width_px - margin, height_px - margin)) # 右下
        ]
        for text, (x, y) in positions:
            if text:
                bbox = draw.textbbox((0,0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                # 根据角落调整实际绘制点
                if x == margin and y == margin:  # 左上
                    draw.text((x, y), text, fill=(255,255,255), font=font)
                elif x == width_px - margin and y == margin:  # 右上
                    draw.text((x - tw, y), text, fill=(255,255,255), font=font)
                elif x == margin and y == height_px - margin:  # 左下
                    draw.text((x, y - th), text, fill=(255,255,255), font=font)
                else:  # 右下
                    draw.text((x - tw, y - th), text, fill=(255,255,255), font=font)
        return img

    def save_image(self, img):
        # 保存到临时文件
        temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp.name)
        if platform == 'android':
            from androidstorage4kivy import SharedStorage
            SharedStorage().copy_to_shared(temp.name)
            self.result_label.text = '已保存到手机存储'
        else:
            self.result_label.text = f'临时保存: {temp.name}'

if __name__ == '__main__':
    ImageGeneratorApp().run()