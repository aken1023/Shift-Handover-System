from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
from datetime import datetime
import logging
import traceback
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import NotFound, HTTPException
from collections import deque
import speech_recognition as sr
import tempfile
from pydub import AudioSegment
import json
from dotenv import load_dotenv
import openai
import subprocess

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 嘗試載入 .env 檔案
load_dotenv(override=True)

def get_openai_key():
    """獲取 OpenAI API 金鑰"""
    # 直接從環境變數獲取
    api_key = os.getenv('OPENAI_API_KEY')
    
    if api_key:
        logger.info("成功從環境變數獲取 API 金鑰")
        # 檢查金鑰格式
        if api_key.startswith('sk-'):
            return api_key
        else:
            logger.error("API 金鑰格式不正確")
    else:
        logger.error("無法從環境變數獲取 API 金鑰")
        # 列出所有可用的環境變數名稱（不包含值）
        logger.info("可用的環境變數：" + ", ".join(k for k in os.environ.keys()))
    
    raise ValueError("未設定 OPENAI_API_KEY 環境變數或格式不正確")

# 設定 OpenAI API 金鑰
import openai
try:
    openai.api_key = get_openai_key()
    logger.info("OpenAI API 金鑰設定完成")
except Exception as e:
    logger.error(f"設定 API 金鑰時發生錯誤: {str(e)}")
    raise

# 建立一個環形緩衝區來存儲最近的錯誤日誌
error_logs = deque(maxlen=100)  # 保存最近100條日誌

class ErrorLogHandler(logging.Handler):
    def emit(self, record):
        error_logs.append({
            'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage(),
            'traceback': record.exc_text if record.exc_text else None
        })

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(),
        ErrorLogHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 設定代理伺服器支援
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 確保上傳目錄存在
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允許的音訊檔案格式
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'webm', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_webm_to_wav(webm_path):
    """將 WebM 音訊檔案轉換為 WAV 格式"""
    try:
        audio = AudioSegment.from_file(webm_path, format="webm")
        wav_path = webm_path.replace(".webm", ".wav")
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        logger.error(f"音訊轉換錯誤: {str(e)}")
        raise

def speech_to_text(audio_path):
    """將音訊檔案轉換為文字"""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        
        # 使用 Google 語音辨識（中文）
        text = recognizer.recognize_google(audio, language='zh-TW')
        return text
    except sr.UnknownValueError:
        logger.error("無法辨識語音內容")
        return "無法辨識語音內容，請重新錄音。"
    except sr.RequestError as e:
        logger.error(f"語音辨識服務錯誤: {str(e)}")
        return "語音辨識服務暫時無法使用，請稍後再試。"
    except Exception as e:
        logger.error(f"語音轉文字過程發生錯誤: {str(e)}")
        raise

def log_error(error_type, message, traceback_info=None):
    """統一的錯誤日誌記錄函數"""
    error_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': error_type,
        'message': message,
        'traceback': traceback_info
    }
    logger.error(f"{error_type}: {message}")
    if traceback_info:
        logger.error(f"Traceback: {traceback_info}")
    return error_data

@app.route('/err')
def error_log():
    """顯示錯誤日誌頁面"""
    return render_template('error_log.html', logs=list(error_logs))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"NotFound: 找不到請求的頁面或資源")
    logger.error(f"Traceback: {traceback.format_exc()}")
    logger.error(f"404錯誤: {request.url}")
    return redirect(url_for('error_log'))

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"InternalServerError: 伺服器內部錯誤")
    logger.error(f"Traceback: {traceback.format_exc()}")
    logger.error(f"500錯誤: {request.url}")
    return redirect(url_for('error_log'))

@app.before_request
def log_request_info():
    logger.info(f"收到請求: {request.method} {request.url}")
    logger.info(f"請求頭: {dict(request.headers)}")

@app.errorhandler(Exception)
def handle_error(error):
    """全局錯誤處理"""
    if isinstance(error, HTTPException):
        error_type = error.__class__.__name__
        error_message = error.description
    else:
        error_type = error.__class__.__name__
        error_message = str(error)
    
    error_traceback = traceback.format_exc() if app.debug else None
    
    log_error(error_type, error_message, error_traceback)
    logger.error(f"發生錯誤: {error_type} - {error_message}\n{error_traceback if error_traceback else ''}")
    
    if request.is_json:
        return jsonify({
            'error': f"{error_type}",
            'message': error_message
        }), 500
    return redirect(url_for('error_log'))

@app.route('/')
def index():
    return render_template('index.html')

def transcribe_audio(file_path):
    """使用 OpenAI Whisper API 進行語音轉文字"""
    try:
        with open(file_path, 'rb') as audio_file:
            response = openai.Audio.transcribe(
                "whisper-1",
                audio_file,
                language="zh"
            )
        return response['text']
    except Exception as e:
        logger.error(f"語音轉文字失敗: {str(e)}")
        raise Exception(f"語音轉文字失敗: {str(e)}")

