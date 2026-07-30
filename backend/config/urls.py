from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from legacy_bridge.views import MenuListView, MyProfileView, MyReservationListView, MyTransactionListView


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/menus/", MenuListView.as_view(), name="menu-list"),
    path("api/v1/me/", MyProfileView.as_view(), name="my-profile"),
    path("api/v1/reservations/me/", MyReservationListView.as_view(), name="my-reservation-list"),
    path("api/v1/wallet/transactions/me/", MyTransactionListView.as_view(), name="my-transaction-list"),
]
