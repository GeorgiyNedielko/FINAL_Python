from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .jwt import EmailTokenObtainPairSerializer
from rest_framework import generics, permissions
from .serializers import RegisterSerializer
from rest_framework import status
from rest_framework.response import Response
from .models import UserBlock


from rest_framework.viewsets import ReadOnlyModelViewSet


from .serializers import UserSerializer

from rest_framework.permissions import IsAdminUser


from django.contrib.auth import get_user_model


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class UserAdminViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class UserListAdminView(generics.ListAPIView):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class UserBlockAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):

        reason = request.data.get("reason", "Заблокирован администратором")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        UserBlock.objects.get_or_create(
            user=user,
            defaults={"reason": reason},
        )

        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])

        return Response(
            {"status": "blocked", "user_id": user.id},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, user_id):

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        UserBlock.objects.filter(user=user).delete()

        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {"status": "unblocked", "user_id": user.id},
            status=status.HTTP_200_OK,
        )


