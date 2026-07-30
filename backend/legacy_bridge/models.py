"""Read-only mappings for the existing Supabase `public` schema.

These models deliberately have no Django migrations. They are used only while
the API bridges Supabase PostgreSQL and must never be written through Django.
"""

from django.db import models


class LegacyUser(models.Model):
    id = models.UUIDField(primary_key=True)
    role = models.CharField(max_length=16)
    student_id = models.CharField(max_length=64)
    name = models.CharField(max_length=100)
    current_point = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'public"."users'


class LegacyMenu(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    day_of_week = models.CharField(max_length=16)
    type = models.CharField(max_length=16)
    title_ko = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    price = models.IntegerField()
    meal_date = models.DateField()
    meal_time = models.TimeField()
    capacity = models.IntegerField()
    reservation_deadline = models.DateTimeField()
    deposit_amount = models.IntegerField()
    is_active = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'public"."menus'


class LegacyReservation(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField()
    menu_id = models.CharField(max_length=64)
    options = models.JSONField()
    total_price = models.IntegerField()
    status = models.CharField(max_length=16)
    meal_date = models.DateField()
    meal_time = models.TimeField()
    menu_snapshot = models.JSONField()
    deposit_amount = models.IntegerField()
    refunded_amount = models.IntegerField()
    created_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True)
    used_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'public"."reservations'


class LegacyPointTransaction(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField()
    amount = models.IntegerField()
    type = models.CharField(max_length=16)
    description = models.TextField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'public"."transactions'
