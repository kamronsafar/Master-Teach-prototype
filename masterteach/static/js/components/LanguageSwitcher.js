class LanguageSwitcher {
    constructor() {
        this.currentLang = localStorage.getItem('selectedLanguage') || 'en';
        this.supportedLanguages = {
            'en': 'English',
            'zh-CN': '中文 (简体)',
            'hi': 'हिन्दी',
            'es': 'Español',
            'fr': 'Français',
            'ar': 'العربية',
            'bn': 'বাংলা',
            'ru': 'Русский',
            'pt': 'Português',
            'id': 'Bahasa Indonesia',
            'ur': 'اردو',
            'de': 'Deutsch',
            'ja': '日本語',
            'sw': 'Kiswahili',
            'it': 'Italiano',
            'tr': 'Türkçe',
            'ko': '한국어',
            'vi': 'Tiếng Việt',
            'ta': 'தமிழ்',
            'fa': 'فارسی',
            'nl': 'Nederlands',
            'pl': 'Polski',
            'uk': 'Українська',
            'ro': 'Română',
            'hu': 'Magyar',
            'cs': 'Čeština',
            'sv': 'Svenska',
            'el': 'Ελληνικά',
            'th': 'ไทย',
            'ms': 'Bahasa Melayu',
            'uz': 'O\'zbekcha',
            'kk': 'Қазақ',
            'az': 'Azərbaycan',
            'ky': 'Кыргызча',
            'tg': 'Тоҷикӣ',
            'am': 'አማርኛ',
            'yo': 'Yorùbá',
            'da': 'Dansk',
            'no': 'Norsk',
            'fi': 'Suomi'
        };
        this.init();
    }

    init() {
        this.createSwitcher();
        this.attachEventListeners();
    }

    createSwitcher() {
        const switcher = document.createElement('div');
        switcher.className = 'language-switcher';
        switcher.innerHTML = `
            <button class="language-btn">
                <span class="current-lang">${this.supportedLanguages[this.currentLang]}</span>
                <i class="fas fa-chevron-down"></i>
            </button>
            <div class="language-dropdown">
                ${Object.entries(this.supportedLanguages)
                    .map(([code, name]) => `
                        <div class="language-option ${code === this.currentLang ? 'active' : ''}" 
                             data-lang="${code}">
                            ${name}
                        </div>
                    `).join('')}
            </div>
        `;
        document.body.appendChild(switcher);
    }

    attachEventListeners() {
        const btn = document.querySelector('.language-btn');
        const dropdown = document.querySelector('.language-dropdown');
        
        btn.addEventListener('click', () => {
            dropdown.classList.toggle('show');
        });

        document.querySelectorAll('.language-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const newLang = e.target.dataset.lang;
                this.switchLanguage(newLang);
                dropdown.classList.remove('show');
            });
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.language-switcher')) {
                dropdown.classList.remove('show');
            }
        });
    }

    async switchLanguage(newLang) {
        if (newLang === this.currentLang) return;
        
        this.currentLang = newLang;
        localStorage.setItem('selectedLanguage', newLang);
        
        // Update UI
        document.querySelector('.current-lang').textContent = this.supportedLanguages[newLang];
        document.querySelectorAll('.language-option').forEach(option => {
            option.classList.toggle('active', option.dataset.lang === newLang);
        });

        // Translate all translatable elements
        await this.translatePage();

        // Update text translator if it exists
        if (window.textTranslator) {
            window.textTranslator.updateLanguage(newLang);
        }
    }

    async translatePage() {
        const translatableElements = document.querySelectorAll('[data-translate]');
        
        for (const element of translatableElements) {
            const originalText = element.getAttribute('data-translate');
            try {
                const response = await fetch('/api/translate/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify({
                        text: originalText,
                        lang_to: this.currentLang
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                if (data.translated) {
                    element.textContent = data.translated;
                } else if (data.error) {
                    console.error('Translation error:', data.error);
                }
            } catch (error) {
                console.error('Translation error:', error);
            }
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
}

// Initialize the language switcher
document.addEventListener('DOMContentLoaded', () => {
    window.languageSwitcher = new LanguageSwitcher();
}); 