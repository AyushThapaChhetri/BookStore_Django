# In your_project/celery.py

import os

from celery import Celery

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_B.settings')  # Replace 'your_project'

app = Celery('Project_B')  # App name matches project

# Load Celery config from Django settings (prefix 'CELERY_')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()
