import json

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from api_serializers import (
    AdminPointSerializer,
    AdminRoleSerializer,
    AiLogSerializer,
    AmountSerializer,
    ChatMessageSerializer,
    ChatRequestSerializer,
    CsrfReadySerializer,
    LoginSerializer,
    MenuSerializer,
    MenuWriteSerializer,
    PointOrderSerializer,
    PointPaymentConfirmSerializer,
    PointPaymentResultSerializer,
    PointTransactionSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
    SignupSerializer,
    UserSerializer,
)
from chatbot.models import AiLog, ChatMessage
from chatbot.services import ChatbotError, generate_chat_answer
from meals.models import Menu
from payments.gateways import confirm_toss_payment
from payments.models import PointOrder
from payments.services import PaymentError, confirm_paid_order, create_point_order
from reservations.models import Reservation
from reservations.services import (
    ReservationError,
    admin_cancel_reservation,
    cancel_reservation,
    reserve_menu,
    use_reservation,
)
from wallet.models import PointTransaction
from wallet.services import WalletError, donate_points


class DjangoAuthenticatedView(APIView):
    """
    세션 인증 및 로그인 여부 검증이 필요한 API 뷰의 공통 기본 클래스.

    모든 하위 뷰에 Django 세션 인증(SessionAuthentication)과
    로그인 필수 권한(IsAuthenticated)을 기본으로 적용합니다.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]


class AdminPermission(permissions.BasePermission):
    """
    관리자(Admin) 권한 확인을 위한 커스텀 Permission 클래스.

    요청자가 인증된 상태이며 사용자 역할(role)이 ADMIN인 경우에만 접근을 허용합니다.
    """
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == User.Role.ADMIN)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """
    클라이언트에 CSRF 쿠키를 주입하기 위한 엔드포인트.

    SPA/프론트엔드 애플리케이션 초기 로드 시 호출되어 브라우저에 'csrftoken' 쿠키를 세팅합니다.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=CsrfReadySerializer)
    def get(self, request):
        return Response({"csrf": "ready"})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """
    이메일과 비밀번호 기반의 세션 로그인 처리 뷰.

    인증 성공 시 Django 세션을 시작하고 로그인된 사용자 정보를 반환합니다.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LoginSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise exceptions.AuthenticationFailed("이메일 또는 비밀번호가 올바르지 않습니다.")
        login(request, user)
        return Response(UserSerializer(user).data)


@method_decorator(csrf_protect, name="dispatch")
class SignupView(APIView):
    """
    신규 사용자 회원가입 처리 뷰.

    이메일/학번 중복 검사 및 패스워드 정책 검증을 통과한 신규 계정을 생성합니다.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=SignupSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if User.objects.filter(email=data["email"]).exists():
            raise exceptions.ValidationError("이미 가입된 이메일입니다.")
        if User.objects.filter(student_id=data["student_id"]).exists():
            raise exceptions.ValidationError("이미 등록된 학번입니다.")
        user = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            name=data["name"],
            student_id=data["student_id"],
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LogoutView(DjangoAuthenticatedView):
    """
    사용자 로그아웃 처리 뷰.

    현재 브라우저에 할당된 세션 데이터를 파기합니다.
    """
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(DjangoAuthenticatedView):
    """현재 로그인된 사용자의 본인 프로필 정보 조회 뷰"""
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class MenuListCreateView(APIView):
    authentication_classes = [SessionAuthentication]

    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == "GET" else [AdminPermission()]

    @extend_schema(
        parameters=[
            OpenApiParameter("active_only", OpenApiTypes.BOOL),
            OpenApiParameter("from_date", OpenApiTypes.DATE),
        ],
        responses=MenuSerializer(many=True),
    )
    def get(self, request):
        queryset = Menu.objects.order_by("meal_date", "meal_time")
        if request.query_params.get("active_only") == "true":
            queryset = queryset.filter(is_active=True)
        if request.query_params.get("from_date"):
            queryset = queryset.filter(meal_date__gte=request.query_params["from_date"])
        return Response(MenuSerializer(queryset, many=True).data)

    @extend_schema(request=MenuWriteSerializer, responses={201: MenuSerializer})
    def post(self, request):
        serializer = MenuWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menu = serializer.save()
        return Response(MenuSerializer(menu).data, status=status.HTTP_201_CREATED)


