import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class PromptTemplate(models.Model):
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
