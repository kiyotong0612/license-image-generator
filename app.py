from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
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
            canvas.save(img_buffer, format='PNG', quality=95, optimize=True)
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
        """左側テキスト描画（タイトルなし）"""
        
        font_large, font_medium, font_small = fonts
        
        # データフィールド
        fields = [
            ('Name:', self._safe_str(data.get('name', 'Not Available'))),
            ('Date of Birth:', self._safe_str(data.get('dateOfBirth', data.get('birthDate', 'Not Available')))),
            ('Address:', self._safe_str(data.get('address', 'Not Available'))),
            ('Issue Date:', self._safe_str(data.get('deliveryDate', data.get('issueDate', 'Not Available')))),
            ('Expiration Date:', self._safe_str(data.get('expirationDate', 'Not Available')))
        ]
        
        # レイアウト調整
        y_pos = 120
        line_spacing = 200
        
        for label, value in fields:
            # ラベル
            if font_medium:
                draw.text((80, y_pos), label, fill=self.text_primary, font=font_medium)
            else:
                draw.text((80, y_pos), label, fill=self.text_primary)
            
            # 値（住所の場合は改行処理）
            value_y = y_pos + 60
            if 'Address' in label and len(value) > 45:
                lines = self._wrap_text(value, 45)
                for i, line in enumerate(lines[:2]):
                    if font_small:
                        draw.text((80, value_y + i * 45), line, fill=self.text_secondary, font=font_small)
                    else:
                        draw.text((80, value_y + i * 45), line, fill=self.text_secondary)
            else:
                if font_small:
                    draw.text((80, value_y), value, fill=self.text_secondary, font=font_small)
                else:
                    draw.text((80, value_y), value, fill=self.text_secondary)
            
            y_pos += line_spacing
    
    def _place_image_from_url(self, canvas, image_url):
        """URL経由での画像配置（縦向き維持）"""
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
            
            # 画像を開く（シンプルに）
            image_bytes = io.BytesIO(response.content)
            original_img = Image.open(image_bytes)
            
            # EXIF情報を取得して元の向きを確認
            exif = original_img._getexif() if hasattr(original_img, '_getexif') else None
            orientation = None
            
            if exif:
                for tag, value in exif.items():
                    if tag == 274:  # Orientation tag
                        orientation = value
                        print(f"EXIF Orientation: {orientation}")
                        break
            
            # 画像のサイズ情報
            width, height = original_img.size
            print(f"元画像サイズ: {width}x{height}")
            print(f"画像の向き: {'縦向き' if height > width else '横向き'}")
            
            # EXIF Orientation 6または8の場合、画像は実際には縦向き
            if orientation in [6, 8]:
                print("📱 iPhoneの縦向き撮影を検出")
                # 画像を90度回転して正しい向きに
                if orientation == 6:
                    original_img = original_img.rotate(-90, expand=True)
                elif orientation == 8:
                    original_img = original_img.rotate(90, expand=True)
                print(f"回転後サイズ: {original_img.size}")
            
            # RGB変換
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # 配置
            self._place_image_on_canvas(canvas, original_img)
            
        except Exception as e:
            print(f"URL画像配置エラー: {str(e)}")
            print(traceback.format_exc())
            self._draw_error_message(canvas, f"画像読み込みエラー: {str(e)[:50]}")
    
    def _place_image_from_base64(self, canvas, image_base64):
        """Base64経由での画像配置"""
        try:
            print("Base64画像処理開始")
            
            # Base64デコード
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            
            image_data = base64.b64decode(image_base64)
            original_img = Image.open(io.BytesIO(image_data))
            
            # RGB変換
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # 配置
            self._place_image_on_canvas(canvas, original_img)
            
        except Exception as e:
            print(f"Base64画像配置エラー: {str(e)}")
            self._draw_error_message(canvas, f"Base64エラー: {str(e)[:50]}")
    
    def _place_image_on_canvas(self, canvas, original_img):
        """画像をキャンバスに配置（共通処理）"""
        try:
            # 配置エリア
            right_start_x = self.left_width
            padding = 60
            available_width = self.right_width - (padding * 2)
            available_height = self.canvas_height - (padding * 2)
            
            # 元画像のサイズ
            orig_width, orig_height = original_img.size
            
            # アスペクト比を保持してリサイズ
            scale_w = available_width / orig_width
            scale_h = available_height / orig_height
            scale = min(scale_w, scale_h)
            
            # スケールを制限（画像が大きくなりすぎないように）
            if scale > 1.5:
                scale = 1.5
            
            final_width = int(orig_width * scale)
            final_height = int(orig_height * scale)
            
            print(f"最終サイズ: {final_width}x{final_height}")
            
            # 高品質リサイズ
            resized_img = original_img.resize((final_width, final_height), Image.Resampling.LANCZOS)
            
            # 中央配置
            x_offset = right_start_x + (self.right_width - final_width) // 2
            y_offset = (self.canvas_height - final_height) // 2
            
            # 画像貼り付け
            canvas.paste(resized_img, (x_offset, y_offset))
            
            # 枠線
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                [x_offset - 2, y_offset - 2, x_offset + final_width + 2, y_offset + final_height + 2],
                outline='#CCCCCC', width=3
            )
            
            print("✅ 画像配置完了")
            
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
    
    def _draw_placeholder(self, draw, font):
        """プレースホルダー"""
        center_x = self.left_width + self.right_width // 2
        center_y = self.canvas_height // 2
        
        draw.rectangle(
            [self.left_width + 80, 80, self.canvas_width - 80, self.canvas_height - 80],
            outline='#DDDDDD', width=4
        )
        
        text = "License Image\nWill Appear Here"
        if font:
            draw.multiline_text((center_x - 120, center_y - 30), text, 
                               fill='#999999', font=font, align='center')
        else:
            draw.multiline_text((center_x - 120, center_y - 30), text, 
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
        
        draw.text((center_x - 150, center_y - 10), message, fill='#FF6B6B')
    
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
        'version': '5.0',
        'service': 'License Image Generator - Fixed Orientation',
        'features': ['URL_SUPPORT', 'BASE64_SUPPORT', 'IPHONE_ORIENTATION_FIX', 'VERTICAL_PRESERVED']
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
                max-height: 95vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            img {{
                max-width: 100%;
                max-height: 90vh;
                width: auto;
                height: auto;
                display: block;
            }}
            .info {{
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="data:image/png;base64,{image_data['base64']}" alt="License" />
        </div>
        <div class="info">
            Generated: {image_data.get('created_at', 'N/A')}
        </div>
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
        print(f"リクエストデータ: {data}")
        
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
    print("License Image Generator v5.0 - iPhone Orientation Fixed")
    print("=" * 60)
    print(f"Port: {port}")
    print("Features:")
    print("- ✅ iPhone縦向き撮影の自動検出と修正")
    print("- ✅ EXIF Orientationタグの適切な処理")
    print("- ✅ メモリ効率の最適化（502エラー対策）")
    print("- ✅ 縦向き免許証を正しく表示")
    print(f"Starting at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
