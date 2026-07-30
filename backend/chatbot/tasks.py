from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import ChatMessage


@shared_task
def delete_expired_chat_messages():
    deleted, _ = ChatMessage.objects.filter(created_at__lt=timezone.now() - timedelta(days=7)).delete()
    return deleted
