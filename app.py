from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont, ExifTags
import io
import base64
import requests
from datetime import datetime
import re
import os
import traceback
import uuid
import threading
import time

app = Flask(__name__)

# メモリ内画像ストレージ
temp_images = {}

def cleanup_old_images():
    """古い画像を定期的に削除"""
    while True:
        try:
            current_time = time.time()
            expired_keys = [
                key for key, data in temp_images.items()
                if current_time - data.get('created', 0) > 3600  # 1時間で削除
            ]
            for key in expired_keys:
                del temp_images[key]
            time.sleep(300)  # 5分ごとに実行
        except Exception as e:
            print(f"クリーンアップエラー: {e}")
            time.sleep(300)

# クリーンアップスレッド開始
cleanup_thread = threading.Thread(target=cleanup_old_images, daemon=True)
cleanup_thread.start()

class LicenseImageGenerator:
    def __init__(self):
        # 画像設定
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
        
    def create_license_image(self, license_data, original_image_url=None):
        """免許証画像生成"""
        try:
            print(f"画像生成開始 - Name: {license_data.get('name', 'N/A')}")
            
            # キャンバス作成
            canvas = Image.new('RGB', (self.canvas_width, self.canvas_height), self.bg_color)
            draw = ImageDraw.Draw(canvas)
            
            # 左側背景
            left_bg = Image.new('RGB', (self.left_width, self.canvas_height), self.left_bg_color)
            canvas.paste(left_bg, (0, 0))
            
            # 中央境界線
            draw.line([(self.left_width, 0), (self.left_width, self.canvas_height)], 
                     fill=self.border_color, width=4)
            
            # 左側にテキスト情報を配置
            self._draw_text_info(draw, license_data)
            
            # 右側に元画像を配置
            if original_image_url:
                self._place_image_from_url(canvas, original_image_url)
            else:
                self._draw_placeholder(draw)
            
            # 画像を出力
            img_buffer = io.BytesIO()
            canvas.save(img_buffer, format='PNG', quality=95)
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            print(f"画像生成エラー: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def _draw_text_info(self, draw, data):
        """左側テキスト描画"""
        try:
            # フォント設定
            try:
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                ]
                
                font_large = None
                font_medium = None
                font_small = None
                
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font_large = ImageFont.truetype(font_path, 48)
                        font_medium = ImageFont.truetype(font_path, 40)
                        font_small = ImageFont.truetype(font_path, 36)
                        break
                
                if not font_large:
                    font_large = font_medium = font_small = ImageFont.load_default()
                    
            except:
                font_large = font_medium = font_small = ImageFont.load_default()
            
            # データフィールド
            fields = [
                ('Name:', data.get('name', 'Not Available')),
                ('Date of Birth:', data.get('birthDate', data.get('dateOfBirth', 'Not Available'))),
                ('Address:', data.get('address', 'Not Available')),
                ('Issue Date:', data.get('issueDate', data.get('deliveryDate', 'Not Available'))),
                ('Expiration Date:', data.get('expirationDate', 'Not Available'))
            ]
            
            # レイアウト
            y_pos = 120
            line_spacing = 200
            
            for label, value in fields:
                # ラベル描画
                draw.text((80, y_pos), label, fill=self.text_primary, font=font_medium)
                
                # 値描画
                value_y = y_pos + 60
                
                # 住所の場合は改行処理
                if 'Address' in label and len(str(value)) > 45:
                    lines = self._wrap_text(str(value), 45)
                    for i, line in enumerate(lines[:2]):
                        draw.text((80, value_y + i * 45), line, fill=self.text_secondary, font=font_small)
                else:
                    draw.text((80, value_y), str(value), fill=self.text_secondary, font=font_small)
                
                y_pos += line_spacing
                
        except Exception as e:
            print(f"テキスト描画エラー: {e}")
    
    def _place_image_from_url(self, canvas, image_url):
        """URL経由での画像配置（iPhone縦向き対応）"""
        try:
            # Google Drive URL処理
            if 'drive.google.com' in image_url:
                file_id_match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', image_url)
                if file_id_match:
                    file_id = file_id_match.group(1)
                    image_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            print(f"画像URL: {image_url}")
            
            # 画像ダウンロード
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(image_url, timeout=30, headers=headers)
            response.raise_for_status()
            
            # 画像を開く
            img = Image.open(io.BytesIO(response.content))
            
            # EXIF情報から回転を検出して修正
            try:
                exif = img._getexif()
                if exif:
                    for tag, value in exif.items():
                        if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                            print(f"EXIF Orientation: {value}")
                            
                            if value == 3:
                                img = img.rotate(180, expand=True)
                            elif value == 6:
                                img = img.rotate(270, expand=True)
                            elif value == 8:
                                img = img.rotate(90, expand=True)
                            
                            print("画像の向きを修正しました")
                            break
            except:
                pass
            
            # RGB変換
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 画像配置
            self._place_image_on_canvas(canvas, img)
            
        except Exception as e:
            print(f"画像配置エラー: {str(e)}")
            self._draw_error_message(canvas, "Image Load Error")
    
    def _place_image_on_canvas(self, canvas, img):
        """画像をキャンバスに配置"""
        try:
            # 配置エリア計算
            padding = 60
            available_width = self.right_width - (padding * 2)
            available_height = self.canvas_height - (padding * 2)
            
            # リサイズ計算
            img_width, img_height = img.size
            scale_w = available_width / img_width
            scale_h = available_height / img_height
            scale = min(scale_w, scale_h, 1.5)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # リサイズ
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央配置
            x = self.left_width + (self.right_width - new_width) // 2
            y = (self.canvas_height - new_height) // 2
            
            # 貼り付け
            canvas.paste(resized, (x, y))
            
            # 枠線
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([x-2, y-2, x+new_width+2, y+new_height+2], 
                          outline='#CCCCCC', width=3)
            
            print(f"画像配置完了: {new_width}x{new_height}")
            
        except Exception as e:
            print(f"配置エラー: {e}")
            raise
    
    def _draw_placeholder(self, draw):
        """プレースホルダー描画"""
        center_x = self.left_width + self.right_width // 2
        center_y = self.canvas_height // 2
        
        draw.rectangle(
            [self.left_width + 80, 80, self.canvas_width - 80, self.canvas_height - 80],
            outline='#DDDDDD', width=3
        )
        
        draw.text((center_x - 80, center_y), "No Image", fill='#999999')
    
    def _draw_error_message(self, canvas, message):
        """エラーメッセージ描画"""
        draw = ImageDraw.Draw(canvas)
        center_x = self.left_width + self.right_width // 2
        center_y = self.canvas_height // 2
        
        draw.rectangle(
            [self.left_width + 100, center_y - 30, 
             self.canvas_width - 100, center_y + 30],
            outline='#FF0000', width=2
        )
        
        draw.text((center_x - 50, center_y - 10), message, fill='#FF0000')
    
    def _wrap_text(self, text, max_chars):
        """テキスト折り返し"""
        if len(text) <= max_chars:
            return [text]
        
        words = text.split(' ')
        lines = []
        current_line = ''
        
        for word in words:
            if len(current_line + ' ' + word) <= max_chars:
                current_line = (current_line + ' ' + word).strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines

