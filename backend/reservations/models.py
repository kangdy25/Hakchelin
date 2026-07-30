import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Reservation(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        USED = "used", "Used"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    menu = models.ForeignKey("meals.Menu", on_delete=models.PROTECT, related_name="reservations")
    options = models.JSONField(default=dict)
    total_price = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RESERVED)
    meal_date = models.DateField()
    meal_time = models.TimeField()
    menu_snapshot = models.JSONField(default=dict)
    deposit_amount = models.PositiveIntegerField(default=0)
    refunded_amount = models.PositiveIntegerField(default=0)
    enforces_meal_limit = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "meal_date", "meal_time"],
                condition=Q(status__in=["reserved", "used"]) & Q(enforces_meal_limit=True),
                name="reservation_one_meal_per_user",
            )
        ]
        indexes = [models.Index(fields=["menu", "status"], name="reservation_menu_status_idx")]
        ordering = ["-created_at"]
