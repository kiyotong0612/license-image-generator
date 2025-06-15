from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import base64
import requests
from datetime import datetime
import re
import os
import traceback

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
        
    def create_perfect_license_image(self, license_data, original_image_url=None, original_image_base64=None):
        """完璧な品質の免許証画像を生成（URL・Base64両方対応）"""
        
        try:
            print(f"画像生成開始 - Name: {license_data.get('name', 'N/A')}")
            print(f"URL提供: {bool(original_image_url)}, Base64提供: {bool(original_image_base64)}")
            
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
                print("URL経由で画像処理開始")
                self._place_right_side_image_from_url(canvas, original_image_url)
            elif original_image_base64:
                print("Base64経由で画像処理開始")
                self._place_right_side_image_from_base64(canvas, original_image_base64)
            else:
                print("画像なし - プレースホルダー表示")
                self._draw_placeholder_image(draw, font_title)
            
            # 最終的な品質向上
            canvas = self._enhance_image_quality(canvas)
            
            # 高品質PNG出力
            img_buffer = io.BytesIO()
            canvas.save(img_buffer, format='PNG', quality=100, optimize=True, dpi=(300, 300))
            img_buffer.seek(0)
            
            result_bytes = img_buffer.getvalue()
            print(f"画像生成完了 - サイズ: {len(result_bytes)} bytes")
            
            return result_bytes
            
        except Exception as e:
            print(f"画像生成エラー: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def _setup_fonts(self):
        """フォントの設定（多様な環境に対応）"""
        try:
            # システムフォントを試行（優先順位順）
            font_paths = [
                # macOS
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Arial.ttf",
                # Windows
                "/Windows/Fonts/arial.ttf",
                "/Windows/Fonts/Arial.ttf",
                "C:/Windows/Fonts/arial.ttf",
                # Linux
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/arial.ttf",
                # Docker/Container環境
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                # 相対パス
                "fonts/arial.ttf",
                "arial.ttf", 
                "Arial.ttf"
            ]
            
            for font_path in font_paths:
                try:
                    font_title = ImageFont.truetype(font_path, 48)
                    font_label = ImageFont.truetype(font_path, 40)
                    font_value = ImageFont.truetype(font_path, 36)
                    print(f"フォント読み込み成功: {font_path}")
                    return font_title, font_label, font_value
                except Exception as font_error:
                    continue
                    
        except Exception as e:
            print(f"フォント設定エラー: {e}")
        
        # デフォルトフォント（最終手段）
        print("デフォルトフォントを使用")
        try:
            font_default = ImageFont.load_default()
            return font_default, font_default, font_default
        except:
            return None, None, None
    
    def _draw_left_side_text(self, draw, data, font_title, font_label, font_value):
        """左側のテキスト配置（完全版）"""
        
        # レイアウト設定
        left_margin = 100
        top_start = 150
        line_spacing = 180
        
        # タイトル
        title = "JAPANESE DRIVER'S LICENSE"
        try:
            if font_title:
                title_bbox = draw.textbbox((0, 0), title, font=font_title)
                title_width = title_bbox[2] - title_bbox[0]
            else:
                title_width = len(title) * 20
        except:
            title_width = len(title) * 20
        
        title_x = max(50, (self.left_width - title_width) // 2)
        
        # タイトル描画
        if font_title:
            draw.text((title_x, 80), title, fill=self.text_primary, font=font_title)
        else:
            draw.text((title_x, 80), title, fill=self.text_primary)
        
        # タイトル下線
        draw.line([(title_x, 140), (title_x + title_width, 140)], 
                 fill=self.accent_color, width=5)
        
        # データフィールド整形
        fields = [
            ('Name:', self._safe_string(data.get('name', 'Not Available'))),
            ('Date of Birth:', self._safe_string(data.get('dateOfBirth', data.get('birthDate', 'Not Available')))),
            ('Address:', self._safe_string(data.get('address', 'Not Available'))),
            ('Issue Date:', self._safe_string(data.get('deliveryDate', data.get('issueDate', 'Not Available')))),
            ('Expiration Date:', self._safe_string(data.get('expirationDate', 'Not Available')))
        ]
        
        y_pos = top_start
        
        for label, value in fields:
            # ラベル描画
            if font_label:
                draw.text((left_margin, y_pos), label, fill=self.text_primary, font=font_label)
            else:
                draw.text((left_margin, y_pos), label, fill=self.text_primary)
            
            # 値描画
            value_y = y_pos + 50
            
            # 住所の特別処理（長文対応）
            if 'Address' in label and len(value) > 60:
                lines = self._smart_text_wrap(value, 55)
                for i, line in enumerate(lines[:3]):  # 最大3行
                    if font_value:
                        draw.text((left_margin, value_y + i * 40), line, 
                                 fill=self.text_secondary, font=font_value)
                    else:
                        draw.text((left_margin, value_y + i * 40), line, 
                                 fill=self.text_secondary)
            else:
                # 通常の値描画
                if font_value:
                    draw.text((left_margin, value_y), value, 
                             fill=self.text_secondary, font=font_value)
                else:
                    draw.text((left_margin, value_y), value, 
                             fill=self.text_secondary)
            
            y_pos += line_spacing
    
    def _place_right_side_image_from_url(self, canvas, image_url):
        """URL経由での右側画像配置"""
        try:
            # Google Drive URL の特別処理
            processed_url = self._process_google_drive_url(image_url)
            print(f"処理後URL: {processed_url}")
            
            # 画像ダウンロード
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            print("画像ダウンロード開始...")
            response = requests.get(processed_url, timeout=30, headers=headers, allow_redirects=True)
            response.raise_for_status()
            
            print(f"ダウンロード完了 - サイズ: {len(response.content)} bytes")
            
            # 画像として読み込み
            original_img = Image.open(io.BytesIO(response.content))
            print(f"画像読み込み完了 - サイズ: {original_img.size}, モード: {original_img.mode}")
            
            # RGB変換（必要に応じて）
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # 画像配置処理
            self._place_processed_image(canvas, original_img)
            
        except Exception as e:
            print(f"URL画像配置エラー: {str(e)}")
            print(traceback.format_exc())
            self._draw_error_placeholder(canvas, f"URL画像エラー: {str(e)[:50]}...")
    
    def _place_right_side_image_from_base64(self, canvas, image_base64):
        """Base64経由での右側画像配置"""
        try:
            print("Base64画像デコード開始...")
            
            # Base64デコード
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]  # data:image/jpeg;base64, 部分を除去
            
            image_data = base64.b64decode(image_base64)
            print(f"Base64デコード完了 - サイズ: {len(image_data)} bytes")
            
            # 画像として読み込み
            original_img = Image.open(io.BytesIO(image_data))
            print(f"画像読み込み完了 - サイズ: {original_img.size}, モード: {original_img.mode}")
            
            # RGB変換（必要に応じて）
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
            
            # 画像配置処理
            self._place_processed_image(canvas, original_img)
            
        except Exception as e:
            print(f"Base64画像配置エラー: {str(e)}")
            print(traceback.format_exc())
            self._draw_error_placeholder(canvas, f"Base64画像エラー: {str(e)[:50]}...")
    
    def _place_processed_image(self, canvas, original_img):
        """処理済み画像の配置（共通処理）"""
        try:
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
            
            print(f"リサイズ: {orig_width}x{orig_height} → {new_width}x{new_height}")
            
            # 高品質リサイズ
            resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央配置計算
            x_offset = right_start_x + (self.right_width - new_width) // 2
            y_offset = (self.canvas_height - new_height) // 2
            
            print(f"配置位置: ({x_offset}, {y_offset})")
            
            # 画像貼り付け
            canvas.paste(resized_img, (x_offset, y_offset))
            
            # 枠線描画
            draw = ImageDraw.Draw(canvas)
            border_width = 4
            draw.rectangle(
                [x_offset - border_width, y_offset - border_width,
                 x_offset + new_width + border_width - 1, 
                 y_offset + new_height + border_width - 1],
                outline='#CCCCCC', width=border_width
            )
            
            print("画像配置完了")
            
        except Exception as e:
            print(f"画像配置処理エラー: {str(e)}")
            raise
    
    def _process_google_drive_url(self, url):
        """Google Drive URLの処理"""
        try:
            print(f"Google Drive URL処理: {url}")
            
            if 'drive.google.com' not in url:
                return url
            
            # 既に直接ダウンロードURLの場合
            if 'export=download' in url:
                return url
            
            # webContentLink形式の場合
            if 'uc?id=' in url:
                return url
            
            # 共有URL形式の場合 (https://drive.google.com/file/d/FILE_ID/view)
            file_id_match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                print(f"URL変換: {direct_url}")
                return direct_url
            
            # その他のGoogle Drive URL
            id_match = re.search(r'id=([a-zA-Z0-9-_]+)', url)
            if id_match:
                file_id = id_match.group(1)
                direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                print(f"ID抽出URL変換: {direct_url}")
                return direct_url
            
            print("Google Drive URLの変換に失敗、元URLを使用")
            return url
            
        except Exception as e:
            print(f"Google Drive URL処理エラー: {e}")
            return url
    
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
            if font_title:
                text_bbox = draw.multiline_textbbox((0, 0), placeholder_text, font=font_title)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            else:
                text_width = 200
                text_height = 100
        except:
            text_width = 200
            text_height = 100
        
        text_x = right_center_x - text_width // 2
        text_y = right_center_y - text_height // 2
        
        if font_title:
            draw.multiline_text((text_x, text_y), placeholder_text, 
                               fill='#999999', font=font_title, align='center')
        else:
            draw.multiline_text((text_x, text_y), placeholder_text, 
                               fill='#999999', align='center')
    
    def _draw_error_placeholder(self, canvas, error_message):
        """エラー時の表示"""
        draw = ImageDraw.Draw(canvas)
        right_center_x = self.left_width + self.right_width // 2
        right_center_y = self.canvas_height // 2
        
        # エラー枠
        padding = 100
        error_coords = [
            self.left_width + padding, self.canvas_height // 2 - 100,
            self.canvas_width - padding, self.canvas_height // 2 + 100
        ]
        draw.rectangle(error_coords, outline='#FF6B6B', width=4, fill='#FFF5F5')
        
        # エラーテキスト
        error_text = "Image Loading Failed"
        draw.text((right_center_x - 150, right_center_y - 30), 
                 error_text, fill='#FF6B6B')
        
        # 詳細エラー
        if len(error_message) < 100:
            draw.text((right_center_x - 200, right_center_y + 10), 
                     error_message, fill='#999999')
    
    def _enhance_image_quality(self, img):
        """画像品質向上"""
        try:
            # シャープネス向上
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)
            
            # コントラスト調整
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            
            # 彩度調整
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.05)
            
            return img
        except Exception as e:
            print(f"画像品質向上エラー: {e}")
            return img
    
    def _smart_text_wrap(self, text, max_chars):
        """テキスト改行処理（スマート版）"""
        if len(text) <= max_chars:
            return [text]
        
        # 優先順位の区切り文字
        separators = [', ', '、', ' ', '-', '/', '\\', '_']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                lines = []
                current_line = ''
                
                for i, part in enumerate(parts):
                    test_line = current_line + (sep + part if current_line else part)
                    if len(test_line) <= max_chars:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = part
                
                if current_line:
                    lines.append(current_line)
                
                return lines[:3]  # 最大3行
        
        # 強制分割（最終手段）
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)][:3]
    
    def _safe_string(self, value):
        """文字列の安全な変換"""
        if value is None:
            return 'Not Available'
        
        try:
            return str(value).strip()
        except:
            return 'Not Available'

