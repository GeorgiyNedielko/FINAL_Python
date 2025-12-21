from rest_framework_simplejwt.views import TokenObtainPairView
from .jwt import EmailTokenObtainPairSerializer
from rest_framework import generics, permissions
from .serializers import RegisterSerializer
from django.contrib.auth import get_user_model

from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAdminUser

from .serializers import UserSerializer

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