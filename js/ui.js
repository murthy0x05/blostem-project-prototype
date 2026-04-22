/* ============================================
   🎨 UI Module — DOM & Animations
   ============================================ */

class UI {
  constructor() {
    // Cache DOM refs
    this.micBtn = document.getElementById('mic-btn');
    this.micLabel = document.getElementById('mic-label');
    this.waveform = document.getElementById('waveform');
    this.transcriptBody = document.getElementById('transcript-body');
    this.responseBody = document.getElementById('response-body');
    this.responseCard = document.getElementById('response-card');
    this.playBtn = document.getElementById('play-btn');
    this.historyList = document.getElementById('history-list');
    this.historySection = document.getElementById('history-section');

    // Settings
    this.settingsToggle = document.getElementById('settings-toggle');
    this.settingsOverlay = document.getElementById('settings-overlay');
    this.settingsPanel = document.getElementById('settings-panel');
    this.settingsClose = document.getElementById('settings-close');
    this.apiKeyInput = document.getElementById('api-key-input');
    this.speedSlider = document.getElementById('speed-slider');
    this.speedValue = document.getElementById('speed-value');
    this.apiKeyNotice = document.getElementById('api-key-notice');

    // Toast container
    this.toastContainer = document.getElementById('toast-container');

    // Lang buttons
    this.langButtons = document.querySelectorAll('.lang-btn');

    // Bind settings panel
    this._initSettingsPanel();
    this._initSpeedSlider();
  }

  /* ---------- Settings Panel ---------- */
  _initSettingsPanel() {
    this.settingsToggle.addEventListener('click', () => this.openSettings());
    this.settingsOverlay.addEventListener('click', () => this.closeSettings());
    this.settingsClose.addEventListener('click', () => this.closeSettings());

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.closeSettings();
    });

    // API key notice click
    if (this.apiKeyNotice) {
      this.apiKeyNotice.addEventListener('click', () => this.openSettings());
    }
  }

  openSettings() {
    this.settingsPanel.classList.add('open');
    this.settingsOverlay.classList.add('open');
    this.apiKeyInput.focus();
  }

  closeSettings() {
    this.settingsPanel.classList.remove('open');
    this.settingsOverlay.classList.remove('open');
  }

  /* ---------- Speed Slider ---------- */
  _initSpeedSlider() {
    if (this.speedSlider && this.speedValue) {
      this.speedSlider.addEventListener('input', () => {
        this.speedValue.textContent = `${this.speedSlider.value}×`;
      });
    }
  }

  getSpeed() {
    return this.speedSlider ? parseFloat(this.speedSlider.value) : 1.0;
  }

  /* ---------- API Key ---------- */
  getApiKey() {
    return this.apiKeyInput ? this.apiKeyInput.value.trim() : '';
  }

  setApiKey(key) {
    if (this.apiKeyInput) this.apiKeyInput.value = key;
  }

  showApiKeyNotice(show) {
    if (this.apiKeyNotice) {
      this.apiKeyNotice.classList.toggle('hidden', !show);
    }
  }

  /* ---------- Language Buttons ---------- */
  setActiveLanguage(langCode) {
    this.langButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === langCode);
    });
  }

  /* ---------- Mic State ---------- */
  setMicState(state) {
    // state: 'idle' | 'recording' | 'processing' | 'speaking'
    this.micBtn.classList.remove('recording');
    this.micLabel.classList.remove('recording-label', 'processing-label');

    switch (state) {
      case 'recording':
        this.micBtn.classList.add('recording');
        this.micLabel.textContent = 'Listening... Tap to stop';
        this.micLabel.classList.add('recording-label');
        this.waveform.classList.add('active');
        break;
      case 'processing':
        this.micLabel.textContent = 'Analyzing your query...';
        this.micLabel.classList.add('processing-label');
        this.waveform.classList.remove('active');
        break;
      case 'speaking':
        this.micLabel.textContent = 'Speaking response...';
        this.micLabel.classList.add('processing-label');
        this.waveform.classList.remove('active');
        break;
      default: // idle
        this.micLabel.textContent = 'Tap the mic and ask about Fixed Deposits';
        this.waveform.classList.remove('active');
        break;
    }
  }

  /* ---------- Transcript ---------- */
  setTranscript(text, isInterim = false) {
    if (!text) {
      this.transcriptBody.textContent = 'Your speech will appear here...';
      this.transcriptBody.classList.add('empty');
      return;
    }
    this.transcriptBody.classList.remove('empty');
    this.transcriptBody.textContent = text;
    if (isInterim) {
      this.transcriptBody.style.opacity = '0.6';
    } else {
      this.transcriptBody.style.opacity = '1';
    }
  }

  /* ---------- Response ---------- */
  setResponse(text) {
    if (!text) {
      this.responseBody.textContent = 'FD suggestions will appear here...';
      this.responseBody.classList.add('empty');
      this.playBtn.disabled = true;
      return;
    }
    this.responseBody.classList.remove('empty');
    this.responseBody.textContent = text;
    this.playBtn.disabled = false;
    this.responseCard.style.animation = 'none';
    // Trigger reflow for re-animation
    void this.responseCard.offsetWidth;
    this.responseCard.style.animation = 'cardFadeIn 0.5s var(--ease-out) both';
  }

  setResponseLoading() {
    this.responseBody.innerHTML = `
      <div class="loader">
        <div class="loader-dot"><span></span><span></span><span></span></div>
        <span>Getting FD suggestions...</span>
      </div>`;
    this.responseBody.classList.remove('empty');
    this.playBtn.disabled = true;
  }

  /* ---------- Play Button State ---------- */
  setPlayState(isSpeaking) {
    if (isSpeaking) {
      this.playBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
        </svg>
        Stop`;
      this.playBtn.classList.add('speaking');
    } else {
      this.playBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Listen`;
      this.playBtn.classList.remove('speaking');
    }
  }

  /* ---------- Conversation History ---------- */
  addToHistory(question, answer, langName) {
    this.historySection.classList.remove('hidden');

    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
      <div class="history-q">${this._escapeHTML(question)}</div>
      <div class="history-a">${this._escapeHTML(answer)}</div>
      <div class="history-meta">${langName} • ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</div>
    `;

    // Prepend (newest first)
    this.historyList.prepend(item);

    // Keep max 10
    while (this.historyList.children.length > 10) {
      this.historyList.removeChild(this.historyList.lastChild);
    }
  }

  /* ---------- Toast Notifications ---------- */
  showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${type === 'error' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️'}</span>
      <span>${this._escapeHTML(message)}</span>
    `;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /* ---------- Helpers ---------- */
  _escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

export default UI;
