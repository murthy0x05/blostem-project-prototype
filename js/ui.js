/* ============================================
   🎨 UI Module — DOM & Animations
   ============================================ */

class UI {
  constructor() {
    // Cache DOM refs
    this.micBtn = document.getElementById('mic-btn');
    this.statusText = document.getElementById('status-text');
    this.waveform = document.getElementById('waveform');
    this.transcriptBody = document.getElementById('transcript-body');
    this.responseBody = document.getElementById('response-body');
    this.responseCard = document.getElementById('response-card');
    this.playBtn = document.getElementById('play-btn');
    this.historyList = document.getElementById('history-list');
    this.historySection = document.getElementById('history-section');

    // Toast container
    this.toastContainer = document.getElementById('toast-container');

    // Lang buttons
    this.langButtons = document.querySelectorAll('.lang-btn');

    // Initialize interactive content
    this.initCollapsibles();
  }

  /* ---------- Language Buttons ---------- */
  setActiveLanguage(langCode) {
    this.langButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === langCode);
    });
  }

  /* ---------- Collapsible Sections ---------- */
  initCollapsibles() {
    const collapsibles = document.querySelectorAll('.section-header.collapsible');
    collapsibles.forEach(header => {
      // Set initial collapsed state
      header.classList.add('collapsed');
      const content = header.nextElementSibling;
      if (content && content.classList.contains('section-body')) {
        content.classList.add('collapsed');
      }

      header.addEventListener('click', () => {
        header.classList.toggle('collapsed');
        if (content && content.classList.contains('section-body')) {
          content.classList.toggle('collapsed');
        }
      });
    });
  }

  /* ---------- Mic State ---------- */
  setMicState(state) {
    // state: 'idle' | 'recording' | 'processing' | 'speaking'
    this.micBtn.classList.remove('recording');
    this.statusText.classList.remove('recording', 'processing', 'speaking');

    switch (state) {
      case 'recording':
        this.micBtn.classList.add('recording');
        this.statusText.innerHTML = '<span class="brand-highlight">RichPerson</span> is listening...';
        this.statusText.classList.add('recording');
        this.waveform.classList.add('active');
        break;
      case 'processing':
        this.statusText.innerHTML = '<span class="brand-highlight">RichPerson</span> is thinking...';
        this.statusText.classList.add('processing');
        this.waveform.classList.remove('active');
        break;
      case 'speaking':
        this.statusText.innerHTML = '<span class="brand-highlight">RichPerson</span> is speaking...';
        this.statusText.classList.add('speaking');
        this.waveform.classList.remove('active');
        break;
      default: // idle
        this.statusText.innerHTML = 'Ask <span class="brand-highlight">RichPerson</span> about Fixed Deposits';
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
