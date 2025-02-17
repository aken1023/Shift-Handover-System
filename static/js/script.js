async function uploadAudio(blob) {
    try {
        console.log('開始上傳音訊檔案');
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        
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
            document.getElementById('result').textContent = data.text;
            
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
                sampleRate: 44100
            }
        });

        console.log('取得麥克風權限');
        
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            console.log('錄音結束，準備上傳');
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
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