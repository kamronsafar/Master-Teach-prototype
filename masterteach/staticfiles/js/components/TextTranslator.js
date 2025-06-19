class TextTranslator {
    constructor() {
        this.currentLang = localStorage.getItem('selectedLanguage') || 'en';
        this.isVisible = false;
        this.isMinimized = false;
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.init();
    }

    init() {
        this.createTranslator();
        this.attachEventListeners();
    }

    createTranslator() {
        const translator = document.createElement('div');
        translator.className = 'text-translator';
        translator.style.display = 'none';
        translator.innerHTML = `
            <div class="translator-header">
                <div class="translator-title">
                    <h3>Translate Text</h3>
                </div>
                <div class="translator-controls">
                    <button class="minimize-translator" title="Minimize">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                    </button>
                    <button class="close-translator" title="Close">&times;</button>
                </div>
            </div>
            <div class="translator-container">
                <div class="translator-input">
                    <textarea 
                        placeholder="Enter text to translate..." 
                        class="source-text"
                    ></textarea>
                </div>
                <div class="translator-output">
                    <div class="translated-text"></div>
                    <div class="translation-info"></div>
                </div>
            </div>
        `;
        document.body.appendChild(translator);
    }

    attachEventListeners() {
        const sourceText = document.querySelector('.source-text');
        const translationToggle = document.getElementById('translationToggle');
        const closeButton = document.querySelector('.close-translator');
        const minimizeButton = document.querySelector('.minimize-translator');
        const translator = document.querySelector('.text-translator');
        const translatorHeader = document.querySelector('.translator-header');
        let debounceTimer;

        // Make translator draggable
        translatorHeader.addEventListener('mousedown', (e) => {
            if (e.target.closest('.translator-controls')) return;
            
            this.isDragging = true;
            const rect = translator.getBoundingClientRect();
            this.dragOffset = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            
            document.addEventListener('mousemove', this.handleDrag);
            document.addEventListener('mouseup', this.stopDrag);
        });

        translationToggle.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleTranslator();
        });

        closeButton.addEventListener('click', () => {
            this.hideTranslator();
        });

        minimizeButton.addEventListener('click', () => {
            this.toggleMinimize();
        });

        document.addEventListener('click', (e) => {
            const translateBtn = document.querySelector('.nav-translate-button');
            if (!translator.contains(e.target) && !translateBtn.contains(e.target)) {
                this.hideTranslator();
            }
        });

        sourceText.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.translateText(e.target.value);
            }, 500);
        });
    }

    handleDrag = (e) => {
        if (!this.isDragging) return;
        
        const translator = document.querySelector('.text-translator');
        const x = e.clientX - this.dragOffset.x;
        const y = e.clientY - this.dragOffset.y;
        
        // Keep within window bounds
        const maxX = window.innerWidth - translator.offsetWidth;
        const maxY = window.innerHeight - translator.offsetHeight;
        
        translator.style.left = `${Math.min(Math.max(0, x), maxX)}px`;
        translator.style.top = `${Math.min(Math.max(0, y), maxY)}px`;
    }

    stopDrag = () => {
        this.isDragging = false;
        document.removeEventListener('mousemove', this.handleDrag);
        document.removeEventListener('mouseup', this.stopDrag);
    }

    toggleMinimize() {
        const translator = document.querySelector('.text-translator');
        const container = document.querySelector('.translator-container');
        const minimizeBtn = document.querySelector('.minimize-translator');
        
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            container.style.display = 'none';
            translator.style.height = 'auto';
            minimizeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
            `;
        } else {
            container.style.display = 'block';
            translator.style.height = 'auto';
            minimizeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
            `;
        }
    }

    toggleTranslator() {
        const translator = document.querySelector('.text-translator');
        if (this.isVisible) {
            this.hideTranslator();
        } else {
            this.showTranslator();
        }
    }

    showTranslator() {
        const translator = document.querySelector('.text-translator');
        translator.style.display = 'block';
        this.isVisible = true;
        setTimeout(() => {
            translator.classList.add('translator-visible');
        }, 10);
    }

    hideTranslator() {
        const translator = document.querySelector('.text-translator');
        translator.classList.remove('translator-visible');
        setTimeout(() => {
            translator.style.display = 'none';
            this.isVisible = false;
            this.isMinimized = false;
            const container = document.querySelector('.translator-container');
            container.style.display = 'block';
        }, 300);
    }

    async translateText(text) {
        if (!text.trim()) {
            document.querySelector('.translated-text').textContent = '';
            document.querySelector('.translation-info').textContent = '';
            return;
        }

        try {
            const response = await fetch('/api/translate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    text: text,
                    lang_to: this.currentLang
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.translated) {
                document.querySelector('.translated-text').textContent = data.translated;
                document.querySelector('.translation-info').textContent = 
                    `Translated from ${data.source_lang} to ${data.target_lang}`;
            } else if (data.error) {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Translation error:', error);
            document.querySelector('.translated-text').textContent = 'Translation failed: ' + error.message;
            document.querySelector('.translation-info').textContent = '';
        }
    }

    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    updateLanguage(newLang) {
        this.currentLang = newLang;
        const sourceText = document.querySelector('.source-text');
        if (sourceText.value.trim()) {
            this.translateText(sourceText.value);
        }
    }
}

// Initialize the text translator
document.addEventListener('DOMContentLoaded', () => {
    window.textTranslator = new TextTranslator();
}); 