# ルートエンドポイント
@app.route('/')
def home():
    """ホームページ"""
    return jsonify({
        'service': 'License Image Generator',
        'version': '5.2',
        'status': 'running',
        'endpoints': {
            'generate': '/generate-license',
            'health': '/health',
            'preview': '/preview/<image_id>'
        }
    })

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '5.2'
    })

@app.route('/preview/<image_id>')
def preview_image(image_id):
    """画像プレビュー"""
    if image_id not in temp_images:
        return "Image not found or expired", 404
    
    image_data = temp_images[image_id]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>License Image Preview</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                font-family: Arial, sans-serif;
            }}
            .container {{
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                overflow: hidden;
                max-width: 95%;
                max-height: 95vh;
            }}
            img {{
                max-width: 100%;
                max-height: 90vh;
                width: auto;
                height: auto;
                display: block;
            }}
            .download-btn {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #007bff;
                color: white;
                padding: 12px 24px;
                border-radius: 25px;
                text-decoration: none;
                box-shadow: 0 4px 15px rgba(0,123,255,0.3);
                font-weight: bold;
                transition: transform 0.2s;
            }}
            .download-btn:hover {{
                transform: scale(1.05);
            }}
            .info {{
                position: fixed;
                top: 20px;
                right: 20px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="data:image/png;base64,{image_data['base64']}" alt="License Image" />
        </div>
        <div class="info">
            Generated: {image_data.get('created_at', 'N/A')}
        </div>
        <a href="data:image/png;base64,{image_data['base64']}" 
           download="license_image.png" 
           class="download-btn">
            📥 Download
        </a>
    </body>
    </html>
    """
    
    return html

@app.route('/generate-license', methods=['POST', 'OPTIONS'])
def generate_license():
    """画像生成エンドポイント"""
    
    # CORS対応
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return response
    
    try:
        # リクエストデータ取得
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        print(f"リクエスト受信: {datetime.now().isoformat()}")
        
        # データ整形
        if 'translatedData' in data:
            # n8nからのフォーマット
            td = data['translatedData']
            license_data = {
                'name': td.get('name', ''),
                'address': td.get('address', ''),
                'birthDate': td.get('birthDate', ''),
                'issueDate': td.get('issueDate', ''),
                'expirationDate': td.get('expirationDate', '')
            }
            image_url = data.get('originalImageUrl')
        else:
            # 直接フォーマット
            license_data = data
            image_url = data.get('originalImageUrl')
        
        # 画像生成
        generator = LicenseImageGenerator()
        image_bytes = generator.create_license_image(license_data, image_url)
        
        # Base64エンコード
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # プレビューURL生成
        image_id = str(uuid.uuid4())
        temp_images[image_id] = {
            'base64': image_b64,
            'created': time.time(),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        preview_url = f"https://license-image-generator-1.onrender.com/preview/{image_id}"
        
        print(f"処理完了 - 画像サイズ: {len(image_bytes)} bytes")
        print(f"プレビューURL: {preview_url}")
        
        # レスポンス
        response = jsonify({
            'success': True,
            'imageBase64': image_b64,
            'image_base64': image_b64,
            'previewUrl': preview_url,
            'message': 'Image generated successfully',
            'stats': {
                'size_bytes': len(image_bytes),
                'dimensions': '2400x1440',
                'format': 'PNG',
                'generated_at': datetime.now().isoformat()
            }
        })
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        print(traceback.format_exc())
        
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        
        error_response.headers['Access-Control-Allow-Origin'] = '*'
        return error_response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    print("=" * 60)
    print("License Image Generator v5.2 - With Preview")
    print("=" * 60)
    print(f"Port: {port}")
    print("Features:")
    print("- ✅ iPhone縦向き撮影の自動検出と修正")
    print("- ✅ プレビューURL生成")
    print("- ✅ ダウンロード機能")
    print(f"Starting at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
