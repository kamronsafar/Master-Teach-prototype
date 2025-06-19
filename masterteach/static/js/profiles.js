// Profile-related JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle favorite toggling
    const favoriteButtons = document.querySelectorAll('.btn-favorite');
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const filmSlug = this.dataset.filmSlug;
            toggleFavorite(filmSlug, this);
        });
    });

    // Handle avatar preview
    const avatarInput = document.querySelector('input[type="file"]');
    if (avatarInput) {
        avatarInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                if (file.size > 5 * 1024 * 1024) { // 5MB limit
                    alert('File size must be less than 5MB');
                    this.value = '';
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.querySelector('.profile-avatar');
                    if (preview) {
                        preview.src = e.target.result;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

// Toggle favorite status
function toggleFavorite(filmSlug, button) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Show loading state
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
    
    fetch(`/profiles/toggle-favorite/${filmSlug}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.is_favorite) {
            button.classList.remove('btn-outline-warning');
            button.classList.add('btn-warning');
            button.innerHTML = '<i class="fas fa-star"></i> Remove from Favorites';
        } else {
            button.classList.remove('btn-warning');
            button.classList.add('btn-outline-warning');
            button.innerHTML = '<i class="fas fa-star"></i> Add to Favorites';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while updating favorites.');
        button.innerHTML = originalContent;
    })
    .finally(() => {
        button.disabled = false;
    });
}

// Mark film as watched
function markWatched(filmSlug) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/profiles/mark-watched/${filmSlug}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI to show film as watched
            const filmCard = document.querySelector(`[data-film-slug="${filmSlug}"]`);
            if (filmCard) {
                filmCard.classList.add('watched');
                const watchButton = filmCard.querySelector('.btn-watch');
                if (watchButton) {
                    watchButton.disabled = true;
                    watchButton.innerHTML = '<i class="fas fa-check"></i> Watched';
                }
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while marking the film as watched.');
    });
}

// Update CEFR progress bars
function updateCEFRProgress(stats) {
    const total = stats.a1_count + stats.a2_count + stats.b1_count + 
                 stats.b2_count + stats.c1_count + stats.c2_count;
    
    if (total > 0) {
        const beginnerProgress = ((stats.a1_count + stats.a2_count) / total) * 100;
        const intermediateProgress = ((stats.b1_count + stats.b2_count) / total) * 100;
        const advancedProgress = ((stats.c1_count + stats.c2_count) / total) * 100;
        
        document.querySelector('.cefr-beginner').style.width = `${beginnerProgress}%`;
        document.querySelector('.cefr-intermediate').style.width = `${intermediateProgress}%`;
        document.querySelector('.cefr-advanced').style.width = `${advancedProgress}%`;
    }
} 