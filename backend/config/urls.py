from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api_views import (
    AdminAiLogsView,
    AdminReservationActionView,
    AdminReservationsView,
    AdminTransactionsView,
    AdminUserPointsView,
    AdminUserRoleView,
    AdminUsersView,
    ChatHistoryView,
    ChatStreamView,
    CsrfView,
    DonationView,
    LoginView,
    LogoutView,
    MenuDetailView,
    MenuListCreateView,
    MeView,
    MyReservationsView,
    MyTransactionsView,
    PointOrderView,
    PointPaymentConfirmView,
    ReservationCancelView,
    ReservationCreateView,
    SignupView,
)


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/csrf/", CsrfView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/signup/", SignupView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/me/", MeView.as_view()),
    path("api/menus/", MenuListCreateView.as_view()),
    path("api/menus/<str:menu_id>/", MenuDetailView.as_view()),
    path("api/reservations/me/", MyReservationsView.as_view()),
    path("api/wallet/transactions/me/", MyTransactionsView.as_view()),
    path("api/reservations/", ReservationCreateView.as_view()),
    path("api/reservations/<uuid:reservation_id>/cancel/", ReservationCancelView.as_view()),
    path(
        "api/admin/reservations/<uuid:reservation_id>/<str:action>/",
        AdminReservationActionView.as_view(),
    ),
    path("api/wallet/donations/", DonationView.as_view()),
    path("api/payments/point-orders/", PointOrderView.as_view()),
    path("api/payments/point-orders/confirm/", PointPaymentConfirmView.as_view()),
    path("api/admin/users/", AdminUsersView.as_view()),
    path("api/admin/reservations/", AdminReservationsView.as_view()),
    path("api/admin/transactions/", AdminTransactionsView.as_view()),
    path("api/admin/ai-logs/", AdminAiLogsView.as_view()),
    path("api/admin/users/<uuid:user_id>/points/", AdminUserPointsView.as_view()),
    path("api/admin/users/<uuid:user_id>/role/", AdminUserRoleView.as_view()),
    path("api/chat/<uuid:conversation_id>/", ChatHistoryView.as_view()),
    path("api/chat/stream/", ChatStreamView.as_view()),
]
