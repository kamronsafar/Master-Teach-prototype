from django.urls import path
from . import views

app_name = 'films'

urlpatterns = [
    path('api/users/search/', views.search_users, name='search_users'),
    path('api/films/<int:film_id>/allowed-users/', views.save_allowed_users, name='save_allowed_users'),
    path('', views.film_list, name='film_list'),
    path('my-films/', views.my_films, name='my_films'),
    path('upload/', views.upload_video, name='upload_video'),
    path('edit/<int:film_id>/', views.edit_film, name='edit_film'),
    path('film/<int:film_id>/', views.film_detail, name='film_detail'),
    path('play/<int:film_id>/', views.play_video, name='play_video'),
    path('vocabulary/<int:film_id>/', views.film_vocabulary, name='film_vocabulary'),
    path('film/<int:film_id>/sentence-segment/', views.get_sentence_segment, name='get_sentence_segment'),
    path('search-tmdb/', views.search_tmdb, name='search_tmdb'),
    path('requests/create/', views.create_film_request, name='create_film_request'),
    path('requests/<int:request_id>/update-status/', views.update_film_request_status, name='update_film_request_status'),
    path('requests/<int:request_id>/link-film/', views.link_film_to_request, name='link_film_to_request'),
    path('request/', views.request_film, name='request_film'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('update-request/<int:request_id>/', views.update_request_status, name='update_request_status'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/unread-count/', views.get_unread_notification_count, name='get_unread_notification_count'),
] 