from django.conf import settings
from django.http import JsonResponse


class WriteBlockMiddleware:
    """점검 창에 API의 상태 변경 요청을 일괄 차단한다."""

    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.DJANGO_WRITE_BLOCKED
            and request.method in self.unsafe_methods
            and request.path.startswith("/api/")
        ):
            response = JsonResponse(
                {"detail": "데이터 이전을 위한 점검 중입니다. 잠시 후 다시 시도해 주세요."},
                status=503,
            )
            response["Retry-After"] = "1800"
            return response
        return self.get_response(request)
