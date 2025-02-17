let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let timerInterval;
let startTime;
const recordButton = document.getElementById('recordButton');
const recordingStatus = document.getElementById('recordingStatus');

async function uploadAudio(blob) {
    try {
        console.log('開始上傳音訊檔案');
        console.log('檔案大小:', blob.size, 'bytes');
        
        const formData = new FormData();
        const extension = blob.type.includes('webm') ? '.webm' : '.mp4';
        formData.append('audio', blob, 'recording' + extension);
        
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`上傳失敗 (${response.status})`);
        }
        
        const data = await response.json();
        console.log('處理結果:', data);
        
        if (data.success) {
            document.getElementById('result').textContent = `語音內容：${data.text}`;
            
            const reportElement = document.getElementById('care-report');
            if (reportElement) {
                reportElement.innerHTML = data.report.replace(/\n/g, '<br>');
            }
            
            const recordingStatus = document.getElementById('recordingStatus');
            if (recordingStatus) {
                recordingStatus.textContent = '完成';
            }
        } else {
            throw new Error(data.error || '處理失敗');
        }
    } catch (error) {
        console.error('上傳錯誤：', error);
        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '處理失敗';
        }
    }
}

// 檢查瀏覽器支援
function checkCompatibility() {
    console.log('檢查瀏覽器相容性');
    const checks = {
        'MediaRecorder API': !!window.MediaRecorder,
        'getUserMedia': !!navigator.mediaDevices?.getUserMedia,
        'Blob': !!window.Blob,
        'FormData': !!window.FormData,
        'Fetch API': !!window.fetch
    };

    for (const [feature, supported] of Object.entries(checks)) {
        console.log(`${feature}: ${supported ? '支援' : '不支援'}`);
    }

    return Object.values(checks).every(v => v);
}

// 檢查音訊格式支援
function checkAudioFormats() {
    const mimeTypes = [
        'audio/webm',
        'audio/webm;codecs=opus',
        'audio/mp4',
        'audio/mp4;codecs=mp4a',
        'audio/ogg',
        'audio/ogg;codecs=opus'
    ];

    const supportedFormats = mimeTypes.filter(type => MediaRecorder.isTypeSupported(type));
    console.log('支援的音訊格式:', supportedFormats);
    return supportedFormats;
}

async function startRecording() {
    try {
        console.log('開始錄音...');
        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '請允許使用麥克風';
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100,
                channelCount: 1
            }
        });

        console.log('已取得麥克風權限');

        // 選擇支援的音訊格式
        const mimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/ogg'
        ];

        let selectedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type));
        
        if (!selectedMimeType) {
            throw new Error('找不到支援的音訊格式');
        }

        console.log('使用音訊格式:', selectedMimeType);

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

        // 更新 UI
        const recordButton = document.getElementById('recordButton');
        const timer = document.getElementById('timer');
        const progressBar = document.getElementById('progressBar');
        
        if (recordButton) {
            recordButton.classList.add('recording');
            recordButton.innerHTML = '<i class="fas fa-stop fa-2x"></i>';
        }
        if (recordingStatus) {
            recordingStatus.textContent = '正在錄音...';
        }
        if (timer) {
            timer.classList.remove('d-none');
            startTime = new Date();
            timerInterval = setInterval(updateTimer, 1000);
            updateTimer();
        }
        if (progressBar) {
            progressBar.classList.remove('d-none');
        }

    } catch (error) {
        console.error('錄音失敗:', error);
        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '錄音失敗: ' + error.message;
        }
    }
}

async function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        console.log('停止錄音');
        mediaRecorder.stop();
        isRecording = false;

        const recordButton = document.getElementById('recordButton');
        if (recordButton) {
            recordButton.innerHTML = '<i class="fas fa-microphone fa-2x"></i>';
            recordButton.classList.remove('recording');
        }

        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '處理中...';
        }

        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('開始初始化錄音功能');
    
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    
    // 檢查瀏覽器相容性
    const isCompatible = checkCompatibility();
    if (!isCompatible) {
        console.error('瀏覽器不支援所需功能');
        if (recordButton) {
            recordButton.disabled = true;
        }
        if (recordingStatus) {
            recordingStatus.textContent = '您的瀏覽器不支援所需功能';
        }
        return;
    }
    
    // 檢查音訊格式支援
    const supportedFormats = checkAudioFormats();
    if (supportedFormats.length === 0) {
        console.error('找不到支援的音訊格式');
        if (recordButton) {
            recordButton.disabled = true;
        }
        if (recordingStatus) {
            recordingStatus.textContent = '您的瀏覽器不支援任何可用的音訊格式';
        }
        return;
    }
    
    // 綁定事件
    if (recordButton) {
        recordButton.disabled = false;
        recordButton.addEventListener('click', () => {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });
    }
    
    if (recordingStatus) {
        recordingStatus.textContent = '準備就緒';
    }
    
    console.log('錄音功能初始化完成');
}); 