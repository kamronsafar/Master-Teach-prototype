# MasterTeach
**Learn languages through films** — a Django web application for uploading and watching videos with bilingual subtitles, vocabulary analysis aligned to CEFR levels, and user progress tracking.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-4.2%2B-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Overview

MasterTeach helps learners improve English (and other languages) by watching films with structured subtitles and NLP-powered insights. Users can register, sign in (including Google OAuth), optionally enable two-factor authentication, upload videos with English and Russian subtitle tracks, and play content in a custom player with learning-oriented UI.

The project combines a Django backend with subtitle processing (SRT → WebVTT), optional background jobs via Celery, and text analysis using NLTK, spaCy, and Gensim Word2Vec for CEFR-style vocabulary profiling.

---

## Features

| Area | Description |
|------|-------------|
| **Authentication** | Email-based accounts (`CustomUser`), signup with password strength rules, login rate limiting, Google OAuth via [django-allauth](https://django-allauth.readthedocs.io/) |
| **Security** | TOTP-based MFA (QR setup with `pyotp` / `qrcode`), optional 2FA at login |
| **Films** | Upload MP4 + English/Russian subtitles; automatic SRT → VTT conversion on save |
| **Player** | HTML5 video with Plyr, dual-subtitle controls, learning tools panel |
| **NLP / CEFR** | `resurs_for_films` module analyzes subtitle text and maps vocabulary to CEFR bands (A1–C2) using Word2Vec + heuristics; example scripts in `example_subtitle/` |
| **Profiles** | Extended user profile (avatar, bio), per-film learning progress stored as JSON (`UserProgress`) |
| **Translation** | `translation` app for generating translated subtitle files (Russian, Chinese) — integration in progress |
| **Automation** | `MovieAutomation` utilities (TMDB metadata, OpenSubtitles, spaCy, CEFR word lists) in `resurs_for_films/` |

---

## Tech Stack

- **Backend:** Django 4.2+, SQLite (default)
- **Auth:** django-allauth, django-crispy-forms + Bootstrap 5
- **Async:** Celery + Redis (broker and result backend)
- **NLP:** NLTK, spaCy (`en_core_web_sm`), Gensim, langdetect, googletrans
- **Media:** ffmpeg-python, pysrt, chunked large uploads (up to 10 GB configured)
- **Frontend:** Django templates, custom CSS (light/dark theme), Font Awesome, Plyr.js
- **APIs (optional):** TMDB, OpenSubtitles, Google Cloud Language

---

## Project Structure

```
masterteach/
├── manage.py                 # Django CLI entry point
├── requirements.txt          # Python dependencies
├── masterteach/              # Project settings, URLs, Celery config
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── user/                     # Custom user model, login, signup, MFA
├── films/                    # Film model, upload, list, player views
├── profiles/                 # User profile & UserProgress models
├── translation/              # Translated subtitle models & views
├── resurs_for_films/         # SRT analysis, CEFR, movie automation (utility package)
├── example_subtitle/         # Standalone CEFR / Word2Vec examples
├── templates/                # HTML templates (base, films, user, learning)
├── static/                   # CSS, JS (e.g. subtitles.js)
├── staticfiles/              # collectstatic output (generated)
├── media/                    # Uploaded videos & subtitles (runtime)
└── tmp/                      # Chunked upload temp directory
```

---

## Prerequisites

- **Python** 3.10 or newer
- **pip** and a virtual environment (`venv` recommended)
- **FFmpeg** (for video/subtitle processing)
- **Redis** (required if you run Celery workers)
- **System libraries** for `python-magic` (file type detection) on Linux

Some dependencies used in `settings.py` are not listed in `requirements.txt`. Install them explicitly if needed:

```bash
pip install celery redis django-cors-headers pyotp qrcode[pil] social-auth-app-django
```

For Hugging Face–based translation in `translation/views.py`:

```bash
pip install transformers torch webvtt-py
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/masterteach.git
cd masterteach
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # if not installed via requirements URL
```

Download NLTK data (also attempted automatically by the Celery worker):

```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
```

### 4. Environment variables

Create a `.env` file in the project root (never commit secrets):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Google OAuth (django-allauth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional integrations
TMDB_API_KEY=your-tmdb-api-key
OPENSUBTITLES_API_KEY=your-opensubtitles-key
```

> **Security note:** Replace any default keys in `settings.py` before deploying to production. Set `DEBUG=False`, configure HTTPS, and use a production database (PostgreSQL recommended).

### 5. Database and static files

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 6. Run the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

### 7. (Optional) Start Celery

In a separate terminal, with Redis running on `localhost:6379`:

```bash
celery -A masterteach worker -l info
```

---

## Usage

1. **Sign up** at `/signup` or **log in** at `/login` (or use Google via `/accounts/`).
2. From the home page, go to **Films** (`/films/`).
3. **Upload** a video (`.mp4`) plus English and Russian subtitle files (`.srt` or `.vtt`) at `/films/upload/`.
4. **Play** a film from the list; switch subtitle tracks or use dual-subtitle mode in the player.
5. Manage your **profile** at `/profile/` and enable **MFA** from the profile UI when configured.

Admin interface: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## URL Map (main routes)

| Path | Description |
|------|-------------|
| `/` | Home (authenticated) |
| `/login`, `/signup`, `/logout` | Authentication |
| `/profile/`, `/settings/` | User profile and settings |
| `/films/` | Film catalog |
| `/films/upload/` | Upload video + subtitles |
| `/films/play/<id>/` | Video player |
| `/accounts/` | django-allauth (Google OAuth) |
| `/admin/` | Django admin |

---

## NLP & CEFR Analysis

Subtitle analysis lives primarily under `resurs_for_films/`:

- **`analyzer.py`** — `TextAnalyzer` tokenizes text, estimates per-word CEFR levels via a Gensim Word2Vec model (`word2vec_model.kv` in the project root), and returns level distribution and key sentences.
- **`subtit.py`** — Parses `.srt` files with `pysrt` and wraps the analyzer for film subtitles.
- **`automation.py`** — `MovieAutomation` ties together TMDB lookup, translation, and CEFR word lists (expects a `DATASET-CEFR/datasets/word_list_cefr.csv` dataset when present).

The `example_subtitle/` folder contains standalone experiments (`subtitle-cefr-example.py`, `srt_to_vtt.py`) for prototyping CEFR classification with Word2Vec and scikit-learn.

To use Word2Vec analysis, generate or place `word2vec_model.kv` in the project root (see `example_subtitle/subtitle-cefr-example.py` for a download/train workflow).

---

## Configuration Highlights

| Setting | Purpose |
|---------|---------|
| `AUTH_USER_MODEL` | `user.CustomUser` (email as username) |
| `MEDIA_ROOT` / `MEDIA_URL` | User-uploaded videos and subtitles |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | Large uploads (10 GB limit) |
| `CRISPY_TEMPLATE_PACK` | Bootstrap 5 forms |

---

## Development Status

This repository is under active development. Be aware of the following:

- **CEFR fields** on `Film` were added in migrations then removed; some templates (e.g. `film_detail.html`) may still reference removed fields.
- **`FilmProgress`** is referenced in `user/views.py` but is not defined in current models — profile statistics may error until restored or views are updated.
- **`translation/views.py`** references a `Video` model that does not match `films.Film`; wire-up is incomplete.
- **`/films/api/translate/dual/`** is called from `static/js/subtitles.js` but may not be implemented in `films/urls.py`.
- **`mfa_setup`** view exists but may need a URL route in `user/urls.py`.
- **`learning/`** templates exist without a dedicated Django app in `INSTALLED_APPS`.

Contributions to align models, URLs, and templates are welcome.

---

## Testing

```bash
python manage.py test
```

Run app-specific tests (e.g. `translation/tests.py`) as they are added.

---

## Deployment Checklist

- [ ] Set `DEBUG=False` and a strong `DJANGO_SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` and HTTPS (HSTS settings are partially enabled in `settings.py`)
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Serve media via nginx/S3; run `collectstatic`
- [ ] Run Celery workers and Redis in production
- [ ] Store secrets only in environment variables or a secrets manager
- [ ] Add `media/`, `db.sqlite3`, `tmp/`, `debug.log`, and `venv/` to `.gitignore`

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

Please follow existing code style and keep changes focused.

---

## License

This project does not include a `LICENSE` file yet. Add one (e.g. MIT) before public distribution if you intend open-source release.

---

## Acknowledgments

- [CEFR](https://www.coe.int/en/web/common-european-framework-reference-languages) framework for language proficiency levels
- [django-allauth](https://www.intenct.nl/projects/django-allauth/) for social authentication
- [Plyr](https://plyr.io/) for the video player UI
- [spaCy](https://spacy.io/) and [Gensim](https://radimrehurek.com/gensim/) for NLP

---

**MasterTeach** — *Learn languages naturally, one film at a time.*
