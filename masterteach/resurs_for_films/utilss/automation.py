import os
import csv
import requests
from typing import Dict, List, Tuple
import spacy
import nltk
from langdetect import detect
from googletrans import Translator
from django.conf import settings
import pandas as pd
from collections import Counter
import pysrt

# Download required NLTK data
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

class MovieAutomation:
    def __init__(self):
        self.tmdb_api_key = settings.TMDB_API_KEY   
        self.tmdb_base_url = 'https://api.themoviedb.org/3'
        self.nlp = spacy.load('en_core_web_sm')
        self.translator = Translator()
        
        # Load CEFR word lists
        self.cefr_word_lists = self._load_cefr_word_lists()
        
    def _load_cefr_word_lists(self) -> Dict[str, set]:
        """Load CEFR word lists from the dataset."""
        cefr_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        word_lists = {level: set() for level in cefr_levels}
        
        # Load the main CEFR word list
        cefr_file = os.path.join(settings.BASE_DIR, 'DATASET-CEFR', 'datasets', 'word_list_cefr.csv')
        
        try:
            # Read CSV with semicolon separator
            df = pd.read_csv(cefr_file, sep=';', encoding='utf-8')
            
            # Process each row
            for _, row in df.iterrows():
                word = str(row['headword']).lower().strip()
                level = str(row['CEFR']).strip()
                
                # Skip empty or invalid entries
                if not word or not level or level not in cefr_levels:
                    continue
                    
                # Add word to appropriate level set
                word_lists[level].add(word)
                
        except Exception as e:
            print(f"Error loading CEFR word list: {e}")
            # Fallback to empty sets if loading fails
            return {level: set() for level in cefr_levels}
            
        return word_lists

    def fetch_movie_details(self, title: str) -> Dict:
        """Fetch movie details from TMDB API."""
        if not self.tmdb_api_key:
            raise ValueError("TMDB API key not found in environment variables")
            
        # Search for the movie
        search_url = f"{self.tmdb_base_url}/search/movie"
        params = {
            'api_key': self.tmdb_api_key,
            'query': title,
            'language': 'en-US'
        }
        
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        
        results = response.json()['results']
        if not results:
            return None
            
        # Get the first result
        movie_id = results[0]['id']
        
        # Get detailed movie information
        details_url = f"{self.tmdb_base_url}/movie/{movie_id}"
        params = {
            'api_key': self.tmdb_api_key,
            'language': 'en-US',
            'append_to_response': 'credits,videos'
        }
        
        response = requests.get(details_url, params=params)
        response.raise_for_status()
        
        movie_data = response.json()
        
        return {
            'title': movie_data['title'],
            'original_title': movie_data['original_title'],
            'release_date': movie_data['release_date'],
            'runtime': movie_data['runtime'],
            'overview': movie_data['overview'],
            'poster_path': f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}" if movie_data['poster_path'] else None,
            'director': next((crew['name'] for crew in movie_data['credits']['crew'] 
                            if crew['job'] == 'Director'), None),
            'cast': [cast['name'] for cast in movie_data['credits']['cast'][:5]],
            'genres': [genre['name'] for genre in movie_data['genres']],
            'trailer': next((video['key'] for video in movie_data['videos']['results'] 
                           if video['type'] == 'Trailer' and video['site'] == 'YouTube'), None)
        }

    def detect_cefr_level(self, text: str) -> Tuple[str, Dict[str, float]]:
        """
        Detect the CEFR level of a text based on vocabulary and sentence complexity.
        Returns the predicted level and confidence scores for each level.
        """
        # Tokenize and clean the text
        doc = self.nlp(text.lower())
        words = [token.text for token in doc if token.is_alpha]
        
        # Calculate word-level metrics
        word_counts = Counter(words)
        total_words = len(words)
        
        # Calculate CEFR level scores
        level_scores = {}
        for level, word_list in self.cefr_word_lists.items():
            # Calculate percentage of words from this CEFR level
            level_words = sum(word_counts[word] for word in word_list if word in word_counts)
            level_scores[level] = (level_words / total_words) * 100 if total_words > 0 else 0
            
        # Calculate sentence complexity
        sentences = nltk.sent_tokenize(text)
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        # Adjust scores based on sentence complexity
        complexity_factor = min(avg_sentence_length / 20, 1.0)  # Normalize to 0-1 range
        for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
            level_scores[level] *= (1 + complexity_factor * (ord(level[1]) - ord('1')) / 5)
            
        # Determine the predicted level
        predicted_level = max(level_scores.items(), key=lambda x: x[1])[0]
        
        return predicted_level, level_scores

    def analyze_vocabulary(self, text: str) -> Dict:
        """Analyze vocabulary in the text and return detailed statistics."""
        try:
            # Tokenize and clean the text
            doc = self.nlp(text.lower())
            words = [token.text for token in doc if token.is_alpha]
            
            # Calculate word frequencies
            word_freq = Counter(words)
            total_words = len(words)
            unique_words = len(set(words))
            
            # Analyze CEFR levels
            level_counts = {level: 0 for level in self.cefr_word_lists.keys()}
            level_words = {level: [] for level in self.cefr_word_lists.keys()}
            
            for word in words:
                for level, word_list in self.cefr_word_lists.items():
                    if word in word_list:
                        level_counts[level] += 1
                        level_words[level].append(word)
                        break
            
            # Calculate percentages
            level_percentages = {
                level: (count / total_words * 100) if total_words > 0 else 0
                for level, count in level_counts.items()
            }
            
            # Get unknown words (not in any CEFR level)
            known_words = set()
            for words in level_words.values():
                known_words.update(words)
            unknown_words = [word for word in set(words) if word not in known_words]
            
            return {
                'word_count': total_words,
                'unique_words': unique_words,
                'word_frequencies': dict(word_freq),
                'level_counts': level_counts,
                'level_percentages': level_percentages,
                'level_words': level_words,
                'unknown_words': unknown_words
            }
        except Exception as e:
            print(f"Error analyzing vocabulary: {e}")
            return {}

    def process_subtitle(self, subtitle_path: str) -> Dict:
        """
        Process a subtitle file to detect language and CEFR level.
        """
        try:
            # Validate file exists and is readable
            if not os.path.exists(subtitle_path):
                raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            subs = None
            
            for encoding in encodings:
                try:
                    subs = pysrt.open(subtitle_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                
            if not subs:
                raise ValueError("Could not decode subtitle file with any supported encoding")
            
            # Extract all text for language detection
            all_text = ' '.join([sub.text for sub in subs])
            
            # Detect language
            try:
                language = detect(all_text)
            except:
                language = 'en'  # Default to English if detection fails
            
            # If not English, translate to English
            translated_subs = []
            if language != 'en':
                for sub in subs:
                    try:
                        translation = self.translator.translate(sub.text, dest='en').text
                        translated_subs.append({
                            'start': sub.start,
                            'end': sub.end,
                            'original': sub.text,
                            'translated': translation
                        })
                    except Exception as e:
                        print(f"Translation error: {e}")
                        translated_subs.append({
                            'start': sub.start,
                            'end': sub.end,
                            'original': sub.text,
                            'translated': sub.text
                        })
                all_text = ' '.join([sub['translated'] for sub in translated_subs])
            else:
                translated_subs = [{
                    'start': sub.start,
                    'end': sub.end,
                    'original': sub.text,
                    'translated': sub.text
                } for sub in subs]
            
            # Detect CEFR level
            level, scores = self.detect_cefr_level(all_text)
            
            # Process vocabulary
            vocabulary_analysis = self.analyze_vocabulary(all_text)
            
            return {
                'original_language': language,
                'cefr_level': level,
                'confidence_scores': scores,
                'translated': language != 'en',
                'vocabulary_analysis': vocabulary_analysis,
                'total_lines': len(subs),
                'subtitle_lines': translated_subs
            }
        except Exception as e:
            print(f"Error processing subtitle: {e}")
            return None 