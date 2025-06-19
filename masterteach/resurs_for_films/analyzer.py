import logging
from gensim.models import KeyedVectors
import os
from django.conf import settings
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class TextAnalyzer:
    def __init__(self):
        self.model = None
        self.stop_words = set(stopwords.words('english'))
        self.cefr_levels = {
            'A1': 0.2,
            'A2': 0.4,
            'B1': 0.6,
            'B2': 0.7,
            'C1': 0.8,
            'C2': 0.9
        }
        
    def load_model(self):
        """Load the Word2Vec model"""
        if self.model is None:
            try:
                model_path = os.path.join(settings.BASE_DIR, 'word2vec_model.kv')
                if os.path.exists(model_path):
                    self.model = KeyedVectors.load(model_path)
                    logger.info("Word2Vec model loaded successfully")
                else:
                    logger.error(f"Word2Vec model not found at {model_path}")
            except Exception as e:
                logger.error(f"Error loading Word2Vec model: {str(e)}")
                raise

    def preprocess_text(self, text):
        """Preprocess text for analysis"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords
        tokens = [word for word in tokens if word not in self.stop_words]
        
        return tokens

    def get_word_level(self, word):
        """Determine CEFR level for a word based on its frequency in the model"""
        if not self.model or word not in self.model:
            return 'A1'  # Default to A1 if word not found
            
        try:
            # Get word frequency (inverse of rank)
            word_rank = self.model.get_vecattr(word, "count")
            max_rank = max(self.model.get_vecattr(w, "count") for w in self.model.index_to_key)
            frequency = word_rank / max_rank
            
            # Map frequency to CEFR level
            for level, threshold in sorted(self.cefr_levels.items(), key=lambda x: x[1]):
                if frequency >= threshold:
                    return level
            return 'A1'
        except Exception as e:
            logger.error(f"Error determining word level for {word}: {str(e)}")
            return 'A1'

    def analyze_text(self, text):
        """Analyze text and return CEFR level information"""
        try:
            self.load_model()
            
            # Preprocess text
            tokens = self.preprocess_text(text)
            
            # Get unique words
            unique_words = set(tokens)
            
            # Analyze each word
            word_levels = {}
            level_distribution = {level: 0 for level in self.cefr_levels.keys()}
            
            for word in unique_words:
                level = self.get_word_level(word)
                word_levels[word] = level
                level_distribution[level] += 1
            
            # Calculate overall level
            total_words = len(unique_words)
            if total_words > 0:
                level_scores = {level: count/total_words for level, count in level_distribution.items()}
                overall_level = max(level_scores.items(), key=lambda x: x[1])[0]
            else:
                overall_level = 'A1'
            
            # Get key sentences (sentences with words from higher CEFR levels)
            sentences = nltk.sent_tokenize(text)
            key_sentences = []
            for sentence in sentences:
                sentence_tokens = self.preprocess_text(sentence)
                sentence_levels = [self.get_word_level(word) for word in sentence_tokens if word in self.model]
                if sentence_levels and max(sentence_levels) in ['B2', 'C1', 'C2']:
                    key_sentences.append(sentence)
            
            return {
                'overall_level': overall_level,
                'level_distribution': level_distribution,
                'vocabulary_data': word_levels,
                'key_sentences': key_sentences[:5],  # Return top 5 key sentences
                'vocabulary_count': len(tokens),
                'unique_words_count': len(unique_words)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text: {str(e)}")
            return {
                'overall_level': 'A1',
                'level_distribution': {'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0},
                'vocabulary_data': {},
                'key_sentences': [],
                'vocabulary_count': 0,
                'unique_words_count': 0
            }

# Create a global instance
_analyzer = None

def get_analyzer():
    """Get or create the global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TextAnalyzer()
    return _analyzer

def analyze_text(text):
    """Analyze text using the global analyzer instance"""
    analyzer = get_analyzer()
    return analyzer.analyze_text(text) 