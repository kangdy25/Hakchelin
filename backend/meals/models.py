import uuid

from django.core.validators import MinValueValidator
from django.db import models


def new_menu_id() -> str:
    return str(uuid.uuid4())


class Menu(models.Model):
    class Type(models.TextChoices):
        KOREAN = "kr", "Korean"
        PREMIUM = "premium", "Premium"
        TAKEOUT = "takeout", "Takeout"

    id = models.CharField(primary_key=True, max_length=64, default=new_menu_id, editable=False)
    day_of_week = models.CharField(max_length=16, blank=True)
    type = models.CharField(max_length=16, choices=Type.choices)
    title_ko = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    price = models.PositiveIntegerField(default=4500)
    meal_date = models.DateField()
    meal_time = models.TimeField(default="12:00:00")
    capacity = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])
    reservation_deadline = models.DateTimeField()
    deposit_amount = models.PositiveIntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["meal_date", "meal_time"], name="menu_active_date_idx")]
        ordering = ["meal_date", "meal_time"]

    def __str__(self) -> str:
        return f"{self.meal_date} {self.title_ko}"
