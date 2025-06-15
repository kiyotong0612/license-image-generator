from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
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

# メモリ内画像ストレージ（一時的）
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
try:
    cleanup_thread = threading.Thread(target=cleanup_old_images, daemon=True)
    cleanup_thread.start()
    print("クリーンアップスレッド開始")
except Exception as e:
    print(f"クリーンアップスレッド開始エラー: {e}")

class StableLicenseImageGenerator:
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
        self.accent_color = '#2196F3'
        
    def create_license_image(self, license_data, original_image_url=None, original_image_base64=None):
        """安定した免許証画像生成"""
        
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
            
            # フォント設定
            fonts = self._setup_fonts()
            
            # 左側にテキスト情報を配置
            self._draw_text_info(draw, license_data, fonts)
            
            # 右側に元画像を配置
            if original_image_url:
                self._place_image_from_url(canvas, original_image_url)
            elif original_image_base64:
                self._place_image_from_base64(canvas, original_image_base64)
            else:
                self._draw_placeholder(draw, fonts[0])
            
            # 画像を高品質で出力
            img_buffer = io.BytesIO()
            canvas.save(img_buffer, format='PNG', quality=100, optimize=True)
            img_buffer.seek(0)
            
            result_bytes = img_buffer.getvalue()
            print(f"画像生成完了 - サイズ: {len(result_bytes)} bytes")
            
            return result_bytes
            
        except Exception as e:
            print(f"画像生成エラー: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def _setup_fonts(self):
        """フォントの安全な設定"""
        try:
            # よく使われるフォントパス
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Windows/Fonts/arial.ttf"
            ]
            
            for font_path in font_paths:
                try:
                    font_large = ImageFont.truetype(font_path, 48)
                    font_medium = ImageFont.truetype(font_path, 40)
                    font_small = ImageFont.truetype(font_path, 36)
                    print(f"フォント使用: {font_path}")
                    return [font_large, font_medium, font_small]
                except:
                    continue
                    
        except Exception as e:
            print(f"フォント設定エラー: {e}")
        
        # デフォルトフォント
        try:
            default_font = ImageFont.load_default()
            return [default_font, default_font, default_font]
        except:
            return [None, None, None]
    
    def _draw_text_info(self, draw, data, fonts):
        """左側テキスト描画"""
        
        font_large, font_medium, font_small = fonts
        
        # タイトル
        title = "JAPANESE DRIVER'S LICENSE"
        title_x = 100
        title_y = 80
        
        if font_large:
            draw.text((title_x, title_y), title, fill=self.text_primary, font=font_large)
        else:
            draw.text((title_x, title_y), title, fill=self.text_primary)
        
        # タイトル下線
        draw.line([(title_x, title_y + 60), (title_x + 800, title_y + 60)], 
                 fill=self.accent_color, width=5)
        
        # データフィールド
        fields = [
            ('Name:', self._safe_str(data.get('name', 'Not Available'))),
            ('Date of Birth:', self._safe_str(data.get('dateOfBirth', data.get('birthDate', 'Not Available')))),
            ('Address:', self._safe_str(data.get('address', 'Not Available'))),
            ('Issue Date:', self._safe_str(data.get('deliveryDate', data.get('issueDate', 'Not Available')))),
            ('Expiration Date:', self._safe_str(data.get('expirationDate', 'Not Available')))
        ]
        
        y_pos = 200
        line_spacing = 180
        
        for label, value in fields:
            # ラベル
            if font_medium:
                draw.text((100, y_pos), label, fill=self.text_primary, font=font_medium)
            else:
                draw.text((100, y_pos), label, fill=self.text_primary)
            
            # 値（住所の場合は改行処理）
            value_y = y_pos + 50
            if 'Address' in label and len(value) > 60:
                lines = self._wrap_text(value, 55)
                for i, line in enumerate(lines[:3]):
                    if font_small:
                        draw.text((100, value_y + i * 40), line, fill=self.text_secondary, font=font_small)
                    else:
                        draw.text((100, value_y + i * 40), line, fill=self.text_secondary)
            else:
                if font_small:
                    draw.text((100, value_y), value, fill=self.text_secondary, font=font_small)
                else:
                    draw.text((100, value_y), value, fill=self.text_secondary)
            
            y_pos += line_spacing
    
    def _place_image_from_url(self, canvas, image_url):
        """URL経由での画像配置（向き保持）"""
        try:
            # Google Drive URL処理
            processed_url = self._process_google_drive_url(image_url)
            print(f"画像URL: {processed_url}")
            
            # 画像ダウンロード
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(processed_url, timeout=30, headers=headers, stream=True)
            response.raise_for_status()
            
            # 画像読み込み
            original_img = Image.open(io.BytesIO(response.content))
            print(f"元画像サイズ: {original_img.size}")
            
            # RGB変換
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # **重要：元の向きを保持**
            self._place_image_keep_orientation(canvas, original_img)
            
        except Exception as e:
            print(f"URL画像配置エラー: {str(e)}")
            self._draw_error_message(canvas, f"画像読み込みエラー: {str(e)[:50]}")
    
    def _place_image_from_base64(self, canvas, image_base64):
        """Base64経由での画像配置（向き保持）"""
        try:
            print("Base64画像処理開始")
            
            # Base64デコード
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            
            image_data = base64.b64decode(image_base64)
            original_img = Image.open(io.BytesIO(image_data))
            print(f"元画像サイズ: {original_img.size}")
            
            # RGB変換
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # **重要：元の向きを保持**
            self._place_image_keep_orientation(canvas, original_img)
            
        except Exception as e:
            print(f"Base64画像配置エラー: {str(e)}")
            self._draw_error_message(canvas, f"Base64エラー: {str(e)[:50]}")
    
    def _place_image_keep_orientation(self, canvas, original_img):
        """画像を元の向きのまま配置"""
        try:
            # 品質向上
            original_img = self._enhance_image(original_img)
            
            # 配置エリア
            right_start_x = self.left_width
            padding = 80
            available_width = self.right_width - (padding * 2)
            available_height = self.canvas_height - (padding * 2)
            
            # **元のサイズ比率を保持してリサイズ**
            orig_width, orig_height = original_img.size
            
            # フィット計算
            scale_w = available_width / orig_width
            scale_h = available_height / orig_height
            scale = min(scale_w, scale_h)
            
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            
            print(f"リサイズ: {orig_width}x{orig_height} → {new_width}x{new_height}")
            print("✅ 元の向きを保持")
            
            # 高品質リサイズ
            resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央配置
            x_offset = right_start_x + (self.right_width - new_width) // 2
            y_offset = (self.canvas_height - new_height) // 2
            
            # 画像貼り付け
            canvas.paste(resized_img, (x_offset, y_offset))
            
            # 枠線
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                [x_offset - 2, y_offset - 2, x_offset + new_width + 2, y_offset + new_height + 2],
                outline='#CCCCCC', width=3
            )
            
            print("画像配置完了")
            
        except Exception as e:
            print(f"画像配置エラー: {str(e)}")
            raise
    
    def _process_google_drive_url(self, url):
        """Google Drive URL処理"""
        try:
            if 'drive.google.com' not in url:
                return url
            
            if 'export=download' in url or 'uc?id=' in url:
                return url
            
            # 共有URL → 直接ダウンロードURL
            file_id_match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            
            return url
            
        except Exception as e:
            print(f"URL処理エラー: {e}")
            return url
    
    def _enhance_image(self, img):
        """画像品質向上"""
        try:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.05)
            
            return img
        except:
            return img
    
    def _draw_placeholder(self, draw, font):
        """プレースホルダー"""
        center_x = self.left_width + self.right_width // 2
        center_y = self.canvas_height // 2
        
        # 枠
        draw.rectangle(
            [self.left_width + 100, 100, self.canvas_width - 100, self.canvas_height - 100],
            outline='#DDDDDD', width=4
        )
        
        # テキスト
        text = "Original License\nImage Area"
        if font:
            draw.multiline_text((center_x - 150, center_y - 50), text, 
                               fill='#999999', font=font, align='center')
        else:
            draw.multiline_text((center_x - 150, center_y - 50), text, 
                               fill='#999999', align='center')
    
    def _draw_error_message(self, canvas, message):
        """エラー表示"""
        draw = ImageDraw.Draw(canvas)
        center_x = self.left_width + self.right_width // 2
        center_y = self.canvas_height // 2
        
        draw.rectangle(
            [self.left_width + 50, center_y - 50, self.canvas_width - 50, center_y + 50],
            outline='#FF6B6B', width=3, fill='#FFF5F5'
        )
        
        draw.text((center_x - 100, center_y - 10), "Image Loading Failed", fill='#FF6B6B')
    
    def _wrap_text(self, text, max_chars):
        """テキスト改行"""
        if len(text) <= max_chars:
            return [text]
        
        for sep in [', ', '、', ' ', '-']:
            if sep in text:
                parts = text.split(sep)
                lines = []
                current = ''
                
                for part in parts:
                    test = current + (sep + part if current else part)
                    if len(test) <= max_chars:
                        current = test
                    else:
                        if current:
                            lines.append(current)
                        current = part
                
                if current:
                    lines.append(current)
                
                return lines[:3]
        
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)][:3]
    
    def _safe_str(self, value):
        """安全な文字列変換"""
        try:
            return str(value).strip() if value else 'Not Available'
        except:
            return 'Not Available'

