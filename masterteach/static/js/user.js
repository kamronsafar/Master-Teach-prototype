// User Profile Interactions
document.addEventListener('DOMContentLoaded', () => {
    // Profile Image Upload Preview
    const profileImageInput = document.querySelector('#profile-image-input');
    const profileImage = document.querySelector('.profile-avatar');
    
    if (profileImageInput && profileImage) {
        profileImageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    profileImage.src = e.target.result;
                    profileImage.classList.add('animate__animated', 'animate__fadeIn');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Stats Counter Animation
    const stats = document.querySelectorAll('.stat-card h3');
    stats.forEach(stat => {
        const target = parseInt(stat.getAttribute('data-value'));
        animateCounter(stat, target);
    });

    // Timeline Animation
    const timelineItems = document.querySelectorAll('.timeline-item');
    const timelineObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('slide-in');
                timelineObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    timelineItems.forEach(item => timelineObserver.observe(item));

    // Settings Form Validation
    const settingsForm = document.querySelector('#settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            validateAndSubmitForm(settingsForm);
        });
    }

    // Notification System
    initializeNotifications();
});

// Counter Animation
function animateCounter(element, target, duration = 2000) {
    let start = 0;
    const increment = target / (duration / 16);
    const timer = setInterval(() => {
        start += increment;
        element.textContent = Math.floor(start);
        if (start >= target) {
            element.textContent = target;
            clearInterval(timer);
        }
    }, 16);
}

// Form Validation and Submission
function validateAndSubmitForm(form) {
    const formData = new FormData(form);
    const errors = [];

    // Validate email
    const email = formData.get('email');
    if (email && !isValidEmail(email)) {
        errors.push('Please enter a valid email address');
    }

    // Validate password if being changed
    const password = formData.get('password');
    const confirmPassword = formData.get('confirm_password');
    if (password && password !== confirmPassword) {
        errors.push('Passwords do not match');
    }

    if (errors.length > 0) {
        showNotification(errors.join('<br>'), 'error');
        return;
    }

    // Submit form
    submitForm(formData);
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Notification System
function initializeNotifications() {
    const notificationContainer = document.createElement('div');
    notificationContainer.className = 'notification-container';
    document.body.appendChild(notificationContainer);
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close">&times;</button>
    `;

    document.querySelector('.notification-container').appendChild(notification);

    // Add animation classes
    setTimeout(() => notification.classList.add('show'), 10);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);

    // Close button
    notification.querySelector('.notification-close').addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    });
}

// Form Submission
async function submitForm(formData) {
    try {
        const response = await fetch('/api/user/settings', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Settings updated successfully');
            // Refresh page after 1 second
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showNotification(data.message || 'An error occurred', 'error');
        }
    } catch (error) {
        showNotification('An error occurred while saving settings', 'error');
    }
}

// Utility Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
}); 