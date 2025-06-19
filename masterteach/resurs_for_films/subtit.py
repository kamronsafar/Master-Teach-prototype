import os
import re
import pysrt
import logging
from .analyzer import get_analyzer, analyze_text

logger = logging.getLogger(__name__)

class Word2VecSRTAnalyzer:
    def __init__(self):
        self.analyzer = get_analyzer()
        self.key_sentences = []

    def load_word2vec_model(self):
        """Load the Word2Vec model"""
        try:
            self.analyzer.load_model()
            logger.info("Word2Vec model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Word2Vec model: {str(e)}")
            raise

    def analyze_srt(self, file_path):
        """Analyze SRT file and return analysis results"""
        try:
            # Load and parse SRT file
            subs = pysrt.open(file_path)
            all_text = ' '.join([sub.text for sub in subs])
            
            # Analyze text using the analyzer
            analysis_result = analyze_text(all_text)
            
            # Extract key sentences
            self.key_sentences = analysis_result.get('key_sentences', [])
            
            return {
                'overall_level': analysis_result['overall_level'],
                'level_distribution': analysis_result['level_distribution'],
                'vocabulary_detailed': analysis_result['vocabulary_data'],
                'duplicate_words_count': analysis_result['vocabulary_count'] - analysis_result['unique_words_count']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing SRT file: {str(e)}")
            return {
                'overall_level': 'Unknown',
                'level_distribution': {},
                'vocabulary_detailed': {},
                'duplicate_words_count': 0
            }

# Global analyzer singleton
_global_analyzer = None

def get_global_analyzer():
    """Get or create the global analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = Word2VecSRTAnalyzer()
        _global_analyzer.load_word2vec_model()
    return _global_analyzer

if __name__ == "__main__":
    # Example usage
    analyzer = get_global_analyzer()
    srt_path = input("Enter SRT file path: ")
    results = analyzer.analyze_srt(srt_path)
    
    print(f"Overall Level: {results['overall_level']}")
    print("\nLevel Distribution:")
    for level, count in results['level_distribution'].items():
        print(f"{level}: {count} words")
    print(f"\nDuplicate Words Count: {results['duplicate_words_count']}")
    print("\nVocabulary and CEFR Levels:")
    for word, level in results['vocabulary_detailed'].items():
        print(f"{word} → {level}")

