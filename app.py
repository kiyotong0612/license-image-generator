from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import base64
import requests
from datetime import datetime
import re
import os

app = Flask(__name__)

class PerfectLicenseImageGenerator:
    def __init__(self):
        # 超高解像度設定
        self.canvas_width = 2400
        self.canvas_height = 1440
        self.left_width = 1200
        self.right_width = 1200
        
        # 色設定
        self.bg_color = '#FFFFFF'
        self.left_bg_color = '#F8F9FA'
        self.text_primary = '#1A1A1A'
        self.text_secondary = '#333333'
        self.border_color = '#E0E0E0'
        self.accent_color = '#2196F3'
        
    def create_perfect_license_image(self, license_data, original_image_url=None):
        """完璧な品質の免許証画像を生成"""
        
        # 高解像度キャンバス作成
        canvas = Image.new('RGB', (self.canvas_width, self.canvas_height), self.bg_color)
        draw = ImageDraw.Draw(canvas)
        
        # 左側背景
        left_bg = Image.new('RGB', (self.left_width, self.canvas_height), self.left_bg_color)
        canvas.paste(left_bg, (0, 0))
        
        # 中央境界線
        draw.line([(self.left_width, 0), (self.left_width, self.canvas_height)], 
                 fill=self.border_color, width=4)
        
        # フォント設定
        font_title, font_label, font_value = self._setup_fonts()
        
        # 左側にテキスト情報を配置
        self._draw_left_side_text(draw, license_data, font_title, font_label, font_value)
        
        # 右側に元画像を配置
        if original_image_url:
            self._place_right_side_image(canvas, original_image_url)
        else:
            self._draw_placeholder_image(draw, font_title)
        
        # 最終的な品質向上
        canvas = self._enhance_image_quality(canvas)
        
        # 高品質PNG出力
        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format='PNG', quality=100, optimize=True, dpi=(300, 300))
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def _setup_fonts(self):
        """フォントの設定"""
        try:
            # システムフォントを試行
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/Windows/Fonts/arial.ttf",              # Windows
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "arial.ttf", "Arial.ttf"                 # 汎用
            ]
            
            for font_path in font_paths:
                try:
                    font_title = ImageFont.truetype(font_path, 48)
                    font_label = ImageFont.truetype(font_path, 40)
                    font_value = ImageFont.truetype(font_path, 36)
                    return font_title, font_label, font_value
                except:
                    continue
        except:
            pass
        
        # デフォルトフォント
        font_default = ImageFont.load_default()
        return font_default, font_default, font_default
    
    def _draw_left_side_text(self, draw, data, font_title, font_label, font_value):
        """左側のテキスト配置"""
        
        # レイアウト設定
        left_margin = 100
        top_start = 150
        line_spacing = 180
        
        # タイトル
        title = "JAPANESE DRIVER'S LICENSE"
        try:
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
        except:
            title_width = len(title) * 20  # フォールバック
        
        title_x = (self.left_width - title_width) // 2
        
        draw.text((title_x, 80), title, fill=self.text_primary, font=font_title)
        
        # タイトル下線
        draw.line([(title_x, 140), (title_x + title_width, 140)], 
                 fill=self.accent_color, width=5)
        
        # データフィールド
        fields = [
            ('Name:', str(data.get('name', 'Not Available'))),
            ('Date of Birth:', str(data.get('dateOfBirth', 'Not Available'))),
            ('Address:', str(data.get('address', 'Not Available'))),
            ('Delivery Date:', str(data.get('deliveryDate', 'Not Available'))),
            ('Expiration Date:', str(data.get('expirationDate', 'Not Available')))
        ]
        
        y_pos = top_start
        
        for label, value in fields:
            # ラベル
            draw.text((left_margin, y_pos), label, fill=self.text_primary, font=font_label)
            
            # 値
            value_y = y_pos + 50
            
            # 住所の特別処理
            if 'Address' in label and len(value) > 60:
                lines = self._smart_text_wrap(value, 55)
                for i, line in enumerate(lines[:3]):
                    draw.text((left_margin, value_y + i * 40), line, 
                             fill=self.text_secondary, font=font_value)
            else:
                draw.text((left_margin, value_y), value, 
                         fill=self.text_secondary, font=font_value)
            
            y_pos += line_spacing
    
    def _place_right_side_image(self, canvas, image_url):
        """右側画像配置"""
        try:
            # 画像ダウンロード
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            original_img = Image.open(io.BytesIO(response.content))
            
            # 画像品質向上
            original_img = self._enhance_image_quality(original_img)
            
            # 配置計算
            right_start_x = self.left_width
            padding = 80
            available_width = self.right_width - (padding * 2)
            available_height = self.canvas_height - (padding * 2)
            
            # アスペクト比保持リサイズ
            orig_width, orig_height = original_img.size
            aspect_ratio = orig_width / orig_height
            
            if available_width / available_height > aspect_ratio:
                new_height = available_height
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = available_width
                new_height = int(new_width / aspect_ratio)
            
            # 高品質リサイズ
            resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央配置
            x_offset = right_start_x + (self.right_width - new_width) // 2
            y_offset = (self.canvas_height - new_height) // 2
            
            # 画像貼り付け
            canvas.paste(resized_img, (x_offset, y_offset))
            
            # 枠線
            draw = ImageDraw.Draw(canvas)
            border_width = 4
            draw.rectangle(
                [x_offset - border_width, y_offset - border_width,
                 x_offset + new_width + border_width - 1, 
                 y_offset + new_height + border_width - 1],
                outline='#CCCCCC', width=border_width
            )
            
        except Exception as e:
            print(f"画像配置エラー: {e}")
            self._draw_error_placeholder(canvas)
    
    def _draw_placeholder_image(self, draw, font_title):
        """プレースホルダー画像"""
        right_center_x = self.left_width + self.right_width // 2
        right_center_y = self.canvas_height // 2
        
        # 枠線
        padding = 120
        frame_coords = [
            self.left_width + padding, padding,
            self.canvas_width - padding, self.canvas_height - padding
        ]
        draw.rectangle(frame_coords, outline='#DDDDDD', width=6)
        
        # テキスト
        placeholder_text = "Original License\nImage Area"
        try:
            text_bbox = draw.multiline_textbbox((0, 0), placeholder_text, font=font_title)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except:
            text_width = 200
            text_height = 100
        
        text_x = right_center_x - text_width // 2
        text_y = right_center_y - text_height // 2
        
        draw.multiline_text((text_x, text_y), placeholder_text, 
                           fill='#999999', font=font_title, align='center')
    
    def _enhance_image_quality(self, img):
        """画像品質向上"""
        try:
            # シャープネス
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)
            
            # コントラスト
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            
            return img
        except:
            return img
    
    def _smart_text_wrap(self, text, max_chars):
        """テキスト改行処理"""
        if len(text) <= max_chars:
            return [text]
        
        separators = [', ', '、', ' ', '-', '/']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                lines = []
                current_line = ''
                
                for part in parts:
                    test_line = current_line + (sep + part if current_line else part)
                    if len(test_line) <= max_chars:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = part
                
                if current_line:
                    lines.append(current_line)
                
                return lines[:3]
        
        # 強制分割
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)][:3]
    
    def _draw_error_placeholder(self, canvas):
        """エラー時の表示"""
        draw = ImageDraw.Draw(canvas)
        right_center_x = self.left_width + self.right_width // 2
        right_center_y = self.canvas_height // 2
        
        error_text = "Image Loading Failed"
        draw.text((right_center_x - 150, right_center_y), 
                 error_text, fill='#FF6B6B')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    })

@app.route('/generate-license', methods=['POST', 'OPTIONS'])
def generate_license():
    # CORS処理
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        print(f"画像生成開始: {data.get('name', 'Unknown')}")
        
        # 画像生成
        generator = PerfectLicenseImageGenerator()
        image_bytes = generator.create_perfect_license_image(
            data, 
            data.get('originalImageUrl')
        )
        
        # Base64エンコード
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"画像生成完了: サイズ={len(image_bytes)} bytes")
        
        response = jsonify({
            'success': True,
            'image_base64': image_b64,
            'message': 'Perfect license image generated',
            'stats': {
                'size_bytes': len(image_bytes),
                'dimensions': '2400x1440',
                'dpi': 300,
                'format': 'PNG'
            }
        })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        error_response = jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"License Image Generator starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
