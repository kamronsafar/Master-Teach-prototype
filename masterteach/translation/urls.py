from django.urls import path
from .views import translate_view, get_supported_languages

urlpatterns = [
    path('api/translate/', translate_view),
    path('api/languages/', get_supported_languages),
]
