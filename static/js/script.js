let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function uploadAudio(blob) {
    try {
        console.log('開始上傳音訊檔案');
        console.log('音訊格式:', blob.type);
        console.log('檔案大小:', blob.size, 'bytes');
        
        const formData = new FormData();
        formData.append('audio', blob, `recording${blob.type.includes('webm') ? '.webm' : '.mp4'}`);
        
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`上傳失敗 (${response.status}): ${errorText}`);
        }
        
        const data = await response.json();
        console.log('處理結果:', data);
        
        if (data.success) {
            // 顯示原始文字
            document.getElementById('result').textContent = `語音內容：${data.text}`;
            
            // 顯示照護報告
            const reportElement = document.getElementById('care-report');
            if (reportElement) {
                reportElement.innerHTML = data.report.replace(/\n/g, '<br>');
            }
            
            recordingStatus.textContent = '準備就緒';
        } else {
            throw new Error(data.error || '處理失敗');
        }
    } catch (error) {
        console.error('上傳錯誤：', error);
        recordingStatus.textContent = '處理失敗';
        alert('處理過程中發生錯誤：' + error.message);
    }
}

// 更新錄音相關的程式碼
async function startRecording() {
    try {
        console.log('開始錄音');
        recordingStatus.textContent = '請在瀏覽器的安全提示中允許使用麥克風';
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100,
                channelCount: 1
            }
        });

        console.log('取得麥克風權限');
        
        // 檢查支援的 MIME 類型
        const mimeTypes = [
            'audio/webm',
            'audio/webm;codecs=opus',
            'audio/mp4',
            'audio/mp4;codecs=mp4a',
            'audio/ogg',
            'audio/ogg;codecs=opus'
        ];
        
        let selectedMimeType = '';
        for (const type of mimeTypes) {
            if (MediaRecorder.isTypeSupported(type)) {
                selectedMimeType = type;
                console.log('使用的音訊格式:', type);
                break;
            }
        }
        
        if (!selectedMimeType) {
            throw new Error('找不到支援的音訊格式');
        }
        
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: selectedMimeType,
            audioBitsPerSecond: 128000
        });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            console.log('錄音結束，準備上傳');
            const audioBlob = new Blob(audioChunks, { type: selectedMimeType });
            await uploadAudio(audioBlob);
        };

        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        
        recordButton.classList.add('recording');
        recordButton.innerHTML = '<i class="fas fa-stop"></i>';
        recordingStatus.textContent = '正在錄音...';
        
    } catch (error) {
        console.error('錄音失敗：', error);
        recordingStatus.textContent = '錄音失敗';
        alert('無法啟動錄音：' + error.message);
    }
}

async function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        console.log('停止錄音');
        mediaRecorder.stop();
        isRecording = false;
        
        recordButton.classList.remove('recording');
        recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
        recordingStatus.textContent = '處理中...';
        
        // 停止所有音訊軌道
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

// 初始化錄音按鈕
document.addEventListener('DOMContentLoaded', () => {
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    
    recordButton.addEventListener('click', () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });
}); 