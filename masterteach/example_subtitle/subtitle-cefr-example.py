import re
import pysrt
import gensim.downloader as api
from gensim.models import KeyedVectors
from collections import defaultdict
import numpy as np
from sklearn.neighbors import KNeighborsClassifier

class Word2VecSRTAnalyzer:
    def __init__(self):
        self.subs = []
        self.word_vectors = None
        self.cefr_model = None
        self.model_path = "GoogleNews-vectors-negative300.bin"
        self.cefr_db = self._load_cefr_base()
        self.vocabulary = defaultdict(set)
        self.word_frequencies = defaultdict(int)  # <<=== YANGI QATOR
        self.key_sentences = []


    def _load_cefr_base(self):
        """Asosiy CEFR ma'lumotlarini yuklash"""
        return {
            'hello': 'A1', 'goodbye': 'A1', 'please': 'A1', 
            'analyze': 'B2', 'sophisticated': 'C1', 'quantum': 'C2'
        }

    def load_word2vec_model(self):
   
        try:
            print("Model yuklanmoqda. Birinchi marta yuklash biroz vaqt oladi...")
            self.word_vectors = api.load("word2vec-google-news-300")
            self.word_vectors.save("word2vec_model.kv")
            self._train_cefr_classifier()
            print("✅ Word2Vec modeli muvaffaqiyatli yuklandi!")
        except Exception as e:
            print("❌ Modelni yuklashda xatolik yuz berdi:", str(e))


    def _train_cefr_classifier(self):
        """CEFR klassifikatorini o'qitish"""
        X = []
        y = []
        for word, level in self.cefr_db.items():
            try:
                X.append(self.word_vectors[word])
                y.append(level)
            except KeyError:
                continue
        
        if X:
            self.cefr_model = KNeighborsClassifier(n_neighbors=3)
            self.cefr_model.fit(X, y)

    def _predict_level(self, word):
        """Word2Vec asosida daraja taxmini"""
        try:

            vector = self.word_vectors[word]
            return self.cefr_model.predict([vector])[0]
        except KeyError:
            return 'Unknown'

    def analyze_srt(self, file_path):
        """SRT faylini tahlil qilish"""
        self.subs = pysrt.open(file_path)
        all_text = ' '.join([sub.text for sub in self.subs])
        
        # Asosiy jumlalarni aniqlash
        self._extract_key_sentences(all_text)
        
        # So'zlar tahlili
        for sub in self.subs:
            for sentence in sub.text.split('.'):
                self._process_sentence(sentence.strip())
        
        return self._generate_report()

    def _extract_key_sentences(self, text):
        """Muhim jumlalarni ajratib olish"""
        sentences = re.split(r'[.!?]', text)
        sentence_scores = []
        
        for sent in sentences:
            score = 0
            for word in sent.split():
                if self._predict_level(word) in ['B2', 'C1', 'C2']:
                    score += 1
            sentence_scores.append((sent, score))
        
        # Eng yuqori 5 ta jumlani tanlash
        self.key_sentences = [s[0] for s in sorted(sentence_scores, 
                                                 key=lambda x: x[1], 
                                                 reverse=True)[:5]]

    def _process_sentence(self, sentence):
        """Har bir jumlani qayta ishlash"""
        for word in re.findall(r'\b\w+\b', sentence.lower()):
            self.word_frequencies[word] += 1

            if word in self.cefr_db:
                level = self.cefr_db[word]
            else:
                level = self._predict_level(word)
            
            self.vocabulary[word] = level


    def _generate_report(self):
        """Hisobot yaratish"""
        level_order = ['C2', 'C1', 'B2', 'B1', 'A2', 'A1', 'Unknown']
        
        # Har bir darajaga tegishli so'zlar sonini hisoblash
        level_counts = defaultdict(int)
        for word, level in self.vocabulary.items():
            level_counts[level] += 1

        # Overall level aniqlash
        for level in level_order:
            if level_counts[level] > 0:
                overall_level = level
                break
        else:
            overall_level = 'Unknown'

        # Takror so'zlar soni
        duplicate_count = sum(1 for word, count in self.word_frequencies.items() if count > 1)

        return {
            'overall_level': overall_level,
            'level_distribution': dict(level_counts),
            'duplicate_words_count': duplicate_count,
            'vocabulary_detailed': self.vocabulary
        }


# Foydalanish misoli
if __name__ == "__main__":
    analyzer = Word2VecSRTAnalyzer()
    analyzer.load_word2vec_model()
    
    results = analyzer.analyze_srt(input("srt: "))
    
    
    print(f"Umumiy Daraja: {results['overall_level']}")
    print("Darajalar bo'yicha taqsimot:")
    for level, count in results['level_distribution'].items():
        print(f"{level}: {count} so'z")

    print(f"\n♻️ Takrorlangan so'zlar soni: {results['duplicate_words_count']}")

    print("\n📚 So'zlar va ularning CEFR darajalari:")
    for word, lvl in results['vocabulary_detailed'].items():
        print(f"{word} → {lvl}")
