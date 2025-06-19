from django.urls import path 
from . import views 
urlpatterns = [
    path("",views.home_view,name='home'),
    path("login",views.login_page,name='login'),
    path("logout",views.logout_page,name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('settings/', views.user_settings, name='user_settings'),
    path("signup",views.signup_view,name='signup'),
    path('verify_mfa/', views.verify_mfa, name='verify_mfa'),
    path('disable-2fa/', views.disable_mfa, name='disable_2fa'),

]