from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import VideoUploadForm, FilmRequestForm
from .models import Film, Vocabulary, FilmRequest, Notification, FilmWatch
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse, HttpResponse, FileResponse, HttpResponseForbidden
from django.conf import settings
import logging
import json
import os
import tempfile
import subprocess
import re
from django.template.loader import render_to_string
from django.db import models
from django.db.models import Q
import requests
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment, PremiumSubscription

logger = logging.getLogger(__name__)

def is_superuser(user):
    return user.is_superuser

@login_required
def film_list(request):
    if request.user.is_superuser:
        # Superusers see all films
        films = Film.objects.all().order_by('-uploaded_at')
    else:
        # For regular users, show public films and films they are allowed to view
        films = Film.objects.filter(
            models.Q(visibility='public') | 
            models.Q(allowed_users=request.user)
        ).distinct().order_by('-uploaded_at')
    return render(request, 'films/film_list.html', {'films': films})

@login_required
def film_detail(request, film_id):
    film = get_object_or_404(Film, id=film_id)
    
    # Get user's watch history
    watch_history = film.get_user_watch_history(request.user)
    
    # Check if user can watch
    can_watch = film.can_user_watch(request.user)
    next_available = None
    if not can_watch and film.visibility == 'public' and not film.is_paid:
        next_available = film.get_next_available_time(request.user)
    
    # Check if user has permission to view the film
    if not request.user.is_superuser and film.visibility == 'requested' and request.user not in film.allowed_users.all():
        messages.error(request, 'You do not have permission to view this film.')
        return redirect('films:film_list')
    
    context = {
        'film': film,
        'watch_history': watch_history,
        'can_watch': can_watch,
        'next_available': next_available,
        'is_premium': hasattr(request.user, 'premiumsubscription') and request.user.premiumsubscription.is_active
    }
    return render(request, 'films/detail.html', context)

@login_required
@user_passes_test(is_superuser)
def upload_video(request):
    if request.method == 'POST':
        print("\n=== Upload Attempt ===")
        print("POST data:", request.POST)
        print("FILES data:", request.FILES)
        
        form = VideoUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            print("\n=== Form Validation Errors ===")
            print("Form errors:", form.errors)
            print("Form non-field errors:", form.non_field_errors())
            
            # Check each field specifically
            for field in form:
                if field.errors:
                    print(f"\nField '{field.name}' errors:")
                    print(f"Value: {field.value()}")
                    print(f"Errors: {field.errors}")
            
            messages.error(request, 'Please check the form for errors.')
            return render(request, 'films/upload.html', {'form': form})
            
        try:
            film = form.save(commit=False)
            film.uploaded_by = request.user  # Set the uploaded_by field
            
            # Handle visibility and allowed users
            if film.visibility == 'requested':
                # For requested films, add the current user as an allowed user
                film.save()  # Save first to get an ID
                allowed_users = list(form.cleaned_data.get('allowed_users', []))
                allowed_users.append(request.user)  # Add current user
                film.allowed_users.set(allowed_users)  # Set all allowed users
            else:
                film.save()
            
            print("\n=== Upload Success ===")
            print(f"Film ID: {film.id}")
            print(f"Title: {film.title}")
            print(f"TMDB ID: {film.tmdb_id}")
            print(f"Uploaded by: {film.uploaded_by}")
            print(f"Visibility: {film.visibility}")
            print(f"Files uploaded:")
            print(f"- Video: {film.video_file}")
            print(f"- English subtitle: {film.english_subtitle}")
            print(f"- Russian subtitle: {film.russian_subtitle}")
            
            messages.success(request, 'Film uploaded successfully!')
            return redirect('films:film_detail', film_id=film.id)
            
        except Exception as e:
            print("\n=== Upload Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            messages.error(request, f'Error uploading film: {str(e)}')
            return render(request, 'films/upload.html', {'form': form})
    else:
        form = VideoUploadForm()
    
    return render(request, 'films/upload.html', {'form': form})

@login_required
@user_passes_test(is_superuser)
def edit_film(request, film_id=None):
    # If film_id is in GET parameters, use that
    if not film_id:
        film_id = request.GET.get('film_id')
    
    if not film_id:
        messages.error(request, 'No film specified.')
        return redirect('films:film_list')
    
    film = get_object_or_404(Film, id=film_id)
    
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES, instance=film)
        if form.is_valid():
            film = form.save()
            
            # Handle visibility and allowed users
            if film.visibility == 'requested':
                # Get the list of allowed users from the form
                allowed_user_ids = request.POST.get('allowed_users', '').split(',')
                if allowed_user_ids and allowed_user_ids[0]:  # Check if not empty
                    # Clear existing allowed users and set new ones
                    film.allowed_users.clear()
                    film.allowed_users.set(allowed_user_ids)
                else:
                    messages.error(request, 'Please select at least one user for requested films.')
                    return render(request, 'films/upload.html', {'form': form, 'film': film})
            
            messages.success(request, 'Film updated successfully!')
            return redirect('films:film_detail', film_id=film.id)
    else:
        form = VideoUploadForm(instance=film)
    
    # Get the list of allowed users for the film
    allowed_users = film.allowed_users.all()
    
    return render(request, 'films/edit.html', {
        'form': form,
        'film': film,
        'allowed_users': allowed_users,
        'film_id': film.id  # Explicitly pass film_id
    })

