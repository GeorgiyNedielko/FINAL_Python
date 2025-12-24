
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, EmailTokenObtainPairView, UserListAdminView
from .views import UserBlockAPIView


urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", EmailTokenObtainPairView.as_view()),
    path("refresh/", TokenRefreshView.as_view()),
    path("admin/users/", UserListAdminView.as_view()),
    path("users/<int:user_id>/block/", UserBlockAPIView.as_view(), name="user_block"),

]
