import re
import pysrt
from collections import defaultdict
import logging
import csv
from functools import lru_cache
import os
from django.conf import settings
from cefrpy import CEFRAnalyzer as CEFRPyAnalyzer

logger = logging.getLogger(__name__)

class CEFRAnalyzer:
    _cefr_db = None  # Class-level cache for CEFR database
    _cefrpy_analyzer = None  # Class-level cache for CEFRPy analyzer

    def __init__(self):
        if CEFRAnalyzer._cefr_db is None:
            CEFRAnalyzer._cefr_db = self._load_cefr_base()
        if CEFRAnalyzer._cefrpy_analyzer is None:
            CEFRAnalyzer._cefrpy_analyzer = CEFRPyAnalyzer()
        self.cefr_db = CEFRAnalyzer._cefr_db
        self.cefrpy_analyzer = CEFRAnalyzer._cefrpy_analyzer
        self.vocabulary = defaultdict(dict)
        self.word_frequencies = defaultdict(int)
        self.key_sentences = []

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_cefr_base():
        """Load base CEFR vocabulary from cefr_mega_dataset.csv with full word information"""
        cefr_dict = {}
        try:
            # Look for the CSV file in multiple locations
            possible_paths = [
                'cefr_mega_dataset.csv',
                os.path.join(settings.BASE_DIR, 'cefr_mega_dataset.csv'),
                os.path.join(settings.BASE_DIR, 'DATASET-CEFR', 'datasets', 'cefr_mega_dataset.csv'),
                os.path.join(settings.BASE_DIR, 'DATASET-CEFR', 'datasets', 'word_list_cefr.csv')
            ]
            
            csv_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    csv_path = path
                    break
            
            if not csv_path:
                logger.error("❌ CEFR dataset not found in any of the expected locations")
                return {}
            
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    word = row['Word'].strip().lower() if 'Word' in row else row['headword'].strip().lower()
                    if not word:
                        continue
                    
                    cefr_dict[word] = {
                        'level': row['CEFR'].strip().upper(),
                        'definition': row.get('Definition', '').strip(),
                        'synonyms': [syn.strip() for syn in row.get('Synonyms', '').split(',')] if row.get('Synonyms') else []
                    }
            logger.info(f"✅ CEFR dataset loaded successfully with {len(cefr_dict)} words")
        except Exception as e:
            logger.error(f"❌ Error loading CEFR dataset: {str(e)}")
        return cefr_dict

    def analyze_subtitle(self, subtitle_file):
        """Analyze subtitle file using vocabulary-based approach"""
        try:
            subs = pysrt.open(subtitle_file)
            all_text = ' '.join([sub.text for sub in subs])
            
            # Extract key sentences
            self._extract_key_sentences(all_text)
            
            # Analyze words
            for sub in subs:
                for sentence in sub.text.split('.'):
                    self._process_sentence(sentence.strip())
            
            return self._generate_report()
        except Exception as e:
            logger.error(f"❌ Error analyzing subtitle: {str(e)}")
            return None

    def _extract_key_sentences(self, text):
        """Extract key sentences based on vocabulary level"""
        try:
            sentences = re.split(r'[.!?]', text)
            sentence_scores = []
            
            for sent in sentences:
                if not sent.strip():
                    continue
                    
                score = 0
                word_count = 0
                for word in sent.split():
                    word_count += 1
                    level = self._get_word_level(word)
                    if level in ['B2', 'C1', 'C2']:
                        score += 2
                    elif level in ['B1']:
                        score += 1
                
                if word_count > 0:
                    normalized_score = score / word_count
                    sentence_scores.append((sent, normalized_score))
            
            self.key_sentences = [s[0] for s in sorted(sentence_scores, 
                                                     key=lambda x: x[1], 
                                                     reverse=True)[:5]]
        except Exception as e:
            logger.error(f"❌ Error extracting key sentences: {str(e)}")
            self.key_sentences = []

    def _get_word_level(self, word):
        """Get CEFR level for a word from the vocabulary database or cefrpy"""
        word = word.lower()
        
        # First try our database
        if word in self.cefr_db:
            return self.cefr_db[word]['level']
            
        # If not found, try cefrpy
        try:
            level_float = self.cefrpy_analyzer.get_average_word_level_float(word)
            if level_float is not None:
                # Convert float level to CEFR level
                if level_float >= 5.5:
                    return 'C2'
                elif level_float >= 4.5:
                    return 'C1'
                elif level_float >= 3.5:
                    return 'B2'
                elif level_float >= 2.5:
                    return 'B1'
                elif level_float >= 1.5:
                    return 'A2'
                else:
                    return 'A1'
        except Exception as e:
            logger.debug(f"Could not get CEFR level from cefrpy for word '{word}': {str(e)}")
            
        return 'A1'  # Default to A1 if word not found

    def _process_sentence(self, sentence):
        """Process each sentence with improved word extraction"""
        try:
            # Improved regex to handle contractions and apostrophes
            words = re.findall(r'\b[\w\']+\b', sentence.lower())
            
            for word in words:
                if len(word) < 2:
                    continue
                    
                self.word_frequencies[word] += 1
                
                # Get word level and store in vocabulary
                level = self._get_word_level(word)
                if word not in self.vocabulary:
                    self.vocabulary[word] = {
                        'level': level,
                        'definition': self.cefr_db.get(word, {}).get('definition', ''),
                        'synonyms': self.cefr_db.get(word, {}).get('synonyms', [])
                    }
        except Exception as e:
            logger.error(f"❌ Error processing sentence: {str(e)}")

    def _generate_report(self):
        """Generate analysis report with enhanced vocabulary information"""
        try:
            level_order = ['C2', 'C1', 'B2', 'B1', 'A2', 'A1']
            
            # Count words per level
            level_counts = defaultdict(int)
            for word_info in self.vocabulary.values():
                level_counts[word_info['level']] += 1

            # Determine overall level based on highest level present
            overall_level = 'A1'
            for level in level_order:
                if level_counts[level] > 0:
                    overall_level = level
                    break

            # Count duplicate words
            duplicate_count = sum(1 for word, count in self.word_frequencies.items() if count > 1)

            # Prepare vocabulary details
            vocabulary_details = {
                word: {
                    'level': info['level'],
                    'definition': info['definition'],
                    'synonyms': info['synonyms'],
                    'frequency': self.word_frequencies[word]
                }
                for word, info in self.vocabulary.items()
            }

            return {
                'overall_level': overall_level,
                'level_distribution': dict(level_counts),
                'duplicate_words_count': duplicate_count,
                'vocabulary_size': len(self.vocabulary),
                'unique_words_count': len(set(self.vocabulary.keys())),
                'key_sentences': self.key_sentences,
                'vocabulary_details': vocabulary_details
            }
        except Exception as e:
            logger.error(f"❌ Error generating report: {str(e)}")
            return None

    def get_word_contexts(self, subtitle_file, target_word):
        """
        Get all sentences containing the target word from the subtitle file.
        Returns a list of contexts with sentence text and timestamps.
        """
        try:
            subs = pysrt.open(subtitle_file)
            contexts = []
            
            for sub in subs:
                if target_word.lower() in sub.text.lower():
                    # Convert subtitle time to seconds
                    start_time = sub.start.ordinal / 1000  # Convert to seconds
                    end_time = sub.end.ordinal / 1000      # Convert to seconds
                    
                    contexts.append({
                        'sentence': sub.text,
                        'start_time': start_time,
                        'end_time': end_time,
                        'start_time_formatted': str(sub.start),
                        'end_time_formatted': str(sub.end)
                    })
            
            return contexts
        except Exception as e:
            logger.error(f"Error getting word contexts: {str(e)}")
            return [] 