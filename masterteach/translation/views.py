from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from deep_translator import GoogleTranslator
from django.conf import settings

SUPPORTED_LANGUAGES = {
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
}

@csrf_exempt
def translate_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text')
            lang_to = data.get('lang_to', 'en')

            if not text:
                return JsonResponse({'error': 'Text is required'}, status=400)

            if lang_to not in SUPPORTED_LANGUAGES:
                return JsonResponse({'error': 'Unsupported language'}, status=400)

            # Try to detect source language
            try:
                translator = GoogleTranslator(source='auto', target=lang_to)
                translated = translator.translate(text)
                return JsonResponse({
                    'translated': translated,
                    'source_lang': translator.source,
                    'target_lang': lang_to
                })
            except Exception as e:
                return JsonResponse({
                    'error': 'Translation failed',
                    'details': str(e)
                }, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

def get_supported_languages(request):
    """Return list of supported languages"""
    return JsonResponse({
        'languages': SUPPORTED_LANGUAGES
    })
