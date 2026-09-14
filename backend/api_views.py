import json

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
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
    MenuQuerySerializer,
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
from chatbot.services import ChatbotError, stream_chat_answer
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
    """
    식단 목록 조회(GET) 및 신규 등록(POST)을 처리하는 뷰.

    HTTP 메서드에 따라 동적으로 권한을 분기하여, 조회는 모든 사용자에게 허용하고 신규 등록은 관리자에게만 허용합니다.
    """
    authentication_classes = [SessionAuthentication]

    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == "GET" else [AdminPermission()]

    @extend_schema(
        parameters=[MenuQuerySerializer],
        responses=MenuSerializer(many=True),
    )
    def get(self, request):
        query_serializer = MenuQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        filters = query_serializer.validated_data

        queryset = Menu.objects.order_by("meal_date", "meal_time")
        if filters["active_only"]:
            queryset = queryset.filter(is_active=True)
        if from_date := filters.get("from_date"):
            queryset = queryset.filter(meal_date__gte=from_date)
        return Response(MenuSerializer(queryset, many=True).data)

    @extend_schema(request=MenuWriteSerializer, responses={201: MenuSerializer})
    def post(self, request):
        serializer = MenuWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menu = serializer.save()
        return Response(MenuSerializer(menu).data, status=status.HTTP_201_CREATED)


class MenuDetailView(DjangoAuthenticatedView):
    """
    [관리자 전용] 특정 식단 메뉴의 상세 수정(PATCH) 및 비활성화/삭제(DELETE)를 처리하는 뷰.

    기본적으로 DjangoAuthenticatedView를 상속하며, 관리자 권한(AdminPermission)으로 격리되어 있습니다.
    """
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
    """
    식단 메뉴 신규 예약 신청 처리 뷰.

    클라이언트로부터 메뉴 ID, 옵션, 예상 결제 총액을 수신하여 유효성을 검증한 뒤,
    비즈니스 서비스 레이어(reserve_menu)를 호출해 원자적 결제 및 예약을 확정합니다.
    """
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
    """
    현재 로그인된 사용자의 본인 식권/예약 내역 전체 조회 뷰.

    세션 인증을 필수로 요구하며, 사용자 본인의 예약 목록을 최신순으로 반환합니다.
    """
    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = Reservation.objects.filter(user=request.user).select_related("user", "menu")
        return Response(ReservationSerializer(queryset, many=True).data)


class ReservationCancelView(DjangoAuthenticatedView):
    """
    사용자가 본인의 유효한 예약을 직접 취소하는 뷰.

    예약 마감 시간 전/후 여부에 따라 보증금 공제 여부를 차등 적용하는 환불 정책을 수행합니다.
    """
    @extend_schema(request=None, responses=ReservationSerializer)
    def post(self, request, reservation_id):
        try:
            reservation = cancel_reservation(user=request.user, reservation_id=reservation_id)
        except (ReservationError, Reservation.DoesNotExist) as error:
            raise exceptions.ValidationError(str(error)) from error
        
        reservation = Reservation.objects.select_related("user", "menu").get(id=reservation.id)
        return Response(ReservationSerializer(reservation).data)


class AdminReservationActionView(DjangoAuthenticatedView):
    """
    [관리자 전용] 특정 예약에 대한 상태 전이 액션(식권 사용 승인 또는 관리자 강제 취소)을 처리하는 뷰.

    URL의 action 파라미터에 따라 'use' 또는 'cancel'을 분기 실행합니다.
    """
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
    """
    현재 로그인한 사용자의 포인트 변동 내역(충전/차감/기부 등) 조회 뷰.

    세션 인증을 필수로 요구하며 본인의 거래 기록만 역순(최신순)으로 제공합니다.
    """
    @extend_schema(responses=PointTransactionSerializer(many=True))
    def get(self, request):
        queryset = PointTransaction.objects.filter(user=request.user).select_related("user")
        return Response(PointTransactionSerializer(queryset, many=True).data)


class DonationView(DjangoAuthenticatedView):
    """
    보유 포인트를 사용해 기부를 수행하는 뷰.

    지갑 서비스 레이어(donate_points)를 호출하여 비관적 락 기반의 원자적 차감을 실행합니다.
    """
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
    """
    포인트 충전을 위한 사전 주문(PointOrder) 생성 뷰.

    클라이언트로부터 충전 희망 금액을 입력받아 최소/최대 한도를 검증하고,
    토스페이먼츠 결제창 호출 시 전달할 고유 주문 번호(order_id)를 발급합니다.
    """
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
    """
    토스페이먼츠 결제창 인증 완료 후 최종 승인 확정 및 포인트 적립 뷰.

    클라이언트가 토스 SDK로부터 전달받은 paymentKey, orderId, amount를 수신하여
    금액 위변조 검증, 외부 PG사 승인 API 호출, 포인트 원자적 지급을 수행합니다.
    """
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
    """
    [관리자 전용] 시스템 전체 예약 현황 목록 조회 뷰.

    식당 관리자가 예약 현황 및 노쇼/취소 통계를 모니터링할 수 있도록 전체 데이터를 최신순으로 제공합니다.
    """
    permission_classes = [AdminPermission]

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = Reservation.objects.select_related("user", "menu").order_by("-created_at")
        return Response(ReservationSerializer(queryset, many=True).data)


