// Initialize Lucide icons
lucide.createIcons();

// DOM Elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const recordBtn = document.getElementById('record-btn');
const recordStatus = document.getElementById('record-status');
const visualizer = document.getElementById('visualizer');
const textInput = document.getElementById('text-input');
const processTextBtn = document.getElementById('process-text-btn');
const jsonOutput = document.getElementById('json-output');
const loader = document.getElementById('loader');
const copyBtn = document.getElementById('copy-btn');

// State
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let visualizerInterval = null;

const API_BASE = 'http://localhost:8000';

// Tab Switching
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(`${tabId}-tab`).classList.add('active');
    });
});

// Animate visualizer when recording
function startVisualizer() {
    visualizer.classList.add('active');
    const bars = visualizer.querySelectorAll('.bar');
    visualizerInterval = setInterval(() => {
        bars.forEach(bar => {
            const height = Math.random() * 20 + 5;
            bar.style.height = `${height}px`;
        });
    }, 100);
}

function stopVisualizer() {
    visualizer.classList.remove('active');
    clearInterval(visualizerInterval);
    const bars = visualizer.querySelectorAll('.bar');
    bars.forEach(bar => {
        bar.style.height = '10px';
    });
}

// Audio Recording
async function toggleRecording() {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Check supported mime types
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
                ? 'audio/webm;codecs=opus' 
                : 'audio/mp4';
                
            mediaRecorder = new MediaRecorder(stream, { mimeType });
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                await sendAudioToAPI(audioBlob);
                
                // Stop all tracks to release mic
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            recordBtn.classList.add('recording');
            recordStatus.textContent = 'Recording... Click to stop';
            startVisualizer();
            
        } catch (err) {
            console.error('Error accessing microphone:', err);
            recordStatus.textContent = 'Microphone access denied';
            recordStatus.style.color = 'var(--danger-color)';
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.classList.remove('recording');
        recordStatus.textContent = 'Processing audio...';
        stopVisualizer();
    }
}

recordBtn.addEventListener('click', toggleRecording);

// Process Audio
async function sendAudioToAPI(audioBlob) {
    showLoader();
    try {
        const formData = new FormData();
        // Append a proper extension to the filename based on blob type
        const ext = audioBlob.type.includes('webm') ? 'webm' : 'mp4';
        formData.append('file', audioBlob, `recording.${ext}`);

        const response = await fetch(`${API_BASE}/stt/transcribe`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        displayOutput(data);
        recordStatus.textContent = 'Ready to record';
    } catch (error) {
        console.error('API Error:', error);
        displayOutput({ error: error.message || 'Failed to process audio' });
        recordStatus.textContent = 'Ready to record';
    } finally {
        hideLoader();
    }
}

// Process Text
processTextBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) return;

    showLoader();
    try {
        const response = await fetch(`${API_BASE}/stt/text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });

        const data = await response.json();
        displayOutput(data);
    } catch (error) {
        console.error('API Error:', error);
        displayOutput({ error: error.message || 'Failed to process text' });
    } finally {
        hideLoader();
    }
});

// UI Helpers
function showLoader() {
    loader.classList.remove('hidden');
    jsonOutput.style.opacity = '0.5';
}

function hideLoader() {
    loader.classList.add('hidden');
    jsonOutput.style.opacity = '1';
}

function displayOutput(data) {
    jsonOutput.textContent = JSON.stringify(data, null, 2);
}

// Copy to clipboard
copyBtn.addEventListener('click', () => {
    const text = jsonOutput.textContent;
    if (text === 'Waiting for input...') return;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalHtml = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i data-lucide="check" class="text-accent"></i>';
        lucide.createIcons();
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHtml;
            lucide.createIcons();
        }, 2000);
    });
});
