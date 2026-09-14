from celery import shared_task

from .services import process_no_shows as process_no_shows_service


@shared_task
def process_no_shows():
    """
    Celery Beat 스케줄러에 의해 15분마다 주기적으로 실행되는 백그라운드 태스크.

    실제 도메인 로직(노쇼 확정 및 포인트 환불 정산)은 services 계층에 위임하고, 처리 완료된 예약 건수를 반환합니다.
    """
    return process_no_shows_service()
