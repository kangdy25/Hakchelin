from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import ChatMessage


@shared_task
def delete_expired_chat_messages():
    """
    Celery Beat 스케줄러에 의해 1시간마다 주기적으로 실행되는 백그라운드 태스크.

    생성된 지 7일이 지난 ChatMessage 레코드를 DB에서 일괄 삭제하여 데이터베이스 스토리지 공간을 최적화하고 사용자 대화 개인정보 보관 기한을 준수합니다.
    """
    deleted, _ = ChatMessage.objects.filter(created_at__lt=timezone.now() - timedelta(days=7)).delete()
    return deleted