# Flask エンドポイント

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '4.0',
        'service': 'Stable License Image Generator',
        'features': ['URL_SUPPORT', 'BASE64_SUPPORT', 'ORIENTATION_PRESERVED', 'IMAGE_PREVIEW']
    })

@app.route('/preview/<image_id>')
def preview_image(image_id):
    """シンプル画像プレビュー"""
    if image_id not in temp_images:
        return "Image not found or expired", 404
    
    image_data = temp_images[image_id]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>License Image</title>
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
            }}
            .container {{
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                overflow: hidden;
                max-width: 95%;
                max-height: 95%;
            }}
            img {{
                width: 100%;
                height: auto;
                display: block;
            }}
            .btn {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #007bff;
                color: white;
                padding: 12px 24px;
                border-radius: 25px;
                text-decoration: none;
                box-shadow: 0 4px 15px rgba(0,123,255,0.3);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="data:image/png;base64,{image_data['base64']}" alt="License" />
        </div>
        <a href="data:image/png;base64,{image_data['base64']}" download="license.png" class="btn">
            📥 Download
        </a>
    </body>
    </html>
    """
    
    return html

@app.route('/generate-license', methods=['POST', 'OPTIONS'])
def generate_license():
    """メイン画像生成エンドポイント"""
    
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
        
        print(f"リクエスト受信: {datetime.now().isoformat()}")
        
        # データ正規化
        if 'translatedData' in data:
            translated_data = data.get('translatedData', {})
            license_data = {
                'name': translated_data.get('name', 'Not Available'),
                'address': translated_data.get('address', 'Not Available'),
                'dateOfBirth': translated_data.get('birthDate', 'Not Available'),
                'deliveryDate': translated_data.get('issueDate', 'Not Available'),
                'expirationDate': translated_data.get('expirationDate', 'Not Available')
            }
            original_image_url = data.get('originalImageUrl')
            original_image_base64 = data.get('originalImage')
        else:
            license_data = {
                'name': data.get('name', 'Not Available'),
                'address': data.get('address', 'Not Available'),
                'dateOfBirth': data.get('dateOfBirth', data.get('birthDate', 'Not Available')),
                'deliveryDate': data.get('deliveryDate', data.get('issueDate', 'Not Available')),
                'expirationDate': data.get('expirationDate', 'Not Available')
            }
            original_image_url = data.get('originalImageUrl')
            original_image_base64 = data.get('originalImage')
        
        print(f"処理開始 - Name: {license_data.get('name')}")
        
        # 画像生成
        generator = StableLicenseImageGenerator()
        image_bytes = generator.create_license_image(
            license_data,
            original_image_url=original_image_url,
            original_image_base64=original_image_base64
        )
        
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
        
        # レスポンス
        response_data = {
            'success': True,
            'imageBase64': image_b64,
            'image_base64': image_b64,
            'previewUrl': preview_url,
            'message': 'License image generated successfully',
            'stats': {
                'size_bytes': len(image_bytes),
                'dimensions': '2400x1440',
                'format': 'PNG',
                'generated_at': datetime.now().isoformat()
            }
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        
        return response
        
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        print(traceback.format_exc())
        
        error_response = jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        
        return error_response, 500

# アプリケーション起動
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("Stable License Image Generator v4.0")
    print("=" * 60)
    print(f"Port: {port}")
    print("Features: Stable Operation, Orientation Preserved, Image Preview")
    print(f"Starting at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
