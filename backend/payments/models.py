import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PointOrder(models.Model):
    """
    외부 PG사(토스페이먼츠)를 통한 포인트 충전 주문 및 결제 승인 내역을 관리하는 모델.

    결제 전체 라이프사이클을 추적하며, PG사 결제 키(payment_key)의 고유성 제약과 원본 응답 스냅샷(toss_response) 저장을 통해 중복 결제 방지 및 감사(Audit) 추적 기능을 제공합니다.
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="point_orders")
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    point_amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    payment_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    payment_provider = models.CharField(max_length=32, default="toss")
    paid_at = models.DateTimeField(null=True, blank=True)
    toss_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
