from rest_framework import serializers


class MenuSerializer(serializers.Serializer):
    id = serializers.CharField()
    day_of_week = serializers.CharField(allow_blank=True)
    type = serializers.ChoiceField(choices=["kr", "premium", "takeout"])
    title_ko = serializers.CharField()
    title_en = serializers.CharField()
    price = serializers.IntegerField()
    meal_date = serializers.DateField()
    meal_time = serializers.TimeField()
    capacity = serializers.IntegerField()
    reservation_deadline = serializers.DateTimeField()
    deposit_amount = serializers.IntegerField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class ProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=["student", "admin"])
    student_id = serializers.CharField()
    name = serializers.CharField()
    current_point = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class ReservationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    menu_id = serializers.CharField()
    options = serializers.JSONField()
    total_price = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["reserved", "used", "cancelled", "no_show"])
    meal_date = serializers.DateField()
    meal_time = serializers.TimeField()
    menu_snapshot = serializers.JSONField()
    deposit_amount = serializers.IntegerField()
    refunded_amount = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    cancelled_at = serializers.DateTimeField(allow_null=True)
    used_at = serializers.DateTimeField(allow_null=True)


class PointTransactionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    amount = serializers.IntegerField()
    type = serializers.ChoiceField(choices=["charge", "deduct", "refund"])
    description = serializers.CharField(allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField()
