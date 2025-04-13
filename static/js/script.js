let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let timerInterval;
let startTime;
const recordButton = document.getElementById('recordButton');
const recordingStatus = document.getElementById('recordingStatus');
let originalText = '';
let currentReport = '';

async function uploadAudio(blob) {
    try {
        const formData = new FormData();
        formData.append('audio', blob, `recording${blob.type.includes('webm') ? '.webm' : '.mp4'}`);

        const recordingStatus = document.getElementById('recordingStatus');
        recordingStatus.textContent = '正在處理...';
        recordingStatus.className = 'status warning';

        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`上傳失敗 (${response.status})`);
        }

        const data = await response.json();
        console.log('API 回應:', data);

        if (data.success) {
            originalText = data.text;  // 保存原始文本
            displayResult(data);
            recordingStatus.textContent = '完成';
            recordingStatus.className = 'status success';
        } else {
            throw new Error(data.error || '處理失敗');
        }
    } catch (error) {
        console.error('錯誤:', error);
        recordingStatus.textContent = '處理失敗: ' + error.message;
        recordingStatus.className = 'status error';
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

// 計時器更新函數
function updateTimer() {
    const now = new Date();
    const diff = now - startTime;
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    const timer = document.getElementById('timer');
    if (timer) {
        timer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        timer.style.display = 'block'; // 確保計時器可見
    }
}

async function startRecording() {
    try {
        console.log('開始錄音...');
        const recordingStatus = document.getElementById('recordingStatus');
        const timer = document.getElementById('timer');
        
        // 重置並啟動計時器
        startTime = new Date();
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        timerInterval = setInterval(updateTimer, 1000);
   

        if (recordingStatus) {
            recordingStatus.textContent = '請允許使用麥克風';
            recordingStatus.className = 'status warning';
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
            const audioBlob = new Blob(audioChunks, { type: selectedMimeType });
            await uploadAudio(audioBlob);
        };

        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        updateTimer(); // 立即更新一次計時器

        // 更新 UI
        const recordButton = document.getElementById('recordButton');
        if (recordButton) {
            recordButton.textContent = '停止錄音';
            recordButton.classList.add('recording');
        }
        
        if (recordingStatus) {
            recordingStatus.textContent = '正在錄音...';
            recordingStatus.className = 'status warning';
        }
        
        if (timer) {
            timer.style.display = 'block';
            
        }

    } catch (error) {
        console.error('錄音失敗:', error);
        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '錄音失敗: ' + error.message;
            recordingStatus.className = 'status error';
        }
        if (timerInterval) {
            clearInterval(timerInterval);
        }
    }
}

async function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        // 停止計時器
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        const timer = document.getElementById('timer');
 

        mediaRecorder.stop();
        isRecording = false;

        const recordButton = document.getElementById('recordButton');
        const recordingStatus = document.getElementById('recordingStatus');
        
        if (recordButton) {
            recordButton.textContent = '開始錄音';
            recordButton.classList.remove('recording');
        }

        if (recordingStatus) {
            recordingStatus.textContent = '處理中...';
            recordingStatus.className = 'status warning';
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

    const timer = document.getElementById('timer');
    if (timer) {
        timer.style.display = 'block';
        
    }
});

function showEditForm() {
    const resultSection = document.getElementById('result-section');
    resultSection.innerHTML = `
        <div class="edit-form">
            <h3>編輯語音內容</h3>
            <textarea id="editText" rows="6" class="form-control">${originalText}</textarea>
            <div class="button-group">
                <button onclick="saveEdit()" class="btn btn-primary">儲存</button>
                <button onclick="cancelEdit()" class="btn btn-secondary">取消</button>
            </div>
        </div>
    `;
}

async function saveEdit() {
    try {
        const editedText = document.getElementById('editText').value;
        const recordingStatus = document.getElementById('recordingStatus');
        
        recordingStatus.textContent = '處理中...';
        recordingStatus.className = 'status warning';

        const response = await fetch('/care-record/edit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: originalText,  // 保存原始文本
                edited_text: editedText
            })
        });

        const data = await response.json();
        
        if (data.success) {
            originalText = editedText;  // 更新原始文本
            displayResult(data);
            recordingStatus.textContent = '完成';
            recordingStatus.className = 'status success';
        } else {
            throw new Error(data.error || '處理失敗');
        }
    } catch (error) {
        console.error('編輯錯誤:', error);
        const recordingStatus = document.getElementById('recordingStatus');
        recordingStatus.textContent = '處理失敗: ' + error.message;
        recordingStatus.className = 'status error';
    }
}

function cancelEdit() {
    // 恢復原始顯示
    displayResult({
        text: originalText,
        report: currentReport
    });
}

// 修改 displayResult 函數
function displayResult(data) {
    const resultSection = document.getElementById('result-section');
    
    // 保存當前報告和文本
    currentReport = data.report;
    originalText = data.text;
    
    resultSection.innerHTML = `
        <div class="result-container">
            <div class="speech-text">
                <h3>語音內容</h3>
                <p>${data.text}</p>
                <button onclick="showEditForm()" class="btn btn-edit">
                    編輯內容
                </button>
            </div>
            <div class="report">
                <h3>工廠評估報告</h3>
                <div class="report-content">
                    ${formatReport(data.report)}
                </div>
            </div>
        </div>
    `;
}

function formatReport(report) {
    // 實現報告格式化的邏輯
    // 這裡需要根據實際的報告格式來實現
    return report;
} 