# Flask エンドポイント定義

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'version': '3.0',
        'service': 'Japanese License Image Generator',
        'features': ['URL_SUPPORT', 'BASE64_SUPPORT', 'GOOGLE_DRIVE_INTEGRATION']
    })

@app.route('/test-url', methods=['POST'])
def test_url():
    """URL処理テスト用エンドポイント"""
    try:
        data = request.json
        image_url = data.get('imageUrl') or data.get('originalImageUrl')
        
        if not image_url:
            return jsonify({'success': False, 'error': 'No imageUrl provided'}), 400
        
        # URL処理テスト
        generator = PerfectLicenseImageGenerator()
        processed_url = generator._process_google_drive_url(image_url)
        
        # 画像ダウンロードテスト
        headers = {'User-Agent': 'Mozilla/5.0 (compatible)'}
        response = requests.head(processed_url, timeout=10, headers=headers)
        
        result = {
            'success': True,
            'originalUrl': image_url,
            'processedUrl': processed_url,
            'accessible': response.status_code == 200,
            'contentType': response.headers.get('content-type', 'unknown'),
            'contentLength': response.headers.get('content-length', 'unknown')
        }
        
        result_response = jsonify(result)
        result_response.headers.add('Access-Control-Allow-Origin', '*')
        return result_response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/generate-license', methods=['POST', 'OPTIONS'])