class MenuDetailView(DjangoAuthenticatedView):
    permission_classes = [AdminPermission]

    @extend_schema(request=MenuWriteSerializer, responses=MenuSerializer)
    def patch(self, request, menu_id):
        menu = get_object_or_404(Menu, id=menu_id)
        serializer = MenuWriteSerializer(menu, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MenuSerializer(menu).data)

    @extend_schema(responses={204: None})
    def delete(self, request, menu_id):
        menu = get_object_or_404(Menu, id=menu_id)
        menu.is_active = False
        menu.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationCreateView(DjangoAuthenticatedView):
    @extend_schema(request=ReservationCreateSerializer, responses={201: ReservationSerializer})
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            reservation = reserve_menu(
                user=request.user,
                menu_id=data["menu_id"],
                options=data["options"],
                submitted_total=data["total_price"],
            )
        except (ReservationError, Menu.DoesNotExist) as error:
            raise exceptions.ValidationError(str(error)) from error
        reservation = Reservation.objects.select_related("user", "menu").get(id=reservation.id)
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class MyReservationsView(DjangoAuthenticatedView):
    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = Reservation.objects.filter(user=request.user).select_related("user", "menu")
        return Response(ReservationSerializer(queryset, many=True).data)


class ReservationCancelView(DjangoAuthenticatedView):
    @extend_schema(request=None, responses=ReservationSerializer)
    def post(self, request, reservation_id):
        try:
            reservation = cancel_reservation(user=request.user, reservation_id=reservation_id)
        except (ReservationError, Reservation.DoesNotExist) as error:
            raise exceptions.ValidationError(str(error)) from error
        reservation = Reservation.objects.select_related("user", "menu").get(id=reservation.id)
        return Response(ReservationSerializer(reservation).data)


class AdminReservationActionView(DjangoAuthenticatedView):
    permission_classes = [AdminPermission]

    @extend_schema(request=None, responses=ReservationSerializer)
    def post(self, request, reservation_id, action):
        try:
            if action == "use":
                reservation = use_reservation(reservation_id=reservation_id)
            elif action == "cancel":
                reservation = admin_cancel_reservation(reservation_id=reservation_id)
            else:
                raise exceptions.NotFound()
        except (ReservationError, Reservation.DoesNotExist) as error:
            raise exceptions.ValidationError(str(error)) from error
        reservation = Reservation.objects.select_related("user", "menu").get(id=reservation.id)
        return Response(ReservationSerializer(reservation).data)


class MyTransactionsView(DjangoAuthenticatedView):
    @extend_schema(responses=PointTransactionSerializer(many=True))
    def get(self, request):
        queryset = PointTransaction.objects.filter(user=request.user).select_related("user")
        return Response(PointTransactionSerializer(queryset, many=True).data)


class DonationView(DjangoAuthenticatedView):
    @extend_schema(request=AmountSerializer, responses={201: PointTransactionSerializer})
    def post(self, request):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            point_transaction = donate_points(user=request.user, amount=serializer.validated_data["amount"])
        except WalletError as error:
            raise exceptions.ValidationError(str(error)) from error
        point_transaction = PointTransaction.objects.select_related("user").get(id=point_transaction.id)
        return Response(PointTransactionSerializer(point_transaction).data, status=status.HTTP_201_CREATED)