def generate_report(text):
    """使用 GPT-3.5 生成結構化報告"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一個專業的護理師，負責整理和格式化交班內容。"},
                {"role": "user", "content": f"請將以下交班內容整理成格式化的照護報告：\n{text}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message['content']
    except Exception as e:
        logger.error(f"生成報告失敗: {str(e)}")
        raise Exception(f"生成報告失敗: {str(e)}")

def save_transcription_log(log_data, audio_file_path):
    """保存轉錄記錄和語音檔案"""
    try:
        timestamp = log_data['timestamp']
        
        # 建立主要儲存目錄
        base_folder = os.path.join(os.getcwd(), 'records')
        os.makedirs(base_folder, exist_ok=True)
        
        # 建立以日期為名的子目錄
        date_folder = os.path.join(base_folder, timestamp[:8])  # YYYYMMDD
        os.makedirs(date_folder, exist_ok=True)
        
        # 建立此次記錄的目錄
        record_folder = os.path.join(date_folder, timestamp[9:])  # HHMMSS
        os.makedirs(record_folder, exist_ok=True)
        
        # 保存音訊檔案
        audio_extension = os.path.splitext(audio_file_path)[1]
        new_audio_path = os.path.join(record_folder, f'audio{audio_extension}')
        import shutil
        shutil.copy2(audio_file_path, new_audio_path)
        logger.info(f"音訊檔案已保存: {new_audio_path}")
        
        # 保存原始文字
        raw_text_path = os.path.join(record_folder, 'raw_text.txt')
        with open(raw_text_path, 'w', encoding='utf-8') as f:
            f.write(log_data['raw_transcription'])
        logger.info(f"原始文字已保存: {raw_text_path}")
        
        # 保存整理後的報告
        report_path = os.path.join(record_folder, 'report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(log_data['formatted_report'])
        logger.info(f"整理後報告已保存: {report_path}")
        
        # 保存完整記錄
        log_path = os.path.join(record_folder, 'record.json')
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        logger.info(f"完整記錄已保存: {log_path}")
        
        return {
            'audio_file': new_audio_path,
            'raw_text': raw_text_path,
            'report': report_path,
            'record': log_path
        }
            
    except Exception as e:
        logger.error(f"記錄保存失敗: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.route('/care-record/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("開始處理上傳請求")
        
        if 'audio' not in request.files:
            logger.error("沒有收到音訊檔案")
            return jsonify({'error': '沒有收到音訊檔案'}), 400
            
        file = request.files['audio']
        if file.filename == '':
            logger.error("沒有選擇檔案")
            return jsonify({'error': '沒有選擇檔案'}), 400

        if not allowed_file(file.filename):
            logger.error(f"不支援的檔案格式: {file.filename}")
            return jsonify({'error': f'不支援的檔案格式。允許的格式: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        try:
            # 建立上傳目錄
            upload_folder = os.path.join(os.getcwd(), 'uploads', 'audio')
            os.makedirs(upload_folder, exist_ok=True)
            
            # 生成檔案名稱
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_extension = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"audio_{timestamp}.{original_extension}")
            filepath = os.path.join(upload_folder, filename)
            
            # 保存檔案
            logger.info(f"準備保存檔案到: {filepath}")
            file.save(filepath)
            logger.info(f"檔案保存成功: {filepath}")
            
            # 檢查檔案
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"檔案保存失敗: {filepath}")
            
            # 轉換音訊
            raw_text = transcribe_audio(filepath)
            logger.info("音訊轉換完成")
            
            # 使用 ChatGPT 處理
            logger.info("開始使用 ChatGPT 處理文字")
            formatted_report = generate_report(raw_text)
            logger.info("AI 內容整理完成")

            # 保存所有資料
            log_data = {
                'timestamp': timestamp,
                'audio_file': filepath,
                'raw_transcription': raw_text,
                'formatted_report': formatted_report,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            saved_paths = save_transcription_log(log_data, filepath)
            logger.info("所有記錄保存完成")
            
            return jsonify({
                'success': True,
                'raw_text': raw_text,
                'report': formatted_report,
                'saved_paths': saved_paths
            })
            
        except Exception as e:
            logger.error(f"處理失敗: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'處理失敗: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"系統錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'系統錯誤: {str(e)}'}), 500

@app.route('/care-record/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        
        # 創建郵件內容
        email_content = f"""
照護交接報告
時間：{datetime.now().strftime("%Y/%m/%d %H:%M")}

交接人：{data['handoverFrom']}

=== 照護報告 ===
{data['report']}
"""
        
        # 這裡之後會實現實際的郵件發送邏輯
        
        return jsonify({'success': True, 'message': '郵件發送成功'})
        
    except Exception as e:
        log_error('EmailError', f"發送郵件時發生錯誤: {str(e)}", traceback.format_exc())
        return jsonify({'error': f"發送郵件時發生錯誤: {str(e)}"}), 500

@app.route('/check-ffmpeg')
def check_ffmpeg_endpoint():
    """檢查 FFmpeg 狀態的端點"""
    try:
        # 檢查 ffmpeg 路徑
        ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
        
        # 檢查版本
        version = subprocess.check_output(['ffmpeg', '-version']).decode()
        
        return jsonify({
            'status': 'ok',
            'ffmpeg_path': ffmpeg_path,
            'version': version.split('\n')[0]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# 設定 Flask 環境
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 