from django import forms
from .models import Film, FilmRequest
from django.contrib.auth import get_user_model

class VideoUploadForm(forms.ModelForm):
    tmdb_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for a movie on TMDB...',
            'id': 'id_tmdb_search'
        })
    )
    tmdb_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_tmdb_id'})
    )
    visibility = forms.ChoiceField(
        choices=Film.VISIBILITY_CHOICES,
        initial='requested',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    allowed_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'id': 'id_allowed_users'
        }),
        help_text='Select additional users who can view this film (you will be automatically added for requested films)'
    )

    class Meta:
        model = Film
        fields = ['title', 'video_file', 'english_subtitle', 'russian_subtitle', 'visibility', 'allowed_users']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_title'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.mp4'}),
            'english_subtitle': forms.FileInput(attrs={'class': 'form-control', 'accept': '.srt,.vtt'}),
            'russian_subtitle': forms.FileInput(attrs={'class': 'form-control', 'accept': '.srt,.vtt'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        allowed_users = cleaned_data.get('allowed_users', [])

        if visibility == 'requested':
            # For requested films, ensure the current user is in allowed_users
            if not allowed_users:
                allowed_users = []
            # We don't need to check uploaded_by here as it will be set in the view
            cleaned_data['allowed_users'] = allowed_users

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        tmdb_id = self.cleaned_data.get('tmdb_id')
        if tmdb_id:
            instance.tmdb_id = tmdb_id
            instance.update_from_tmdb(tmdb_id)
        if commit:
            instance.save()
            # Save many-to-many relationships
            self.save_m2m()
        return instance

class FilmRequestForm(forms.ModelForm):
    tmdb_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for a movie on TMDB...',
            'id': 'id_tmdb_search'
        })
    )
    tmdb_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_tmdb_id'})
    )

    class Meta:
        model = FilmRequest
        fields = ['title', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_title'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 