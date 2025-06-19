from django.contrib import admin
from .models import Film, Vocabulary, FilmVocabulary

@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'cefr_level', 'vocabulary_size', 'unique_words_count', 'uploaded_at')
    search_fields = ('title',)
    list_filter = ('cefr_level', 'uploaded_at')

@admin.register(Vocabulary)
class VocabularyAdmin(admin.ModelAdmin):
    list_display = ('word', 'cefr_level', 'usage_count', 'created_at')
    search_fields = ('word', 'definition')
    list_filter = ('cefr_level', 'created_at')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')

@admin.register(FilmVocabulary)
class FilmVocabularyAdmin(admin.ModelAdmin):
    list_display = ('film', 'vocabulary', 'frequency', 'first_occurrence')
    search_fields = ('film__title', 'vocabulary__word')
    list_filter = ('vocabulary__cefr_level',)