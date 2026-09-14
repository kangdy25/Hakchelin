import uuid

from django.conf import settings
from django.db import models


class PointTransaction(models.Model):
    """사용자의 포인트 변동(충전, 차감, 환불) 내역을 기록하는 모델"""
    class Type(models.TextChoices):
        CHARGE = "charge", "Charge"
        DEDUCT = "deduct", "Deduct"
        REFUND = "refund", "Refund"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="point_transactions")
    amount = models.IntegerField()
    type = models.CharField(max_length=16, choices=Type.choices)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
