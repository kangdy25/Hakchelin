from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.models import User
from chatbot.models import AiLog, ChatMessage
from meals.models import Menu
from reservations.models import Reservation
from wallet.models import PointTransaction


class UserSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    student_id = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role", "student_id", "name", "current_point", "created_at"]
        read_only_fields = fields


class MenuSummarySerializer(serializers.Serializer):
    title_ko = serializers.CharField()
    title_en = serializers.CharField()
    price = serializers.IntegerField()
    type = serializers.CharField()
    day_of_week = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SignupSerializer(LoginSerializer):
    name = serializers.CharField(max_length=100)
    student_id = serializers.CharField(max_length=64)

    def validate(self, attrs):
        user = User(email=attrs["email"], name=attrs["name"], student_id=attrs["student_id"])
        validate_password(attrs["password"], user=user)
        return attrs


class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = [
            "id",
            "day_of_week",
            "type",
            "title_ko",
            "title_en",
            "price",
            "meal_date",
            "meal_time",
            "capacity",
            "reservation_deadline",
            "deposit_amount",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class MenuWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        exclude = ["id", "created_at"]


class ReservationSerializer(serializers.ModelSerializer):
    users = UserSummarySerializer(source="user", read_only=True)
    menus = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "user_id",
            "menu_id",
            "options",
            "total_price",
            "status",
            "meal_date",
            "meal_time",
            "deposit_amount",
            "refunded_amount",
            "menu_snapshot",
            "created_at",
            "users",
            "menus",
        ]
        read_only_fields = fields

    @extend_schema_field(MenuSummarySerializer)
    def get_menus(self, obj) -> dict:
        return {
            "title_ko": obj.menu.title_ko,
            "title_en": obj.menu.title_en,
            "price": obj.menu.price,
            "type": obj.menu.type,
            "day_of_week": obj.menu.day_of_week,
        }


class ReservationCreateSerializer(serializers.Serializer):
    menu_id = serializers.CharField(max_length=64)
    options = serializers.JSONField(default=dict)
    total_price = serializers.IntegerField(min_value=0)


class PointTransactionSerializer(serializers.ModelSerializer):
    users = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = PointTransaction
        fields = ["id", "user_id", "amount", "type", "description", "created_at", "users"]
        read_only_fields = fields


class AmountSerializer(serializers.Serializer):
    amount = serializers.IntegerField()


class AdminPointSerializer(AmountSerializer):
    description = serializers.CharField(max_length=255)


class AdminRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class PointOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    amount = serializers.IntegerField()
    point_amount = serializers.IntegerField()


class PointPaymentConfirmSerializer(serializers.Serializer):
    payment_key = serializers.CharField(max_length=255)
    order_id = serializers.CharField(max_length=100)
    amount = serializers.IntegerField(min_value=1)


class PointPaymentResultSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    status = serializers.CharField()
    point_amount = serializers.IntegerField()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["role", "content"]
        read_only_fields = fields


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=100)
    conversation_id = serializers.UUIDField()


class AiLogSerializer(serializers.ModelSerializer):
    users = UserSummarySerializer(source="user", read_only=True, allow_null=True)

    class Meta:
        model = AiLog
        fields = [
            "id",
            "created_at",
            "stage",
            "model",
            "latency_ms",
            "status_code",
            "error_message",
            "users",
        ]
        read_only_fields = fields


class CsrfReadySerializer(serializers.Serializer):
    csrf = serializers.CharField()
