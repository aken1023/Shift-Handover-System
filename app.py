#shift-handover-system-production.up.railway.app
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, Blueprint
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
from openai import OpenAI
import time
import openai
import shutil

# 載入 .env 檔案
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

def check_api_key():
    """檢查 API 金鑰設定"""
    api_key = os.getenv('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    
    logger.info("=== API 金鑰檢查 ===")
    logger.info(f"API 金鑰是否存在: {'是' if api_key else '否'}")
    
    if api_key:
        masked_key = api_key[:4] + '*' * (len(api_key) - 4)
        logger.info(f"API 金鑰格式: {masked_key}")
    
    return api_key

def get_openai_client():
    """初始化 OpenAI 客戶端"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API 金鑰未設定")
        raise Exception("OpenAI API 金鑰未設定")
    return OpenAI(api_key=api_key)

def transcribe_audio(file_path):
    """使用 OpenAI Whisper 進行語音轉文字"""
    try:
        logger.info(f"開始處理音訊檔案: {file_path}")
        
        # 取得 OpenAI 客戶端
        client = get_openai_client()
        
        start_time = time.time()
        logger.info("開始呼叫 OpenAI Whisper API")
        
        with open(file_path, 'rb') as audio:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language="zh"
            )
            
            logger.info("API 呼叫成功")
            logger.info(f"回應類型: {type(response)}")
            
            # 新版 API 回應格式
            if hasattr(response, 'text'):
                return response.text
            else:
                logger.error(f"未預期的回應格式: {response}")
                raise Exception("API 回應格式錯誤")
                
    except Exception as e:
        logger.error(f"轉錄過程發生錯誤: {str(e)}", exc_info=True)
        raise

app = Flask(__name__)

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

# 設定代理伺服器支援
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 設定上傳資料夾
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 設定允許的檔案類型
ALLOWED_EXTENSIONS = {'m4a', 'mp4', 'webm'}  # 增加 webm 格式支援

# 設定上傳檔案大小限制
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    """檢查檔案類型是否允許"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def convert_to_mp4(input_path):
    """將音訊檔案轉換為 MP4 格式"""
    try:
        audio = AudioSegment.from_file(input_path)
        mp4_path = input_path.rsplit('.', 1)[0] + '.mp4'
        audio.export(mp4_path, format='mp4')
        return mp4_path
    except Exception as e:
        logger.error(f"音訊轉換錯誤: {str(e)}")
        raise

def speech_to_text(audio_path):
    try:
        client = get_openai_client()
        
        # 轉換音訊格式為 mp3（Whisper API 支援的格式）
        audio = AudioSegment.from_file(audio_path)
        mp3_path = audio_path.replace('.webm', '.mp3')
        audio.export(mp3_path, format='mp3')
        
        # 使用 Whisper API 進行語音辨識
        with open(mp3_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh",
                response_format="text",
                temperature=0.2,  # 降低隨機性
                prompt="這是一份護理交接班的口述內容，內容不可以無中生有"  # 添加上下文提示
            )
            
        # 清理暫存檔案
        try:
            os.remove(mp3_path)
        except:
            pass
            
        print(f"語音轉文字結果: {transcript}")
        return transcript
        
    except Exception as e:
        print(f"語音轉文字錯誤: {str(e)}")
        return None

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
    return '', 204  # 返回無內容

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
    """首頁路由"""
    return render_template('index.html')

@app.route('/test-multi-segment')
def test_multi_segment():
    """多段語音輸入測試頁面"""
    return render_template('test_multi_segment.html')

def generate_care_report(text):
    try:
        if not isinstance(text, str):
            text = str(text)
        
        print("開始生成報告，輸入文本:", text)

        client = get_openai_client()

        messages = [
            {
                "role": "system", 
                "content": "你是一個專業的護理人員，擅長整理護理交接班紀錄。"
            },
            {
                "role": "user",
                "content": f"""
                如果口述內容:{text}與醫療照護無關，請委婉拒絕回覆，請勿生成任何內容。
                請根據以下口述內容:{text}，整理成一份完整的護理交接班紀錄，請務必嚴謸依據口述內容回答，不得無中生有，確保數據準確，避免產生不真實或無意義的資訊。

                格式要求：
                請依照以下固定格式撰寫交接班紀錄。若下列問題在口述內容中未提及，請標註「資料不足」，而非自行補充或推測。

                護理交接班紀錄格式：

                1.病患主要診斷與生命徵象
                2.重要管路與傷口評估
                3.特殊藥物使用與治療
                4.護理重點與異常狀況
                5.後續照護計畫與注意事項
          
                
                """
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            max_tokens=2100
        )
        
        report = response.choices[0].message.content
        print("成功生成報告:", report)
        return report

    except Exception as e:
        print(f"生成報告錯誤: {str(e)}")
        return f"無法生成報告：{str(e)}"

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

care_record = Blueprint('care_record', __name__, url_prefix='/care-record')

@care_record.route('/upload', methods=['POST'])
def upload():
    try:
        logger.info("=== 開始處理上傳請求 ===")
        
        if 'audio' not in request.files:
            logger.error("請求中沒有音訊檔案")
            return jsonify({'error': '沒有收到音訊檔案'}), 400
        
        audio_file = request.files['audio']
        logger.info(f"收到檔案: {audio_file.filename}")
        
        if audio_file.filename == '':
            logger.error("檔案名稱為空")
            return jsonify({'error': '沒有選擇檔案'}), 400
            
        # 建立上傳目錄
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # 使用時間戳生成唯一檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = secure_filename(f"{timestamp}_{audio_file.filename}")
        original_path = os.path.join(upload_folder, filename)
        
        # 確保檔案完全寫入並關閉
        audio_file.save(original_path)
        audio_file.close()
        logger.info("原始檔案儲存成功")
        
        try:
            # 轉換為 MP4 格式並保存
            mp4_filename = f"{timestamp}_converted_recording.mp4"  # 修改輸出檔名
            mp4_path = os.path.join(upload_folder, mp4_filename)
            
            # 使用 subprocess 直接調用 ffmpeg 進行轉換
            import subprocess
            try:
                subprocess.run([
                    'ffmpeg', '-i', original_path,
                    '-acodec', 'aac',
                    '-y',  # 覆蓋已存在的檔案
                    mp4_path
                ], check=True, capture_output=True)
                logger.info(f"檔案已轉換為 MP4 格式: {mp4_path}")
                
                # 轉換完成後刪除原始檔案
                if os.path.exists(original_path):
                    os.remove(original_path)
                    logger.info(f"原始檔案已刪除: {original_path}")
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg 轉換錯誤: {e.stderr.decode()}")
                raise
            
            # 等待檔案操作完成
            time.sleep(0.5)
            
            # 轉換音訊為文字
            text = transcribe_audio(mp4_path)
            logger.info(f"音訊轉換完成: {text}")
            
            # 生成照護報告
            report = generate_care_report(text)
            logger.info("照護報告生成完成")
            
            # 保存記錄
            log_data = {
                'timestamp': timestamp,
                'raw_transcription': text,
                'formatted_report': report
            }
            
            save_paths = save_transcription_log(log_data, mp4_path)
            
            return jsonify({
                'success': True,
                'text': text,
                'report': report,
                'timestamp': timestamp,
                'paths': save_paths
            })
            
        except Exception as e:
            logger.error(f"處理失敗: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'處理失敗: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"處理失敗: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'處理失敗: {str(e)}'
        }), 500

@care_record.route('/upload-multi', methods=['POST'])
def upload_multi():
    """處理多段語音上傳"""
    try:
        logger.info("=== 開始處理多段語音上傳請求 ===")
        
        # 獲取所有音訊段落
        audio_segments = request.files.getlist('audio_segments')
        segment_count = request.form.get('segment_count', 0)
        
        logger.info(f"收到 {len(audio_segments)} 段音訊")
        
        if not audio_segments:
            logger.error("請求中沒有音訊檔案")
            return jsonify({'error': '沒有收到音訊檔案'}), 400
            
        # 建立上傳目錄
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # 使用時間戳生成唯一資料夾
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(upload_folder, f"multi_segment_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)
        
        all_transcriptions = []
        segment_paths = []
        
        try:
            # 處理每個音訊段落
            for i, audio_file in enumerate(audio_segments):
                logger.info(f"處理第 {i+1} 段音訊: {audio_file.filename}")
                
                # 儲存原始檔案
                filename = secure_filename(f"segment_{i+1}_{audio_file.filename}")
                original_path = os.path.join(session_folder, filename)
                audio_file.save(original_path)
                
                # 轉換為 MP4 格式
                mp4_filename = f"segment_{i+1}_converted.mp4"
                mp4_path = os.path.join(session_folder, mp4_filename)
                
                import subprocess
                try:
                    subprocess.run([
                        'ffmpeg', '-i', original_path,
                        '-acodec', 'aac',
                        '-y',
                        mp4_path
                    ], check=True, capture_output=True)
                    logger.info(f"段落 {i+1} 已轉換為 MP4 格式")
                    
                    # 刪除原始檔案
                    if os.path.exists(original_path):
                        os.remove(original_path)
                        
                except subprocess.CalledProcessError as e:
                    logger.error(f"FFmpeg 轉換錯誤: {e.stderr.decode()}")
                    raise
                
                # 轉錄音訊
                segment_text = transcribe_audio(mp4_path)
                logger.info(f"段落 {i+1} 轉錄完成: {segment_text[:50]}...")
                
                all_transcriptions.append(f"[段落 {i+1}] {segment_text}")
                segment_paths.append(mp4_path)
            
            # 合併所有轉錄文字
            combined_text = "\n\n".join(all_transcriptions)
            logger.info(f"所有段落轉錄完成，總長度: {len(combined_text)} 字元")
            
            # 生成照護報告
            report = generate_care_report(combined_text)
            logger.info("照護報告生成完成")
            
            # 保存多段記錄
            log_data = {
                'timestamp': timestamp,
                'segment_count': len(audio_segments),
                'raw_transcriptions': all_transcriptions,
                'combined_transcription': combined_text,
                'formatted_report': report
            }
            
            # 保存到記錄目錄
            base_folder = os.path.join(os.getcwd(), 'records')
            os.makedirs(base_folder, exist_ok=True)
            
            date_folder = os.path.join(base_folder, timestamp[:8])
            os.makedirs(date_folder, exist_ok=True)
            
            record_folder = os.path.join(date_folder, f"multi_{timestamp[9:]}")
            os.makedirs(record_folder, exist_ok=True)
            
            # 複製所有音訊段落
            import shutil
            for i, segment_path in enumerate(segment_paths):
                new_path = os.path.join(record_folder, f'segment_{i+1}.mp4')
                shutil.copy2(segment_path, new_path)
            
            # 保存合併的轉錄文字
            combined_text_path = os.path.join(record_folder, 'combined_text.txt')
            with open(combined_text_path, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            
            # 保存各段落的轉錄文字
            segments_text_path = os.path.join(record_folder, 'segments_text.json')
            with open(segments_text_path, 'w', encoding='utf-8') as f:
                json.dump(all_transcriptions, f, ensure_ascii=False, indent=2)
            
            # 保存報告
            report_path = os.path.join(record_folder, 'report.md')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # 保存完整記錄
            log_path = os.path.join(record_folder, 'record.json')
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'text': combined_text,
                'report': report,
                'timestamp': timestamp,
                'segment_count': len(audio_segments),
                'segments': all_transcriptions
            })
            
        except Exception as e:
            logger.error(f"多段處理失敗: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'處理失敗: {str(e)}'
            }), 500
            
        finally:
            # 清理暫存目錄
            try:
                if os.path.exists(session_folder):
                    shutil.rmtree(session_folder)
                    logger.info("暫存目錄已清理")
            except:
                pass
                
    except Exception as e:
        logger.error(f"多段上傳失敗: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'處理失敗: {str(e)}'
        }), 500

