import io
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import pyotp
import qrcode
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.core.cache import cache
from django.utils import timezone
import os
import re
from profiles.models import Profile
from django.db import models

CustomUser = get_user_model()

def verify_2fa_otp(user, otp):
    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(otp):
        user.mfa_enabled = True
        user.save()
        return True
    return False

def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        raise ValidationError("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character")

@login_required
def home_view(request):
    return render(request, 'home.html')

@login_required
def profile_view(request):
    """View for displaying user profile"""
    try:
        # Get or create user profile
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Get user's learning statistics
        from films.models import FilmProgress
        progress_stats = FilmProgress.objects.filter(user=request.user).aggregate(
            total_watch_time=models.Sum('current_position'),
            total_films=models.Count('film', distinct=True),
            completed_films=models.Count('film', filter=models.Q(completed=True))
        )
        
        # Get recent activity
        recent_progress = FilmProgress.objects.filter(user=request.user).order_by('-last_watched')[:5]
        
        context = {
            'profile': profile,
            'progress_stats': progress_stats,
            'recent_progress': recent_progress
        }
        return render(request, 'user/profile.html', context)
    except Exception as e:
        messages.error(request, 'An error occurred while loading your profile')
        return redirect('home')

@login_required
def mfa_setup(request):
    """View for setting up MFA"""
    user = request.user
    if not user.mfa_secret:
        user.mfa_secret = pyotp.random_base32()
        user.save()

    otp_uri = pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
        name=user.email,
        issuer_name="masterteach"
    )

    qr = qrcode.make(otp_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    
    buffer.seek(0)  
    qr_code = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_code_data_uri = f"data:image/png;base64,{qr_code}"

    return render(request, 'user/mfa_setup.html', {
        'qr_code': qr_code_data_uri,
        'mfa_enabled': user.mfa_enabled
    })

@login_required
def verify_mfa(request):
    """Handle MFA verification"""
    if request.method == 'POST':
        code = request.POST.get('code')
        if not code:
            messages.error(request, 'Please enter the verification code')
            return redirect('mfa_setup')
            
        user = request.user
        totp = pyotp.TOTP(user.mfa_secret)
        
        if totp.verify(code):
            user.mfa_enabled = True
            user.save()
            messages.success(request, 'MFA has been enabled successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Invalid verification code')
            return redirect('mfa_setup')
            
    return redirect('mfa_setup')

@login_required
def disable_mfa(request):
    """Disable MFA for user"""
    if request.method == 'POST':
        user = request.user
        user.mfa_enabled = False
        user.mfa_secret = None
        user.save()
        messages.success(request, 'MFA has been disabled successfully!')
    return redirect('profile')

def login_page(request):
    # Check for too many login attempts
    ip_address = request.META.get('REMOTE_ADDR')
    cache_key = f'login_attempts_{ip_address}'
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 5:
        messages.error(request, 'Too many login attempts. Please try again later.')
        return render(request, 'user/login.html')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Reset login attempts on successful authentication
            cache.delete(cache_key)
            
            if user.mfa_enabled:
                return render(request, 'user/otp_verify.html', {'user_id': user.id})
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('profile') 
        else:
            # Increment failed login attempts
            cache.set(cache_key, attempts + 1, 300)  # 5 minutes timeout
            messages.error(request, 'Invalid email or password. Please try again.')
    return render(request, 'user/login.html')

@login_required
def logout_page(request):
    logout(request)  
    messages.success(request, 'You have been logged out successfully.') 
    return redirect('/')

def signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Check if passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match. Please try again.')
            return render(request, 'user/signup.html')

        # Validate password strength
        try:
            validate_password_strength(password1)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'user/signup.html')

        # Check if email is already taken
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email is already in use. Please try another.')
            return render(request, 'user/signup.html')

        # Create the new user
        user = CustomUser.objects.create_user(username=email, email=email, password=password1)
        user.save()
        messages.success(request, 'Signup successful! You can now log in.')
        return redirect('login')

    return render(request, 'user/signup.html')

@login_required
def user_settings(request):
    """Handle user settings page and updates"""
    user = request.user
    
    if request.method == 'POST':
        # Handle form submission
        username = request.POST.get('username')
        email = request.POST.get('email')
        bio = request.POST.get('bio')
        
        # Update user information
        if username and username != user.username:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username is already taken.')
            else:
                user.username = username
                
        if email and email != user.email:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email is already in use.')
            else:
                user.email = email
                
        if bio is not None:
            user.bio = bio
            
        user.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('user_settings')
        
    return render(request, 'user/settings.html', {
        'user': user,
        'active_tab': 'settings'
    })

@login_required
def update_profile(request):
    """Handle profile updates"""
    if request.method == 'POST':
        try:
            user = request.user
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Update basic info
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            
            # Update profile info
            profile.bio = request.POST.get('bio', '')
            
            # Handle avatar upload
            if 'avatar' in request.FILES:
                avatar = request.FILES['avatar']
                profile.avatar = avatar
            
            # Validate email uniqueness
            if user.__class__.objects.exclude(pk=user.pk).filter(email=user.email).exists():
                raise ValidationError('Email already exists')
            
            # Validate username uniqueness
            if user.__class__.objects.exclude(pk=user.pk).filter(username=user.username).exists():
                raise ValidationError('Username already exists')
            
            user.save()
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'An error occurred while updating your profile')
    
    return redirect('profile')

