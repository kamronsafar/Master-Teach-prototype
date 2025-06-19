import os
from celery import Celery
from celery.signals import worker_ready
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'masterteach.settings')

app = Celery('masterteach')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery to use Redis as message broker
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
)

@worker_ready.connect
def at_start(sender, **kwargs):
    """Initialize NLTK data when Celery worker starts"""
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('wordnet', quiet=True)
    except Exception as e:
        print(f"Error downloading NLTK data: {str(e)}")

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')