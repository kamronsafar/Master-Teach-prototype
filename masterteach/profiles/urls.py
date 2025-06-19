from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.profile_list, name='profile_list'),
    path('progress/', views.learning_progress, name='learning_progress'),
    path('edit/', views.profile_edit, name='profile_edit'),
    path('<str:username>/', views.profile_view, name='profile_view'),
] 