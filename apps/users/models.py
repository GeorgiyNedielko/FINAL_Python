from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TENANT = "tenant", "Tenant"
        LANDLORD = "landlord", "Landlord"

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.TENANT)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email

class UserBlock(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reason = models.TextField()
    blocked_at = models.DateTimeField(auto_now_add=True)
