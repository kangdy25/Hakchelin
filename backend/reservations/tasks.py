from celery import shared_task

from .services import process_no_shows as process_no_shows_service


@shared_task
def process_no_shows():
    return process_no_shows_service()
