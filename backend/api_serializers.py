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


class MenuQuerySerializer(serializers.Serializer):
    """메뉴 목록의 활성화 여부와 조회 시작일 필터를 검증하는 쿼리 DTO."""
    active_only = serializers.BooleanField(required=False, default=False)
    from_date = serializers.DateField(required=False)


class ReservationSerializer(serializers.ModelSerializer):
    """
    예약 상세 및 목록 조회(GET) 전용 ModelSerializer.

    예약 당사자 요약 정보(UserSummarySerializer)와 연결된 식단 정보(MenuSummarySerializer)를
    중첩 구조로 함께 직렬화하며, 확정된 예약의 임의 수정을 방지하기 위해 전체 필드를 읽기 전용으로 설정합니다.
    """
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
    """
    식단 메뉴 예약 요청(POST) 데이터 검증 시리얼라이저.

    클라이언트로부터 식단 ID, 커스텀 옵션(JSON), 지불할 총금액을 전달받아 유효성을 검증합니다.
    """
    menu_id = serializers.CharField(max_length=64)
    options = serializers.JSONField(default=dict)
    total_price = serializers.IntegerField(min_value=0)


class PointTransactionSerializer(serializers.ModelSerializer):
    """
    포인트 거래(변동) 내역 조회 전용 ModelSerializer.

    사용자 정보를 UserSummarySerializer를 통해 중첩 요약 객체로 직렬화하며,
    거래내역 데이터의 위변조 방지를 위해 전체 필드를 읽기 전용(read_only)으로 설정합니다.
    """
    users = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = PointTransaction
        fields = ["id", "user_id", "amount", "type", "description", "created_at", "users"]
        read_only_fields = fields


class AmountSerializer(serializers.Serializer):
    """포인트 기부 또는 결제 주문 시 단일 금액(amount) 입력을 검증하는 기본 DTO"""
    amount = serializers.IntegerField()


class AdminPointSerializer(AmountSerializer):
    """
    [관리자 전용] 사용자 포인트 수동 지급/차감 처리 시리얼라이저.

    AmountSerializer를 상속받아 금액 필드를 재사용하며, 감사 추적을 위해 필수적인 사유 설명 필드를 추가합니다.
    """
    description = serializers.CharField(max_length=255)


class AdminRoleSerializer(serializers.Serializer):
    """관리자 API에서 특정 사용자의 권한/역할(Role)을 변경할 때 사용하는 시리얼라이저"""
    role = serializers.ChoiceField(choices=User.Role.choices)


class PointOrderSerializer(serializers.Serializer):
    """
    포인트 충전 사전 주문 생성 응답 DTO.

    클라이언트가 토스페이먼츠 SDK 결제창을 띄우는 데 필요한 식별 번호와 금액 정보를 직렬화합니다.
    """
    order_id = serializers.CharField()
    amount = serializers.IntegerField()
    point_amount = serializers.IntegerField()


class PointPaymentConfirmSerializer(serializers.Serializer):
    """
    토스페이먼츠 결제창 인증 완료 후 서버 최종 승인 요청 DTO.

    클라이언트가 토스 SDK로부터 전달받은 인증 파라미터를 수신하여 금액 위변조 및 유효성을 검증합니다.
    """
    payment_key = serializers.CharField(max_length=255)
    order_id = serializers.CharField(max_length=100)
    amount = serializers.IntegerField(min_value=1)


class PointPaymentResultSerializer(serializers.Serializer):
    """
    토스페이먼츠 최종 승인 완료 응답 DTO.

    승인 확정된 주문 ID, 최종 주문 상태, 실제 충전 처리된 포인트 수량을 클라이언트에 반환합니다.
    """
    order_id = serializers.CharField()
    status = serializers.CharField()
    point_amount = serializers.IntegerField()


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    대화 이력 조회 전용 ModelSerializer.

    클라이언트 렌더링에 필요한 발화 주체와 대화 본문만 직렬화하며,
    과거 메시지 위변조를 방지하기 위해 전체 필드를 읽기 전용으로 제한합니다.
    """
    class Meta:
        model = ChatMessage
        fields = ["role", "content"]
        read_only_fields = fields


class ChatRequestSerializer(serializers.Serializer):
    """
    AI 챗봇 질문 전송 및 스트리밍 요청 데이터 검증 DTO.

    클라이언트로부터 사용자 질문 문자열과 대화 세션 식별자를 수신하여
    질문 길이 제한(1~100자) 및 포맷 유효성을 검증합니다.
    """
    message = serializers.CharField(min_length=1, max_length=100)
    conversation_id = serializers.UUIDField()


class AiLogSerializer(serializers.ModelSerializer):
    """
    [관리자 전용] AI 추론 파이프라인 감사 로그 조회 전용 ModelSerializer.

    추론 단계, 사용 모델, 응답 소요 시간(Latency), 에러 메시지와 요청자 요약 정보를 함께 직렬화하며,
    감사 데이터의 무결성을 위해 전체 필드를 읽기 전용으로 제한합니다.
    """
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
    """
    CSRF 쿠키 세팅 확인 응답 전용 스키마 DTO.

    SPA/프론트엔드 초기화 시 브라우저에 'csrftoken' 쿠키가 정상 주입되었음을 알리는
    상태 응답({"csrf": "ready"})의 직렬화 규격을 정의하며, drf-spectacular 문서화에 활용됩니다.
    """
    csrf = serializers.CharField()
