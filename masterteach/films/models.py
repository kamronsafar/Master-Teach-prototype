from django.db import models
from django.conf import settings
import os
from .utils import CEFRAnalyzer
import logging
import requests
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

def convert_srt_to_vtt(srt_path, vtt_path):
    # Try different encodings
    encodings = ['utf-8', 'utf-16', 'windows-1251', 'cp1251']
    
    for encoding in encodings:
        try:
            with open(srt_path, 'r', encoding=encoding) as srt_file:
                srt_content = srt_file.read()
            
            vtt_content = "WEBVTT\n\n" + srt_content.replace(',', '.')
            
            with open(vtt_path, 'w', encoding='utf-8') as vtt_file:
                vtt_file.write(vtt_content)
            return
        except UnicodeDecodeError:
            continue
    
    # If all encodings fail, raise an error
    raise ValueError(f"Could not decode subtitle file with any of the attempted encodings: {encodings}")

class Vocabulary(models.Model):
    CEFR_LEVELS = [
        ('A1', 'Beginner'),
        ('A2', 'Elementary'),
        ('B1', 'Intermediate'),
        ('B2', 'Upper Intermediate'),
        ('C1', 'Advanced'),
        ('C2', 'Mastery'),
    ]

    word = models.CharField(max_length=100, unique=True)
    cefr_level = models.CharField(max_length=2, choices=CEFR_LEVELS)
    definition = models.TextField()
    synonyms = models.JSONField(default=list)
    antonyms = models.JSONField(default=list)
    examples = models.JSONField(default=list)
    part_of_speech = models.CharField(max_length=20, null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    difficulty_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.word} ({self.cefr_level})"

    class Meta:
        verbose_name_plural = "Vocabularies"
        ordering = ['word']
        indexes = [
            models.Index(fields=['word']),
            models.Index(fields=['cefr_level']),
            models.Index(fields=['usage_count']),
        ]

    def get_absolute_url(self):
        return reverse('films:vocabulary_detail', args=[str(self.id)])

    def update_usage_count(self):
        self.usage_count = FilmVocabulary.objects.filter(vocabulary=self).count()
        self.save(update_fields=['usage_count'])

class FilmVocabulary(models.Model):
    film = models.ForeignKey('Film', on_delete=models.CASCADE, related_name='vocabularies')
    vocabulary = models.ForeignKey(Vocabulary, on_delete=models.CASCADE)
    frequency = models.IntegerField(default=1)
    first_occurrence = models.CharField(max_length=200, null=True, blank=True)
    timestamps = models.JSONField(default=list)
    context_sentences = models.JSONField(default=list)

    class Meta:
        unique_together = ['film', 'vocabulary']
        verbose_name_plural = "Film Vocabularies"
        indexes = [
            models.Index(fields=['film', 'vocabulary']),
            models.Index(fields=['frequency']),
        ]

    def update_frequency(self):
        self.frequency = len(self.timestamps)
        self.save(update_fields=['frequency'])

class FilmWatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='film_watches')
    film = models.ForeignKey('Film', on_delete=models.CASCADE, related_name='watches')
    watched_at = models.DateTimeField(auto_now_add=True)
    watch_duration = models.IntegerField(default=0)  # Duration in seconds

    class Meta:
        ordering = ['-watched_at']
        indexes = [
            models.Index(fields=['user', 'film']),
            models.Index(fields=['watched_at']),
        ]

    def __str__(self):
        return f"{self.user.username} watched {self.film.title}"

