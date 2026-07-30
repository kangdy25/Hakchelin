from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SupabaseJWTAuthentication
from .repositories import get_profile, list_menus, list_reservations, list_transactions
from .serializers import MenuSerializer, PointTransactionSerializer, ProfileSerializer, ReservationSerializer


class MenuListView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="active_only", type=bool, required=False),
            OpenApiParameter(name="from_date", type=str, required=False),
        ],
        responses=MenuSerializer(many=True),
    )
    def get(self, request):
        active_only = request.query_params.get("active_only", "false").lower() == "true"
        from_date = request.query_params.get("from_date")
        return Response(MenuSerializer(list_menus(active_only=active_only, from_date=from_date), many=True).data)


class SupabaseAuthenticatedView(APIView):
    authentication_classes = [SupabaseJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


class MyProfileView(SupabaseAuthenticatedView):
    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        try:
            profile = get_profile(request.user.id)
        except ObjectDoesNotExist as error:
            raise exceptions.NotFound("사용자 프로필을 찾을 수 없습니다.") from error
        return Response(ProfileSerializer(profile).data)


class MyReservationListView(SupabaseAuthenticatedView):
    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        return Response(ReservationSerializer(list_reservations(request.user.id), many=True).data)


class MyTransactionListView(SupabaseAuthenticatedView):
    @extend_schema(responses=PointTransactionSerializer(many=True))
    def get(self, request):
        return Response(PointTransactionSerializer(list_transactions(request.user.id), many=True).data)