def generate_license():
    """メインの免許証画像生成エンドポイント"""
    
    # CORS preflight 処理
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # リクエストデータ取得
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        print(f"リクエスト受信: {datetime.now().isoformat()}")
        print(f"データキー: {list(data.keys())}")
        
        # データ構造の判定と正規化
        if 'translatedData' in data:
            # N8N形式
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
            # 直接形式
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
        print(f"URL: {bool(original_image_url)}, Base64: {bool(original_image_base64)}")
        
        # 画像生成処理
        generator = PerfectLicenseImageGenerator()
        image_bytes = generator.create_perfect_license_image(
            license_data, 
            original_image_url=original_image_url,
            original_image_base64=original_image_base64
        )
        
        # Base64エンコード
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"処理完了 - 画像サイズ: {len(image_bytes)} bytes")
        
        # レスポンス生成
        response_data = {
            'success': True,
            'imageBase64': image_b64,  # N8N用
            'image_base64': image_b64,  # 互換性用
            'message': 'Perfect license image generated successfully',
            'stats': {
                'size_bytes': len(image_bytes),
                'dimensions': '2400x1440',
                'dpi': 300,
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
            'timestamp': datetime.now().isoformat(),
            'service': 'Japanese License Image Generator'
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        error_response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        
        return error_response, 500

# アプリケーション起動設定
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("Japanese License Image Generator v3.0")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Debug: {debug_mode}")
    print(f"Features: URL Support, Base64 Support, Google Drive Integration")
    print(f"Starting at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