class Film(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('requested', 'Requested'),
        ('processing', 'Processing'),
        ('ready', 'Ready')
    ]
    
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='videos/')
    english_subtitle = models.FileField(upload_to='subtitles/english/')
    russian_subtitle = models.FileField(upload_to='subtitles/russian/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='requested')
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='allowed_films',
        blank=True,
        help_text='Users who can view this film'
    )
    
    # Payment and delivery fields
    is_paid = models.BooleanField(default=False)
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='film_payments')
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    is_fast_delivery = models.BooleanField(default=False)
    
    # CEFR Analysis fields
    cefr_level = models.CharField(max_length=2, null=True, blank=True)
    vocabulary_size = models.IntegerField(default=0)
    unique_words_count = models.IntegerField(default=0)
    level_distribution = models.JSONField(null=True, blank=True)
    key_sentences = models.JSONField(null=True, blank=True)
    vocabulary_details = models.JSONField(null=True, blank=True)  # Store detailed vocabulary analysis

    thumbnail = models.ImageField(
        upload_to='thumbnails/',
        null=True,
        blank=True,
        help_text='Upload a thumbnail image for the film'
    )

     # TMDB fields
    tmdb_id = models.IntegerField(null=True, blank=True, unique=True)
    tmdb_poster_path = models.CharField(max_length=200, blank=True)
    tmdb_backdrop_path = models.CharField(max_length=200, blank=True)
    tmdb_release_date = models.DateField(null=True, blank=True)
    tmdb_vote_average = models.FloatField(null=True, blank=True)
    tmdb_genres = models.JSONField(null=True, blank=True)
    tmdb_overview = models.TextField(blank=True)
    tmdb_runtime = models.IntegerField(null=True, blank=True)
    tmdb_original_title = models.CharField(max_length=200, blank=True)
    tmdb_original_language = models.CharField(max_length=10, blank=True)
    tmdb_popularity = models.FloatField(null=True, blank=True)
    tmdb_vote_count = models.IntegerField(null=True, blank=True)
    tmdb_tagline = models.CharField(max_length=200, blank=True)
    tmdb_status = models.CharField(max_length=20, blank=True)
    tmdb_budget = models.BigIntegerField(null=True, blank=True)
    tmdb_revenue = models.BigIntegerField(null=True, blank=True)
    tmdb_homepage = models.URLField(blank=True)
    tmdb_imdb_id = models.CharField(max_length=20, blank=True)
    tmdb_production_companies = models.JSONField(default=list, blank=True)
    tmdb_production_countries = models.JSONField(default=list, blank=True)
    tmdb_spoken_languages = models.JSONField(default=list, blank=True)
    
    def get_tmdb_poster_url(self):
        if self.tmdb_poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.tmdb_poster_path}"
        return None

    def get_tmdb_backdrop_url(self):
        if self.tmdb_backdrop_path:
            return f"https://image.tmdb.org/t/p/original{self.tmdb_backdrop_path}"
        return None

    def update_from_tmdb(self, tmdb_id=None):
        if not tmdb_id and not self.tmdb_id:
            return False
            
        tmdb_id = tmdb_id or self.tmdb_id
        api_key = settings.TMDB_API_KEY
        base_url = "https://api.themoviedb.org/3"
        
        try:
            # Get movie details
            response = requests.get(
                f"{base_url}/movie/{tmdb_id}",
                params={"api_key": api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            # Update all TMDB fields
            self.tmdb_id = data.get('id')
            self.tmdb_poster_path = data.get('poster_path')
            self.tmdb_backdrop_path = data.get('backdrop_path')
            self.tmdb_release_date = data.get('release_date')
            self.tmdb_vote_average = data.get('vote_average')
            self.tmdb_genres = [genre['name'] for genre in data.get('genres', [])]
            self.tmdb_overview = data.get('overview')
            self.tmdb_runtime = data.get('runtime')
            self.tmdb_original_title = data.get('original_title')
            self.tmdb_original_language = data.get('original_language')
            self.tmdb_popularity = data.get('popularity')
            self.tmdb_vote_count = data.get('vote_count')
            self.tmdb_tagline = data.get('tagline')
            self.tmdb_status = data.get('status')
            self.tmdb_budget = data.get('budget')
            self.tmdb_revenue = data.get('revenue')
            self.tmdb_homepage = data.get('homepage')
            self.tmdb_imdb_id = data.get('imdb_id')
            self.tmdb_production_companies = data.get('production_companies')
            self.tmdb_production_countries = data.get('production_countries')
            self.tmdb_spoken_languages = data.get('spoken_languages')
            
            # Update basic film info
            self.title = data.get('title', self.title)
            
            self.save()
            return True
        except Exception as e:
            logger.error(f"Error updating film from TMDB: {str(e)}")
            return False

    @staticmethod
    def search_tmdb(query):
        api_key = settings.TMDB_API_KEY
        base_url = "https://api.themoviedb.org/3"
        
        try:
            response = requests.get(
                f"{base_url}/search/movie",
                params={
                    "api_key": api_key,
                    "query": query,
                    "language": "en-US",
                    "include_adult": False
                }
            )
            response.raise_for_status()
            results = response.json().get('results', [])
            
            # Format results for frontend
            formatted_results = []
            for movie in results:
                formatted_results.append({
                    'id': movie.get('id'),
                    'title': movie.get('title'),
                    'release_date': movie.get('release_date'),
                    'poster_path': f"https://image.tmdb.org/t/p/w200{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    'overview': movie.get('overview'),
                    'vote_average': movie.get('vote_average'),
                    'genres': []  # Will be populated when movie is selected
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching TMDB: {str(e)}")
            return []
        
    def save(self, *args, **kwargs):
        # First save to get the file path
        super().save(*args, **kwargs)
        
        # Convert English subtitle if it's SRT
        if self.english_subtitle.name.endswith('.srt'):
            srt_path = self.english_subtitle.path
            vtt_path = os.path.splitext(srt_path)[0] + '.vtt'
            convert_srt_to_vtt(srt_path, vtt_path)
            self.english_subtitle.name = os.path.splitext(self.english_subtitle.name)[0] + '.vtt'
        
        # Convert Russian subtitle if it's SRT
        if self.russian_subtitle.name.endswith('.srt'):
            srt_path = self.russian_subtitle.path
            vtt_path = os.path.splitext(srt_path)[0] + '.vtt'
            convert_srt_to_vtt(srt_path, vtt_path)
            self.russian_subtitle.name = os.path.splitext(self.russian_subtitle.name)[0] + '.vtt'
        
        # Analyze English subtitle for CEFR data
        if self.english_subtitle and not self.cefr_level:
            analyzer = CEFRAnalyzer()
            analysis = analyzer.analyze_subtitle(self.english_subtitle.path)
            
            if analysis:
                self.cefr_level = analysis['overall_level']
                self.vocabulary_size = analysis['vocabulary_size']
                self.unique_words_count = analysis['unique_words_count']
                self.level_distribution = analysis['level_distribution']
                self.key_sentences = analysis['key_sentences']
                self.vocabulary_details = analysis['vocabulary_details']
                
                # Save again to update the CEFR data
                super().save(*args, **kwargs)

    def add_allowed_user(self, user):
        """Add a user to the list of users who can view this film."""
        self.allowed_users.add(user)
        if self.visibility == 'requested':
            self.save()

    def remove_allowed_user(self, user):
        """Remove a user from the list of users who can view this film."""
        self.allowed_users.remove(user)
        if self.visibility == 'requested':
            self.save()

    def is_visible_to_user(self, user):
        """Check if a user can view this film."""
        if self.visibility == 'public':
            return True
        return user in self.allowed_users.all()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-uploaded_at'] 

    def can_user_watch(self, user):
        """
        Check if a user can watch this film based on their subscription status and viewing history
        """
        # Premium users can watch any film
        if hasattr(user, 'premiumsubscription') and user.premiumsubscription.is_active:
            return True

        # If film is public and not paid, check viewing limits
        if self.visibility == 'public' and not self.is_paid:
            # Get user's last watch
            last_watch = FilmWatch.objects.filter(
                user=user,
                watched_at__gte=timezone.now() - timedelta(days=3)
            ).order_by('-watched_at').first()
            
            # If no watch in last 3 days, user can watch
            return last_watch is None

        # For paid films, check if user has paid
        if self.is_paid:
            return self.payment and self.payment.user == user and self.payment.status == 'completed'

        # For requested films, check if user is allowed
        return user in self.allowed_users.all()

    def record_watch(self, user, duration=0):
        """
        Record a user watching this film
        """
        FilmWatch.objects.create(
            user=user,
            film=self,
            watch_duration=duration
        )

    def get_user_watch_history(self, user):
        """
        Get a user's watch history for this film
        """
        return FilmWatch.objects.filter(
            user=user,
            film=self
        ).order_by('-watched_at')

    def get_next_available_time(self, user):
        """
        Get the next time a free user can watch this film
        """
        if hasattr(user, 'premiumsubscription') and user.premiumsubscription.is_active:
            return None

        last_watch = FilmWatch.objects.filter(
            user=user,
            watched_at__gte=timezone.now() - timedelta(days=3)
        ).order_by('-watched_at').first()

        if last_watch:
            return last_watch.watched_at + timedelta(days=3)
        return None

class FilmRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('processing', 'Processing'),
        ('ready', 'Ready')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='film_requests')
    title = models.CharField(max_length=255, default='Untitled Request')
    tmdb_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    # Payment and delivery fields
    is_paid = models.BooleanField(default=False)
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='request_payments')
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    is_fast_delivery = models.BooleanField(default=False)
    
    # Film reference after completion
    completed_film = models.ForeignKey(Film, on_delete=models.SET_NULL, null=True, blank=True, related_name='request')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def update_status(self, new_status):
        self.status = new_status
        self.save()
        
        # Create notification for status update
        Notification.objects.create(
            user=self.user,
            notification_type='request_status',
            title='Film Request Status Update',
            message=f'Your request for "{self.title}" has been {new_status}.',
            film_request=self
        )

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('film_request', 'Film Request'),
        ('request_status', 'Request Status Update'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    film_request = models.ForeignKey(FilmRequest, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.title}"

    @classmethod
    def create_film_request_notification(cls, film_request):
        """Create notifications for superusers when a new film request is made"""
        superusers = get_user_model().objects.filter(is_superuser=True)
        for superuser in superusers:
            cls.objects.create(
                user=superuser,
                notification_type='film_request',
                title='New Film Request',
                message=f'User {film_request.user.email} has requested the film: {film_request.title}',
                film_request=film_request
            ) 