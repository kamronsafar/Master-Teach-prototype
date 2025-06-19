from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Prefetch
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.conf import settings
from .models import Profile, WatchedFilm
from .forms import ProfileForm
from films.models import Film
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

@login_required
def profile_list(request):
    """
    View all profiles with pagination and caching.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with paginated profiles
    """
    cache_key = f'profile_list_page_{request.GET.get("page", 1)}'
    cached_result = cache.get(cache_key)
    
    if cached_result:
        return cached_result
        
    profiles = Profile.objects.select_related('user').prefetch_related(
        Prefetch('user__watched_films', queryset=WatchedFilm.objects.select_related('film'))
    )
    
    paginator = Paginator(profiles, 12)  # Show 12 profiles per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    response = render(request, 'profiles/profile_list.html', {
        'page_obj': page_obj,
        'profiles': page_obj,
    })
    
    cache.set(cache_key, response, 300)  # Cache for 5 minutes
    return response

@login_required
def profile_view(request, username):
    """
    View a specific user's profile.
    
    Args:
        request: The HTTP request object
        username: The username of the profile to view
        
    Returns:
        Rendered template with profile details
        
    Raises:
        Http404: If the user or profile doesn't exist
    """
    try:
        user = User.objects.select_related('profile').get(username=username)
        profile = user.profile
    except (User.DoesNotExist, Profile.DoesNotExist):
        raise Http404("Profile not found")
        
    user_progress = WatchedFilm.objects.filter(user=user).select_related('film')
    
    # Calculate progress for each film
    for progress in user_progress:
        total_words = progress.film.words.count()
        learned_words = len(progress.words_learned)
        progress.percentage = int((learned_words / total_words * 100) if total_words > 0 else 0)
    
    context = {
        'profile_user': user,
        'profile': profile,
        'user_progress': user_progress,
    }
    return render(request, 'profiles/profile_detail.html', context)

@login_required
def profile_edit(request):
    """
    Edit the current user's profile.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with profile edit form
        
    Raises:
        PermissionDenied: If user tries to edit another user's profile
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profiles:profile_view', username=request.user.username)
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
    else:
        form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'profiles/profile_edit.html', {'form': form})

@login_required
def learning_progress(request):
    """
    View the current user's learning progress.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with learning progress
    """
    progress = WatchedFilm.objects.filter(user=request.user).select_related('film')
    
    # Calculate progress for each film
    for p in progress:
        total_words = p.film.words.count()
        learned_words = len(p.words_learned)
        p.percentage = int((learned_words / total_words * 100) if total_words > 0 else 0)
    
    return render(request, 'profiles/learning_progress.html', {'progress': progress})