class AdminTransactionsView(DjangoAuthenticatedView):
    """[관리자 전용] 시스템 전체 포인트 거래 내역 조회 뷰."""
    permission_classes = [AdminPermission]

    @extend_schema(responses=PointTransactionSerializer(many=True))
    def get(self, request):
        queryset = PointTransaction.objects.select_related("user").order_by("-created_at")[:50]
        return Response(PointTransactionSerializer(queryset, many=True).data)


class AdminAiLogsView(DjangoAuthenticatedView):
    """
    [관리자 전용] AI 추론 파이프라인 감사 로그 조회 뷰.

    시스템 전반에서 발생한 LLM 호출 이력, 단계별 추론 성공 여부, 지연 시간(Latency),
    에러 발생 내역을 최신순 상위 50건 조회하여 모니터링 대시보드에 제공합니다.
    """
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


def _recent_chat_history(*, user, conversation_id) -> list[dict]:
    """최근 대화 30개를 선택한 뒤 대화가 생성된 순서로 반환합니다."""

    history = list(
        ChatMessage.objects.filter(user=user, conversation_id=conversation_id)
        .values("role", "content")
        .order_by("-created_at", "-id")[:30]
    )
    history.reverse()
    return history


class ChatHistoryView(DjangoAuthenticatedView):
    """
    특정 대화 세션의 이전 메시지 이력 조회 뷰.

    요청자 본인의 특정 대화 쓰레드(conversation_id)에 속한 메시지를
    시간순으로 최대 30건 조회하여 클라이언트 화면에 말풍선 목록으로 렌더링합니다.
    """
    @extend_schema(responses=ChatMessageSerializer(many=True))
    def get(self, request, conversation_id):
        history = _recent_chat_history(
            user=request.user,
            conversation_id=conversation_id,
        )
        return Response(ChatMessageSerializer(history, many=True).data)


class ChatStreamView(DjangoAuthenticatedView):
    """
    AI 어시스턴트의 SSE 응답 전달 및 대화 저장 처리 뷰.

    클라이언트의 질문을 최근 대화 맥락과 함께 Gemini LLM 서비스에 전달하고,
    생성되는 답변 조각을 SSE(text/event-stream)의 token 이벤트로 즉시 전송하고,
    스트림이 정상적으로 끝나면 완성된 답변을 done 이벤트로 전송합니다.
    사용자 발화와 AI 응답은 단일 원자적 트랜잭션 내에서 ChatMessage로 영구 보관됩니다.
    """
    @extend_schema(
        request=ChatRequestSerializer,
        responses={(200, "text/event-stream"): OpenApiTypes.STR},
    )
    def post(self, request):
        # 입력 데이터 검증 (질문 1~100자 제한 및 UUID 형태의 세션 ID 검증)
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 멀티턴 컨텍스트 구성을 위해 동일 세션 내 최근 30개 발화 이력 추출
        history = _recent_chat_history(
            user=request.user,
            conversation_id=data["conversation_id"],
        )

        def events():
            try:
                # 각 조각은 수신 즉시 브라우저에 전달하되, 
                # 정상 완료 후 저장할 수 있도록 동일한 조각을 서버에서도 누적한다.
                answer_parts = []
                for text in stream_chat_answer(
                    user=request.user, message=data["message"], history=history
                ):
                    answer_parts.append(text)
                    yield f"event: token\ndata: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

                answer = "".join(answer_parts).strip()
                # Gemini 스트림을 끝까지 정상적으로 소비한 뒤에만 두 메시지를 저장한다.
                # 중간 오류나 연결 종료 시에는 이 블록에 도달하지 않아 부분 대화가 남지 않는다.
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
                # done에는 완성본을 넣어 프런트가 누락된 마지막 조각을 최종 보정할 수 있게 한다.
                yield f"event: done\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
            except ChatbotError as error:
                yield f"event: error\ndata: {json.dumps({'message': str(error)}, ensure_ascii=False)}\n\n"

        # 스트리밍 전용 HTTP 응답 객체 생성
        response = StreamingHttpResponse(events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        # Nginx 등 리버스 프록시의 응답 버퍼링 강제 해제 (이벤트 즉시 플러시)
        response["X-Accel-Buffering"] = "no"
        return response
