from django.db import models
from django.conf import settings
from films.models import Film
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_avatar_size(value):
    """Validate avatar file size (max 5MB)"""
    if value.size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError('Avatar file size must be no more than 5MB')

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='User',
        help_text='The user this profile belongs to'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
            validate_avatar_size
        ],
        verbose_name='Profile Picture',
        help_text='User profile picture (max 5MB, JPG/PNG only)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='When this profile was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='When this profile was last updated'
    )

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        # Delete old avatar file if it exists and is being replaced
        if self.pk:
            try:
                old_profile = Profile.objects.get(pk=self.pk)
                if old_profile.avatar and old_profile.avatar != self.avatar:
                    old_profile.avatar.delete(save=False)
            except Profile.DoesNotExist:
                pass
        super().save(*args, **kwargs)

class WatchedFilm(models.Model):
    CEFR_LEVELS = [
        ('A1', 'A1 - Beginner'),
        ('A2', 'A2 - Elementary'),
        ('B1', 'B1 - Intermediate'),
        ('B2', 'B2 - Upper Intermediate'),
        ('C1', 'C1 - Advanced'),
        ('C2', 'C2 - Mastery'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watched_films',
        verbose_name='User',
        help_text='The user who watched the film'
    )
    film = models.ForeignKey(
        Film,
        on_delete=models.CASCADE,
        related_name='watched_by',
        verbose_name='Film',
        help_text='The film that was watched'
    )
    watched_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Watched At',
        help_text='When the film was watched'
    )
    is_favorite = models.BooleanField(
        default=False,
        verbose_name='Is Favorite',
        help_text='Whether this film is marked as favorite'
    )
    cefr_level = models.CharField(
        max_length=2,
        choices=CEFR_LEVELS,
        verbose_name='CEFR Level',
        help_text='The CEFR level of the film'
    )

    class Meta:
        verbose_name = 'Watched Film'
        verbose_name_plural = 'Watched Films'
        ordering = ['-watched_at']
        unique_together = ['user', 'film']
        indexes = [
            models.Index(fields=['user', 'film']),
            models.Index(fields=['watched_at']),
            models.Index(fields=['cefr_level']),
        ]

    def __str__(self):
        return f"{self.user.username} watched {self.film.title}"

class CEFRStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cefr_stats',
        verbose_name='User',
        help_text='The user these stats belong to'
    )
    a1_count = models.PositiveIntegerField(
        default=0,
        verbose_name='A1 Films',
        help_text='Number of A1 level films watched'
    )
    a2_count = models.PositiveIntegerField(
        default=0,
        verbose_name='A2 Films',
        help_text='Number of A2 level films watched'
    )
    b1_count = models.PositiveIntegerField(
        default=0,
        verbose_name='B1 Films',
        help_text='Number of B1 level films watched'
    )
    b2_count = models.PositiveIntegerField(
        default=0,
        verbose_name='B2 Films',
        help_text='Number of B2 level films watched'
    )
    c1_count = models.PositiveIntegerField(
        default=0,
        verbose_name='C1 Films',
        help_text='Number of C1 level films watched'
    )
    c2_count = models.PositiveIntegerField(
        default=0,
        verbose_name='C2 Films',
        help_text='Number of C2 level films watched'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Updated',
        help_text='When these stats were last updated'
    )

    class Meta:
        verbose_name = 'CEFR Statistics'
        verbose_name_plural = 'CEFR Statistics'
        indexes = [
            models.Index(fields=['last_updated']),
        ]

    def __str__(self):
        return f"{self.user.username}'s CEFR statistics"

    def update_stats(self):
        """Update CEFR statistics based on watched films"""
        watched_films = WatchedFilm.objects.filter(user=self.user)
        self.a1_count = watched_films.filter(cefr_level='A1').count()
        self.a2_count = watched_films.filter(cefr_level='A2').count()
        self.b1_count = watched_films.filter(cefr_level='B1').count()
        self.b2_count = watched_films.filter(cefr_level='B2').count()
        self.c1_count = watched_films.filter(cefr_level='C1').count()
        self.c2_count = watched_films.filter(cefr_level='C2').count()
        self.save()