@login_required
def play_video(request, film_id):
    film = get_object_or_404(Film, id=film_id)
    
    # Check if user has permission to view the film
    if not request.user.is_superuser and film.visibility == 'requested' and request.user not in film.allowed_users.all():
        messages.error(request, 'You do not have permission to view this film.')
        return redirect('films:film_list')
    
    return render(request, 'films/player.html', {'film': film})

@login_required
def film_vocabulary(request, film_id):
    film = get_object_or_404(Film, id=film_id)
    
    # Check if user has permission to view the film
    if not request.user.is_superuser and film.visibility == 'requested' and request.user not in film.allowed_users.all():
        messages.error(request, 'You do not have permission to view this film.')
        return redirect('films:film_list')
    
    # Get filter parameters
    level = request.GET.get('level', 'all')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'frequency')
    page = request.GET.get('page', 1)
    word = request.GET.get('word', '')
    
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Get vocabulary details
    vocabulary_details = film.vocabulary_details
    
    # Filter by level if specified
    if level != 'all':
        vocabulary_details = {
            word: details for word, details in vocabulary_details.items()
            if details['level'].lower() == level.lower()
        }
    
    # Filter by search query if specified
    if search_query:
        vocabulary_details = {
            word: details for word, details in vocabulary_details.items()
            if search_query.lower() in word.lower() or 
               search_query.lower() in details['definition'].lower()
        }
    
    # Sort vocabulary
    if sort_by == 'frequency':
        vocabulary_details = dict(sorted(
            vocabulary_details.items(),
            key=lambda x: x[1]['frequency'],
            reverse=True
        ))
    elif sort_by == 'level':
        level_order = {'A1': 0, 'A2': 1, 'B1': 2, 'B2': 3, 'C1': 4, 'C2': 5}
        vocabulary_details = dict(sorted(
            vocabulary_details.items(),
            key=lambda x: level_order.get(x[1]['level'], 0)
        ))
    
    # Calculate pagination
    items_per_page = 20
    total_items = len(vocabulary_details)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Get current page items
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_page_items = dict(list(vocabulary_details.items())[start_idx:end_idx])
    
    # If a specific word is requested, get its contexts
    if word:
        contexts = []
        try:
            # Read subtitle file directly
            if film.english_subtitle:
                with open(film.english_subtitle.path, 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                # Split content into subtitle blocks
                subtitle_blocks = subtitle_content.split('\n\n')
                
                # Create regex pattern for the word
                word_pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                
                # Process each subtitle block
                for block in subtitle_blocks:
                    lines = block.strip().split('\n')
                    if len(lines) < 3:  # Skip invalid blocks
                        continue
                    
                    # Extract timestamp line
                    timestamp_line = lines[1]
                    if '-->' not in timestamp_line:
                        continue
                    
                    # Parse timestamps
                    start_time, end_time = timestamp_line.split('-->')
                    start_time = start_time.strip()
                    end_time = end_time.strip()
                    
                    # Get the actual subtitle text (all lines after timestamp)
                    text_lines = lines[2:]
                    text = ' '.join(text_lines)
                    
                    # Clean up the text
                    # Remove any remaining numbers at the start
                    text = re.sub(r'^\d+\s+', '', text)
                    # Remove any remaining timestamps
                    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->?\s*\d{2}:\d{2}:\d{2}\.\d{3}', '', text)
                    # Clean up whitespace
                    text = ' '.join(text.split())
                    
                    if word_pattern.search(text):
                        contexts.append({
                            'sentence': text,
                            'start_time': start_time,
                            'end_time': end_time
                        })
                
                # Limit to 10 contexts
                contexts = contexts[:10]
            
        except Exception as e:
            logger.error(f"Error getting contexts for word {word}: {str(e)}")
            contexts = []
        
        # Return contexts as JSON
        return JsonResponse({
            'contexts': contexts,
            'word': word
        })
    
    context = {
        'film': film,
        'vocabulary_details': current_page_items,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'current_level': level,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'films/vocabulary.html', context)

@login_required
def get_sentence_segment(request, film_id):
    """Create and serve a temporary video segment for a specific sentence."""
    film = get_object_or_404(Film, id=film_id)
    start_time = request.GET.get('start')
    end_time = request.GET.get('end')
    
    if not start_time or not end_time:
        return HttpResponse('Missing start or end time', status=400)
    
    try:
        # Convert VTT time format to seconds
        def vtt_time_to_seconds(vtt_time):
            h, m, s = vtt_time.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        
        start_seconds = vtt_time_to_seconds(start_time)
        end_seconds = vtt_time_to_seconds(end_time)
        
        # Add buffer time before and after the sentence
        buffer_time = 1.0  # 1 second buffer
        start_seconds = max(0, start_seconds - buffer_time)
        duration = end_seconds - start_seconds + buffer_time
        
        # Create a temporary file for the segment
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Use ffmpeg to create the segment
            command = [
                'ffmpeg',
                '-ss', str(start_seconds),
                '-i', film.video_file.path,
                '-t', str(duration),
                '-c', 'copy',
                '-y',
                temp_path
            ]
            
            subprocess.run(command, check=True, capture_output=True)
            
            # Serve the temporary file
            response = FileResponse(open(temp_path, 'rb'), content_type='video/mp4')
            response['Content-Disposition'] = f'inline; filename="sentence_segment.mp4"'
            
            # Delete the temporary file after sending
            def cleanup():
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")
            
            response.closed = cleanup
            return response
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating video segment: {str(e)}")
            logger.error(f"FFmpeg stderr: {e.stderr.decode()}")
            return HttpResponse('Error creating video segment', status=500)
            
    except Exception as e:
        logger.error(f"Error processing video segment: {str(e)}")
        return HttpResponse('Error processing video segment', status=500)

@login_required
@require_http_methods(["GET"])
def search_tmdb(request):
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse([], safe=False)
    
    if not hasattr(settings, 'TMDB_API_KEY'):
        logger.error("TMDB_API_KEY is not configured in settings")
        return JsonResponse({'error': 'TMDB API is not configured'}, status=500)
    
    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/search/movie',
            params={
                'api_key': settings.TMDB_API_KEY,
                'query': query,
                'language': 'en-US',
                'page': 1,
                'include_adult': False
            }
        )
        response.raise_for_status()
        data = response.json()
        
        results = []
        for movie in data.get('results', [])[:5]:  # Limit to 5 results
            results.append({
                'id': movie['id'],
                'title': movie['title'],
                'release_date': movie.get('release_date'),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
                'overview': movie.get('overview'),
                'vote_average': movie.get('vote_average')
            })
        
        return JsonResponse(results, safe=False)
    except requests.RequestException as e:
        logger.error(f"Error searching TMDB: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def create_film_request(request):
    try:
        data = json.loads(request.body)
        film_request = FilmRequest.objects.create(
            user=request.user,
            title=data.get('tmdb_title', 'Untitled Request'),
            tmdb_id=data.get('tmdb_id'),
            status='pending'
        )
        
        # Create notifications for superusers
        Notification.create_film_request_notification(film_request)
        
        return JsonResponse({'status': 'success', 'request_id': film_request.id})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating film request: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def film_request_list(request):
    if request.user.is_superuser:
        # Superusers see all requests
        requests = FilmRequest.objects.all().order_by('-created_at')
    else:
        # Regular users see only their requests
        requests = FilmRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'films/request_list.html', {'requests': requests})

