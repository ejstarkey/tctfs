"""
Celery queue configuration for TCTFS background tasks.
"""
from celery import Celery
from kombu import Queue

# Create Celery app
celery_app = Celery('tctfs')

# Configure Redis as broker and backend
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Define queues
celery_app.conf.task_queues = (
    Queue('default', routing_key='task.#'),
    Queue('ingest', routing_key='ingest.#'),
    Queue('forecast', routing_key='forecast.#'),
    Queue('zones', routing_key='zones.#'),
    Queue('alerts', routing_key='alerts.#'),
)

# Import schedules
from .schedules import CELERY_BEAT_SCHEDULE
celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE

# Default queue
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_default_exchange = 'tasks'
celery_app.conf.task_default_routing_key = 'task.default'
