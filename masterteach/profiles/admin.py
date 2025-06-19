from django.contrib import admin

# Register your models here.
from .models import Profile, WatchedFilm, CEFRStats

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(WatchedFilm)
class WatchedFilmAdmin(admin.ModelAdmin):
    list_display = ('user', 'film', 'watched_at', 'is_favorite', 'cefr_level')
    search_fields = ('user__username', 'film__title')
    list_filter = ('is_favorite', 'cefr_level', 'watched_at')
    readonly_fields = ('watched_at',)

@admin.register(CEFRStats)
class CEFRStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'a1_count', 'a2_count', 'b1_count', 'b2_count', 'c1_count', 'c2_count', 'last_updated')
    search_fields = ('user__username',)
    readonly_fields = ('last_updated',)