@login_required
def film_request_detail(request, request_id):
    if request.user.is_superuser:
        film_request = get_object_or_404(FilmRequest, id=request_id)
    else:
        film_request = get_object_or_404(FilmRequest, id=request_id, user=request.user)
    return render(request, 'films/request_detail.html', {'request': film_request})

@login_required
@user_passes_test(is_superuser)
@require_http_methods(["POST"])
def update_film_request_status(request, request_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        film_id = data.get('film_id')  # Optional: ID of an existing film to link
        
        if new_status not in dict(FilmRequest.STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        film_request = get_object_or_404(FilmRequest, id=request_id)
        
        # If linking to an existing film
        if film_id and new_status == 'completed':
            film = get_object_or_404(Film, id=film_id)
            film_request.film = film
            film_request.status = new_status
            film_request.save()
            
            # Add the requesting user to the film's allowed users
            film.add_allowed_user(film_request.user)
            
            return JsonResponse({
                'message': 'Request completed and linked to existing film',
                'status': new_status
            })
        
        film_request.status = new_status
        film_request.save()
        
        return JsonResponse({
            'message': 'Request status updated successfully',
            'status': new_status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating film request status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def my_films(request):
    if request.user.is_superuser:
        uploaded_films = Film.objects.all().order_by('-uploaded_at')
        requested_films = Film.objects.none()  # Superusers don't have requested films
    else:
        uploaded_films = Film.objects.none()  # Regular users can't upload films
        # Get films that the user has requested and are approved
        requested_films = Film.objects.filter(
            allowed_users=request.user
        ).order_by('-uploaded_at')
    
    return render(request, 'films/my_films.html', {
        'uploaded_films': uploaded_films,
        'requested_films': requested_films
    })

@login_required
@user_passes_test(is_superuser)
def link_film_to_request(request, request_id):
    film_request = get_object_or_404(FilmRequest, id=request_id)
    film_id = request.POST.get('film_id')
    
    if film_id:
        film = get_object_or_404(Film, id=film_id)
        film_request.film = film
        film_request.status = 'completed'
        film_request.save()
        
        # Add the requesting user to the film's allowed users
        film.allowed_users.add(film_request.user)
        
        messages.success(request, 'Film linked to request successfully!')
    else:
        messages.error(request, 'No film selected.')
    
    return redirect('films:film_requests')

@login_required
@user_passes_test(is_superuser)
def search_users(request):
    query = request.GET.get('query', '')
    
    if not query:
        return JsonResponse({'users': []})
    
    User = get_user_model()
    
    try:
        # Search in both username and email fields
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(is_superuser=True)[:5]  # Limit to 5 results and exclude superusers
        
        results = [{
            'id': user.id,
            'username': user.username,
            'email': user.email
        } for user in users]
        
        return JsonResponse({'users': results})
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_superuser)
@require_http_methods(["POST"])
def save_allowed_users(request, film_id):
    try:
        # First check if the film exists
        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Film with ID {film_id} not found'
            }, status=404)

        # Parse the JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)

        allowed_user_ids = data.get('allowed_users', [])
        
        # Update allowed users
        film.allowed_users.clear()
        if allowed_user_ids:
            # Verify that all user IDs exist
            User = get_user_model()
            existing_users = User.objects.filter(id__in=allowed_user_ids)
            if len(existing_users) != len(allowed_user_ids):
                return JsonResponse({
                    'status': 'error',
                    'message': 'One or more user IDs are invalid'
                }, status=400)
            film.allowed_users.set(existing_users)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Allowed users updated successfully',
            'allowed_users': list(film.allowed_users.values('id', 'username'))
        })
    except Exception as e:
        logger.error(f"Error saving allowed users for film {film_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def request_film(request):
    if request.method == 'POST':
        form = FilmRequestForm(request.POST)
        if form.is_valid():
            film_request = form.save(commit=False)
            film_request.user = request.user
            film_request.save()
            
            # Create notifications for superusers
            Notification.create_film_request_notification(film_request)
            
            messages.success(request, 'Your film request has been submitted successfully.')
            return redirect('films:film_list')
    else:
        form = FilmRequestForm()
    
    return render(request, 'films/request_film.html', {'form': form})

@login_required
def notifications(request):
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()
    
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            
            if notification.film_request:
                return redirect('films:my_requests')
    
    return render(request, 'films/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })

@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('films:notifications')

@login_required
def get_unread_notification_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def my_requests(request):
    if not request.user.is_superuser:
        requests = FilmRequest.objects.filter(user=request.user)
    else:
        requests = FilmRequest.objects.all()
    
    return render(request, 'films/my_requests.html', {'requests': requests})

@login_required
def update_request_status(request, request_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    
    film_request = get_object_or_404(FilmRequest, id=request_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(FilmRequest.STATUS_CHOICES):
            film_request.status = new_status
            film_request.save()
            
            # Notify user about status change
            send_mail(
                f'Film Request {new_status.capitalize()}',
                f'Your request for "{film_request.title}" has been {new_status}.',
                settings.DEFAULT_FROM_EMAIL,
                [film_request.user.email],
                fail_silently=False,
            )
            
            messages.success(request, f'Request status updated to {new_status}')
    
    return redirect('films:my_requests')

@login_required
def watch_film(request, film_id):
    film = get_object_or_404(Film, id=film_id)
    
    # Check if user can watch the film
    if not film.can_user_watch(request.user):
        if film.visibility == 'public' and not film.is_paid:
            next_time = film.get_next_available_time(request.user)
            if next_time:
                messages.warning(
                    request,
                    f'You can watch this film again after {next_time.strftime("%Y-%m-%d %H:%M")}. '
                    'Upgrade to premium for unlimited access!'
                )
            else:
                messages.warning(
                    request,
                    'You can only watch one film every 3 days with a free account. '
                    'Upgrade to premium for unlimited access!'
                )
        else:
            messages.error(request, 'You do not have permission to watch this film.')
        return redirect('films:film_detail', film_id=film.id)
    
    # Record the watch
    film.record_watch(request.user)
    
    context = {
        'film': film,
        'is_premium': hasattr(request.user, 'premiumsubscription') and request.user.premiumsubscription.is_active
    }
    return render(request, 'films/watch.html', context)

@login_required
def upload_film(request):
    if request.method == 'POST':
        form = FilmUploadForm(request.POST, request.FILES)
        if form.is_valid():
            film = form.save(commit=False)
            film.uploaded_by = request.user
            
            # Set visibility based on form data
            visibility = form.cleaned_data.get('visibility')
            film.visibility = visibility
            
            # If it's a paid film, create payment record
            if form.cleaned_data.get('is_paid'):
                film.is_paid = True
                film.is_fast_delivery = form.cleaned_data.get('is_fast_delivery', False)
            
            film.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, 'Film uploaded successfully!')
            return redirect('films:film_detail', film_id=film.id)
    else:
        form = FilmUploadForm()
    
    return render(request, 'films/upload.html', {'form': form}) 