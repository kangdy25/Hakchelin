import uuid
from dataclasses import dataclass

import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header


@dataclass(frozen=True)
class SupabasePrincipal:
    id: uuid.UUID
    email: str | None = None
    role: str = "student"

    @property
    def is_authenticated(self) -> bool:
        return True


class SupabaseJWTAuthentication(BaseAuthentication):
    """Validate a Supabase bearer token during the read-only bridge period."""

    keyword = b"bearer"

    def authenticate(self, request):
        authorization = get_authorization_header(request).split()
        if not authorization:
            return None
        if len(authorization) != 2 or authorization[0].lower() != self.keyword:
            raise exceptions.AuthenticationFailed("유효하지 않은 Authorization 헤더입니다.")

        token = authorization[1].decode("utf-8")
        payload = self._decode(token)
        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as error:
            raise exceptions.AuthenticationFailed("Supabase 토큰의 사용자 식별자가 유효하지 않습니다.") from error

        return SupabasePrincipal(id=user_id, email=payload.get("email"), role=payload.get("role", "student")), token

    def _decode(self, token: str) -> dict:
        options = {"verify_aud": bool(settings.SUPABASE_JWT_AUDIENCE)}
        kwargs = {
            "audience": settings.SUPABASE_JWT_AUDIENCE or None,
            "issuer": settings.SUPABASE_JWT_ISSUER or None,
            "options": options,
        }
        try:
            if settings.SUPABASE_JWT_SECRET:
                return jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], **kwargs)
            if settings.SUPABASE_JWT_JWKS_URL:
                signing_key = jwt.PyJWKClient(settings.SUPABASE_JWT_JWKS_URL).get_signing_key_from_jwt(token).key
                return jwt.decode(token, signing_key, algorithms=["ES256", "RS256"], **kwargs)
        except jwt.PyJWTError as error:
            raise exceptions.AuthenticationFailed("Supabase 토큰을 검증할 수 없습니다.") from error
        raise exceptions.AuthenticationFailed("Supabase JWT 검증 설정이 없습니다.")
