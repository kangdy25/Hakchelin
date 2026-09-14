import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class PromptTemplate(models.Model):
    """
    LLM 프롬프트 템플릿의 버전 및 하이퍼파라미터를 동적으로 관리하는 모델.

    서비스 재배포 없이 프롬프트를 A/B 테스트하거나 롤백할 수 있도록 버저닝을 지원하며,
    DB 조건부 유니크 제약을 통해 서비스당 오직 하나의 활성 프롬프트만 허용합니다.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(max_length=100)
    version = models.PositiveIntegerField()
    prompt_content = models.TextField()
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default="0.20", validators=[MinValueValidator(0), MaxValueValidator(1)])
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["service_name", "version"], name="prompt_template_service_version"),
            models.UniqueConstraint(
                fields=["service_name"], condition=Q(is_active=True), name="prompt_template_one_active"
            ),
        ]


class AiLog(models.Model):
    """
    LLM 추론 파이프라인의 각 단계별 실행 결과, 지연 시간, 토큰 소모량 및 에러를 기록하는 감사 로그 모델.

    프롬프트 인젝션 방어, 가드레일, 본 대화 생성의 3단계 파이프라인을 분기 추적하며,
    운영 비용 정산(USD)과 시스템 장애 디버깅을 위한 관측성 데이터를 제공합니다.
    """
    class Stage(models.TextChoices):
        VALIDATION = "validation", "Validation"
        GUARDRAIL = "guardrail", "Guardrail"
        MAIN_CHAT = "main_chat", "Main chat"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.UUIDField(default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_logs")
    stage = models.CharField(max_length=16, choices=Stage.choices)
    model = models.CharField(max_length=100, null=True, blank=True)
    prompt_version = models.PositiveIntegerField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    status_code = models.PositiveSmallIntegerField()
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "stage", "-created_at"], name="ai_log_user_stage_created_idx"),
            models.Index(fields=["-created_at"], name="ai_log_created_idx"),
        ]


class ChatMessage(models.Model):
    """
    사용자와 AI 어시스턴트 간의 대화 세션 메시지를 저장하는 모델.

    컨텍스트 기반 멀티턴(Multi-turn) 대화를 위해 이전 대화 내역을 제공하며,
    개인정보 보호 및 스토리지 관리를 위해 Celery 배치 태스크로 7일 경과 시 자동 삭제됩니다.
    """
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    conversation_id = models.UUIDField()
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "conversation_id", "created_at"], name="chat_message_conversation_idx")
        ]
