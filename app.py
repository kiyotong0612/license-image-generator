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
        # 高解像度設定
        self.canvas_width = 2000
        self.canvas_height = 1200
        self.left_width = 1000
        self.right_width = 1000
        
        # 色設定
        self.bg_color = '#FFFFFF'
        self.left_bg_color = '#F8F9FA'
        self.text_primary = '#1A1A1A'
        self.text_secondary = '#333333'
        self.border_color = '#E0E0E0'
        
    def create_perfect_license_image(self, license_data, original_image_url=None):
        """PDFサンプルと同品質の画像を生成"""
        
        # 高解像度キャンバス作成
        canvas = Image.new('RGB', (self.canvas_width, self.canvas_height), self.bg_color)
        draw = ImageDraw.Draw(canvas)
        
        # 左側背景
        left_bg = Image.new('RGB', (self.left_width, self.canvas_height), self.left_bg_color)
        canvas.paste(left_bg, (0, 0))
        
        # 中央境界線
        draw.line([(self.left_width, 0), (self.left_width, self.canvas_height)], 
                 fill=self.border_color, width=3)
        
        # フォント設定（サイズを大きく）
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            font_value = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except:
            try:
                font_title = ImageFont.truetype("arial.ttf", 36)
                font_label = ImageFont.truetype("arial.ttf", 32)
                font_value = ImageFont.truetype("arial.ttf", 28)
            except:
                font_title = ImageFont.load_default()
                font_label = ImageFont.load_default()
                font_value = ImageFont.load_default()
        
        # 左側にテキスト情報を配置
        self._draw_left_side_text(draw, license_data, font_title, font_label, font_value)
        
        # 右側に元画像を配置
        if original_image_url:
            self._place_right_side_image(canvas, original_image_url)
        else:
            self._draw_placeholder_image(draw, font_title)
        
        # 最終的な品質向上
        canvas = self._enhance_image_quality(canvas)
        
        # 画像をバイトデータに変換
        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format='PNG', quality=100, optimize=True, dpi=(300, 300))
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def _draw_left_side_text(self, draw, data, font_title, font_label, font_value):
        """左側のテキスト情報を完璧に配置"""
        
        # マージン設定
        left_margin = 80
        top_margin = 120
        line_spacing = 160
        
        # タイトル
        title = "LICENSE INFORMATION"
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.left_width - title_width) // 2
        
        draw.text((title_x, 50), title, fill=self.text_primary, font=font_title)
        
        # タイトル下線
        line_y = 95
        line_start = title_x
        line_end = title_x + title_width
        draw.line([(line_start, line_y), (line_end, line_y)], fill='#2196F3', width=4)
        
        # データフィールド
        fields = [
            ('Name:', data.get('name', 'Not Available')),
            ('Date of Birth:', data.get('dateOfBirth', 'Not Available')),
            ('Address:', data.get('address', 'Not Available')),
            ('Delivery Date:', data.get('deliveryDate', 'Not Available')),
            ('Expiration Date:', data.get('expirationDate', 'Not Available'))
        ]
        
        y_pos = top_margin
        
        for label, value in fields:
            # ラベル（太字風）
            draw.text((left_margin, y_pos), label, fill=self.text_primary, font=font_label)
            
            # 値の配置
            value_y = y_pos + 45
            value_text = str(value)
            
            # 住所の場合は特別処理（複数行）
            if 'Address' in label and len(value_text) > 50:
                lines = self._smart_text_wrap(value_text, 45)
                for i, line in enumerate(lines[:3]):  # 最大3行
                    draw.text((left_margin, value_y + i * 35), line, 
                             fill=self.text_secondary, font=font_value)
            else:
                draw.text((left_margin, value_y), value_text, 
                         fill=self.text_secondary, font=font_value)
            
            y_pos += line_spacing
    
    def _place_right_side_image(self, canvas, image_url):
        """右側に元画像を完璧に配置"""
        try:
            # 画像をダウンロード
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            original_img = Image.open(io.BytesIO(response.content))
            
            # 画像の品質向上
            original_img = self._enhance_image_quality(original_img)
            
            # 右側エリア設定
            right_start_x = self.left_width
            padding = 60
            available_width = self.right_width - (padding * 2)
            available_height = self.canvas_height - (padding * 2)
            
            # アスペクト比を完全保持
            orig_width, orig_height = original_img.size
            aspect_ratio = orig_width / orig_height
            
            # リサイズ計算
            if available_width / available_height > aspect_ratio:
                # 高さベース
                new_height = available_height
                new_width = int(new_height * aspect_ratio)
            else:
                # 幅ベース
                new_width = available_width
                new_height = int(new_width / aspect_ratio)
            
            # 高品質リサイズ
            resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央配置計算
            x_offset = right_start_x + (self.right_width - new_width) // 2
            y_offset = (self.canvas_height - new_height) // 2
            
            # 画像貼り付け
            canvas.paste(resized_img, (x_offset, y_offset))
            
            # 画像周囲に高品質な枠線
            draw = ImageDraw.Draw(canvas)
            border_width = 3
            draw.rectangle(
                [x_offset - border_width, y_offset - border_width,
                 x_offset + new_width + border_width - 1, y_offset + new_height + border_width - 1],
                outline='#CCCCCC', width=border_width
            )
            
            # 影効果（オプション）
            shadow_offset = 5
            draw.rectangle(
                [x_offset + shadow_offset, y_offset + shadow_offset,
                 x_offset + new_width + shadow_offset, y_offset + new_height + shadow_offset],
                outline='#E0E0E0', width=1
            )
            
        except Exception as e:
            print(f"画像配置エラー: {e}")
            self._draw_error_placeholder(canvas)
    
    def _draw_placeholder_image(self, draw, font_title):
        """画像がない場合のプレースホルダー"""
        right_center_x = self.left_width + self.right_width // 2
        right_center_y = self.canvas_height // 2
        
        # 枠線
        padding = 100
        frame_coords = [
            self.left_width + padding, padding,
            self.canvas_width - padding, self.canvas_height - padding
        ]
        draw.rectangle(frame_coords, outline='#DDDDDD', width=4)
        
        # プレースホルダーテキスト
        placeholder_text = "Original License\nImage Area"
        text_bbox = draw.multiline_textbbox((0, 0), placeholder_text, font=font_title)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = right_center_x - text_width // 2
        text_y = right_center_y - text_height // 2
        
        draw.multiline_text((text_x, text_y), placeholder_text, 
                           fill='#999999', font=font_title, align='center')
    
    def _enhance_image_quality(self, img):
        """画像品質の向上"""
        # シャープネス向上
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        # コントラスト向上
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        
        return img
    
    def _smart_text_wrap(self, text, max_chars):
        """スマートなテキスト改行"""
        if len(text) <= max_chars:
            return [text]
        
        # 区切り文字で優先的に分割
        separators = [', ', '、', ' ', '-']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                lines = []
                current_line = ''
                
                for part in parts:
                    if len(current_line + sep + part) <= max_chars:
                        current_line += (sep + part if current_line else part)
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = part
                
                if current_line:
                    lines.append(current_line)
                
                return lines[:3]  # 最大3行
        
        # 強制分割
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)][:3]
    
    def _draw_error_placeholder(self, canvas):
        """エラー時のプレースホルダー"""
        draw = ImageDraw.Draw(canvas)
        right_center_x = self.left_width + self.right_width // 2
        right_center_y = self.canvas_height // 2
        
        error_text = "Image Loading\nFailed"
        draw.multiline_text((right_center_x - 100, right_center_y - 30), 
                           error_text, fill='#FF6B6B', align='center')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/generate-license', methods=['POST', 'OPTIONS'])
def generate_license():
    # CORS対応
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # 完璧な画像生成
        generator = PerfectLicenseImageGenerator()
        image_bytes = generator.create_perfect_license_image(
            data, 
            data.get('originalImageUrl')
        )
        
        # Base64エンコード
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        response = jsonify({
            'success': True,
            'image_base64': image_b64,
            'message': 'Perfect license image generated successfully',
            'quality': 'ultra-high',
            'dimensions': '2000x1200',
            'dpi': 300
        })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
