# 多段語音輸入功能實作說明

## 概述

本專案已成功實作多段語音輸入功能，允許使用者分段錄製語音，系統會將所有段落合併處理並生成照護報告。

## 功能特點

1. **分段錄製**：使用者可以錄製多個語音段落，每段錄製完成後可以選擇繼續錄製或完成
2. **段落管理**：可以播放、刪除已錄製的段落
3. **合併處理**：所有段落會被合併轉錄，生成完整的照護報告
4. **進度顯示**：即時顯示已錄製的段落數量和狀態

## 技術實作

### 前端實作 (index.html)

主要功能包括：

```javascript
// 儲存所有錄音段落
let audioSegments = [];

// 錄音完成後儲存段落
mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: selectedMimeType });
    audioSegments.push({
        blob: audioBlob,
        duration: duration,
        timestamp: new Date().toISOString(),
        mimeType: selectedMimeType
    });
};

// 上傳所有段落
async function uploadAllSegments() {
    const formData = new FormData();
    audioSegments.forEach((segment, index) => {
        formData.append('audio_segments', segment.blob, filename);
    });
    // 發送到 /care-record/upload-multi
}
```

### 後端實作 (app.py)

新增了 `/care-record/upload-multi` 路由來處理多段語音：

```python
@care_record.route('/upload-multi', methods=['POST'])
def upload_multi():
    # 獲取所有音訊段落
    audio_segments = request.files.getlist('audio_segments')
    
    # 處理每個段落
    for i, audio_file in enumerate(audio_segments):
        # 轉換格式
        # 轉錄文字
        segment_text = transcribe_audio(mp4_path)
        all_transcriptions.append(f"[段落 {i+1}] {segment_text}")
    
    # 合併所有轉錄文字
    combined_text = "\n\n".join(all_transcriptions)
    
    # 生成照護報告
    report = generate_care_report(combined_text)
```

## 使用方式

### 主頁面 (/)

1. 點擊「開始錄音」開始第一段錄製
2. 點擊「停止錄音」結束當前段落
3. 可以查看已錄製的段落列表，包含播放和刪除功能
4. 繼續點擊「繼續錄音」錄製更多段落
5. 所有段落錄製完成後，點擊「完成所有錄音」
6. 系統會合併所有段落並生成照護報告

### 測試頁面 (/test-multi-segment)

提供簡化的測試介面，方便測試多段語音輸入功能。

## 資料儲存結構

多段錄音的資料會儲存在以下結構：

```
records/
├── YYYYMMDD/
│   └── multi_HHMMSS/
│       ├── segment_1.mp4
│       ├── segment_2.mp4
│       ├── segment_N.mp4
│       ├── combined_text.txt     # 合併的轉錄文字
│       ├── segments_text.json    # 各段落的轉錄文字
│       ├── report.md            # 生成的照護報告
│       └── record.json          # 完整記錄
```

## 優點

1. **靈活性**：使用者可以在思考時暫停，整理思緒後繼續錄製
2. **容錯性**：如果某段錄製不理想，可以刪除重錄
3. **完整性**：系統會保留所有段落的原始錄音和轉錄文字
4. **連貫性**：合併後的文字會標註段落編號，保持上下文關係

## 注意事項

1. 每個段落建議不要超過 5 分鐘，以確保轉錄品質
2. 段落之間的停頓時間不限，使用者可以充分思考
3. 系統會自動處理音訊格式轉換（WebM → MP4）
4. 所有段落會依序合併，請注意錄製順序

## API 端點

- **單段上傳**：`POST /care-record/upload`
- **多段上傳**：`POST /care-record/upload-multi`
- **測試頁面**：`GET /test-multi-segment`

## 瀏覽器支援

- Chrome/Edge：完整支援
- Firefox：完整支援
- Safari：需要 iOS 14.3+ 或 macOS Big Sur+

## 未來改進方向

1. 支援拖曳調整段落順序
2. 支援段落編輯（重新錄製特定段落）
3. 加入語音品質檢測
4. 支援背景噪音消除
5. 加入即時轉錄預覽