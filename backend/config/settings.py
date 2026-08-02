import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host]


def env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() == "true"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "meals",
    "reservations",
    "wallet",
    "payments",
    "chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.WriteBlockMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
if "pytest" in sys.modules or any("pytest" in argument for argument in sys.argv):
    database_url = os.getenv("TEST_DATABASE_URL") or "sqlite:///:memory:"

DATABASES = {
    "default": dj_database_url.parse(
        database_url,
        conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "0")),
    )
}

DJANGO_WRITE_BLOCKED = os.getenv("DJANGO_WRITE_BLOCKED", "false").lower() == "true"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Hakchelin API",
    "DESCRIPTION": "Hakchelin Django API contract",
    "VERSION": "v1",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "UserRoleEnum": [("student", "Student"), ("admin", "Admin")],
        "ChatRoleEnum": [("user", "User"), ("assistant", "Assistant")],
        "MenuTypeEnum": [("kr", "Korean"), ("premium", "Premium"), ("takeout", "Takeout")],
        "TransactionTypeEnum": [("charge", "Charge"), ("deduct", "Deduct"), ("refund", "Refund")],
    },
}

CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.getenv(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin
]

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
CELERY_BEAT_SCHEDULE = {
    "process-reservation-no-shows": {
        "task": "reservations.tasks.process_no_shows",
        "schedule": 900,
    },
    "delete-expired-chat-messages": {
        "task": "chatbot.tasks.delete_expired_chat_messages",
        "schedule": 3600,
    },
}
TOSS_PAYMENTS_SECRET_KEY = os.getenv("TOSS_PAYMENTS_SECRET_KEY", "")
TOSS_PAYMENTS_CONFIRM_URL = os.getenv(
    "TOSS_PAYMENTS_CONFIRM_URL",
    "https://api.tosspayments.com/v1/payments/confirm",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "45"))

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# api.hakchelin.cloud에서 발급한 CSRF 토큰을 hakchelin.cloud의 Nuxt 앱이
# 읽어 mutation 헤더에 실을 수 있도록 한다. 세션 쿠키는 API host-only로
# 유지해 불필요하게 넓은 범위로 전송하지 않는다.
CSRF_COOKIE_DOMAIN = os.getenv("DJANGO_CSRF_COOKIE_DOMAIN") or None
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# 로컬과 테스트에서는 비활성화하고, Caddy 뒤의 운영 환경에서만 명시적으로
# HTTPS redirect/HSTS를 켠다. HSTS는 HTTPS가 정상 검증된 도메인에만 설정한다.
SECURE_SSL_REDIRECT = env_flag("DJANGO_SECURE_SSL_REDIRECT")
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_flag("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_flag("DJANGO_SECURE_HSTS_PRELOAD")
