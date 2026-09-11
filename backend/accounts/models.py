import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models


class UserManager(BaseUserManager):
    """
    User 모델 생성을 전담하는 커스텀 매니저 클래스.

    일반 사용자 및 관리자(Superuser) 계정 생성 로직을 제공합니다.
    """
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("관리자 계정은 is_staff와 is_superuser가 필요합니다.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    이메일 기반 로그인을 지원하는 커스텀 사용자 모델.

    기본 인증 필드로 email을 사용하며, 권한 관리, 학번, 역할, 포인트 필드를 포함합니다.
    """
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)
    student_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    current_point = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["student_id", "name"]

    class Meta:
        ordering = ["student_id"]

    def save(self, *args, **kwargs):
        self.is_staff = self.role == self.Role.ADMIN or self.is_superuser
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student_id} ({self.email})"