class PointOrderView(DjangoAuthenticatedView):
    @extend_schema(request=AmountSerializer, responses={201: PointOrderSerializer})
    def post(self, request):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = create_point_order(user=request.user, amount=serializer.validated_data["amount"])
        except PaymentError as error:
            raise exceptions.ValidationError(str(error)) from error
        return Response(PointOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class PointPaymentConfirmView(DjangoAuthenticatedView):
    @extend_schema(request=PointPaymentConfirmSerializer, responses=PointPaymentResultSerializer)
    def post(self, request):
        serializer = PointPaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = get_object_or_404(PointOrder, order_id=data["order_id"], user=request.user)
        if order.status == PointOrder.Status.PAID:
            return Response(
                {
                    "order_id": order.order_id,
                    "status": order.status,
                    "point_amount": order.point_amount,
                }
            )
        if order.amount != data["amount"]:
            raise exceptions.ValidationError("주문 금액이 일치하지 않습니다.")
        try:
            toss_response = confirm_toss_payment(
                payment_key=data["payment_key"],
                order_id=data["order_id"],
                amount=data["amount"],
            )
            order = confirm_paid_order(
                user=request.user,
                order_id=data["order_id"],
                payment_key=data["payment_key"],
                approved_amount=data["amount"],
                toss_response=toss_response,
            )
        except (PaymentError, PointOrder.DoesNotExist) as error:
            raise exceptions.ValidationError(str(error)) from error
        return Response(
            {
                "order_id": order.order_id,
                "status": order.status,
                "point_amount": order.point_amount,
            }
        )


class AdminUsersView(DjangoAuthenticatedView):
    """[관리자 전용] 전체 사용자 목록 조회 뷰"""
    permission_classes = [AdminPermission]

    @extend_schema(responses=UserSerializer(many=True))
    def get(self, request):
        return Response(UserSerializer(User.objects.order_by("student_id"), many=True).data)


class AdminReservationsView(DjangoAuthenticatedView):
    permission_classes = [AdminPermission]

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = Reservation.objects.select_related("user", "menu").order_by("-created_at")
        return Response(ReservationSerializer(queryset, many=True).data)


class AdminTransactionsView(DjangoAuthenticatedView):
    permission_classes = [AdminPermission]

    @extend_schema(responses=PointTransactionSerializer(many=True))
    def get(self, request):
        queryset = PointTransaction.objects.select_related("user").order_by("-created_at")[:50]
        return Response(PointTransactionSerializer(queryset, many=True).data)


class AdminAiLogsView(DjangoAuthenticatedView):
    permission_classes = [AdminPermission]

    @extend_schema(responses=AiLogSerializer(many=True))
    def get(self, request):
        queryset = AiLog.objects.select_related("user").order_by("-created_at")[:50]
        return Response(AiLogSerializer(queryset, many=True).data)


class AdminUserPointsView(DjangoAuthenticatedView):
    """
    [관리자 전용] 특정 사용자의 포인트를 강제 지급/차감하는 뷰.

    동시성 이슈를 방어하기 위해 DB 비관적 락(select_for_update)과 트랜잭션을 적용합니다.
    """
    permission_classes = [AdminPermission]

    @extend_schema(request=AdminPointSerializer, responses=UserSerializer)
    @transaction.atomic
    def post(self, request, user_id):
        user = get_object_or_404(User.objects.select_for_update(), id=user_id)
        serializer = AdminPointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        user.current_point += amount
        if user.current_point < 0:
            raise exceptions.ValidationError("포인트가 부족합니다.")
        user.save(update_fields=["current_point"])
        PointTransaction.objects.create(
            user=user,
            amount=amount,
            type=PointTransaction.Type.CHARGE if amount > 0 else PointTransaction.Type.DEDUCT,
            description=serializer.validated_data["description"],
        )
        return Response(UserSerializer(user).data)


class AdminUserRoleView(DjangoAuthenticatedView):
    """[관리자 전용] 특정 사용자의 시스템 역할(Role)을 변경하는 뷰"""
    permission_classes = [AdminPermission]

    @extend_schema(request=AdminRoleSerializer, responses=UserSerializer)
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = AdminRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.role = serializer.validated_data["role"]
        user.save()
        return Response(UserSerializer(user).data)


class ChatHistoryView(DjangoAuthenticatedView):
    @extend_schema(responses=ChatMessageSerializer(many=True))
    def get(self, request, conversation_id):
        queryset = ChatMessage.objects.filter(
            user=request.user,
            conversation_id=conversation_id,
        ).order_by("created_at")[:30]
        return Response(ChatMessageSerializer(queryset, many=True).data)


class ChatStreamView(DjangoAuthenticatedView):
    @extend_schema(
        request=ChatRequestSerializer,
        responses={(200, "text/event-stream"): OpenApiTypes.STR},
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        history = list(
            ChatMessage.objects.filter(
                user=request.user,
                conversation_id=data["conversation_id"],
            )
            .values("role", "content")
            .order_by("created_at")[:30]
        )
        def events():
            try:
                answer = generate_chat_answer(
                    user=request.user,
                    message=data["message"],
                    history=history,
                )
                with transaction.atomic():
                    ChatMessage.objects.create(
                        user=request.user,
                        conversation_id=data["conversation_id"],
                        role=ChatMessage.Role.USER,
                        content=data["message"],
                    )
                    ChatMessage.objects.create(
                        user=request.user,
                        conversation_id=data["conversation_id"],
                        role=ChatMessage.Role.ASSISTANT,
                        content=answer,
                    )
                yield f"event: token\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
                yield f"event: done\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
            except ChatbotError as error:
                yield f"event: error\ndata: {json.dumps({'error': str(error)}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