# 在主應用程式中註冊藍圖
app.register_blueprint(care_record)

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

@app.route('/api/upload', methods=['POST'])
def upload_audio():
    try:
        logger.info("=== 開始處理上傳請求 ===")
        logger.info(f"請求內容類型: {request.content_type}")
        logger.info(f"請求檔案數量: {len(request.files)}")
        
        if 'audio' not in request.files:
            logger.error("請求中沒有音訊檔案")
            return jsonify({'error': '沒有收到音訊檔案'}), 400
        
        audio_file = request.files['audio']
        logger.info(f"收到檔案: {audio_file.filename}")
        
        if audio_file.filename == '':
            logger.error("檔案名稱為空")
            return jsonify({'error': '沒有選擇檔案'}), 400
            
        # 建立上傳目錄
        upload_folder = os.path.join(app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"上傳目錄: {upload_folder}")
        
        # 儲存檔案
        filename = secure_filename(audio_file.filename)
        file_path = os.path.join(upload_folder, filename)
        logger.info(f"儲存檔案至: {file_path}")
        
        audio_file.save(file_path)
        logger.info("檔案儲存成功")
        
        try:
            # 轉換音訊
            logger.info("開始轉換音訊")
            text = transcribe_audio(file_path)
            logger.info("音訊轉換完成")
            
            # 生成護理報告
            report = generate_care_report(text)

            return jsonify({
                'success': True,
                'text': text,
                'report': report
            })
            
        finally:
            # 清理暫存檔案
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("暫存檔案已清理")
        
    except Exception as e:
        logger.error(f"處理失敗: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'處理失敗: {str(e)}'
        }), 500

# 設定 Flask 環境
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

@app.route('/api/check-support', methods=['GET'])
def check_support():
    """檢查瀏覽器支援狀態"""
    return jsonify({
        'success': True,
        'formats': list(ALLOWED_EXTENSIONS)
    })

@app.route('/care-record/edit', methods=['POST'])
def edit_report():
    try:
        data = request.json
        original_text = data.get('text', '')
        edited_text = data.get('edited_text', '')
        
        print("原始文本:", original_text)
        print("編輯後文本:", edited_text)

        # 使用編輯後的文本重新生成報告
        report = generate_care_report(edited_text)

        return jsonify({
            'success': True,
            'text': edited_text,
            'report': report
        }, ensure_ascii=False)

    except Exception as e:
        print(f"編輯報告錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    # 在啟動時檢查 API 金鑰
    logger.info("=== 應用程式啟動 ===")
    check_api_key()
    
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port, debug=True)