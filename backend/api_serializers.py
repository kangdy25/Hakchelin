from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.models import User
from chatbot.models import AiLog, ChatMessage
from meals.models import Menu
from reservations.models import Reservation
from wallet.models import PointTransaction


class UserSummarySerializer(serializers.Serializer):
    """
    타 도메인(예약, 포인트 거래, AI 로그 등)에 포함하기 위한 간소화된 사용자 정보 시리얼라이저.

    민감한 인증 정보(이메일, 잔여 포인트 등)를 배제하고 표시 목적의 최소 필드만 직렬화합니다.
    """
    name = serializers.CharField()
    student_id = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """사용자 상세 프로필 조회 전용 ModelSerializer"""
    class Meta:
        model = User
        fields = ["id", "email", "role", "student_id", "name", "current_point", "created_at"]
        read_only_fields = fields


class MenuSummarySerializer(serializers.Serializer):
    """
    메뉴 전체 정보 조회(GET) 전용 ModelSerializer.

    식단 일정, 가격, 예약 정원, 마감 시점 등 메뉴 엔티티의 모든 상세 필드를 클라이언트 응답 규격으로 직렬화합니다.
    """
    title_ko = serializers.CharField()
    title_en = serializers.CharField()
    price = serializers.IntegerField()
    type = serializers.CharField()
    day_of_week = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    """
    사용자 로그인 요청 처리를 위한 인증 시리얼라이저.

    이메일과 비밀번호 필드를 수신하며, 비밀번호는 직렬화(응답) 시 누출되지 않도록 처리합니다.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SignupSerializer(LoginSerializer):
    """
    신규 회원가입을 위한 요청 데이터 검증 시리얼라이저.

    LoginSerializer를 상속받아 이메일/비밀번호 필드를 재사용하며,
    추가적인 실명, 학번 입력값 및 Django 내장 패스워드 복잡도 검증을 수행합니다.
    """
    name = serializers.CharField(max_length=100)
    student_id = serializers.CharField(max_length=64)

    def validate(self, attrs):
        user = User(email=attrs["email"], name=attrs["name"], student_id=attrs["student_id"])
        validate_password(attrs["password"], user=user)
        return attrs


class MenuSerializer(serializers.ModelSerializer):
    """
    메뉴 전체 정보 조회(GET) 전용 ModelSerializer.

    식단 일정, 가격, 예약 정원, 마감 시점 등 메뉴 엔티티의 모든 상세 필드를 클라이언트 응답 규격으로 직렬화합니다.
    """
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
    """
    관리자 메뉴 신규 등록(POST) 및 부분 수정(PATCH) 전용 ModelSerializer.

    클라이언트가 임의로 조작해서는 안 되는 식별자와 생성일시를 입력 대상에서 제외하여 Mass Assignment를 방지합니다.
    """
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
    """관리자 API에서 특정 사용자의 권한/역할(Role)을 변경할 때 사용하는 시리얼라이저"""
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
