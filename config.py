import os

# 設定上傳檔案的目錄
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'audio')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允許的檔案類型
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'webm', 'm4a'} 