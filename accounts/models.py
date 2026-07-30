from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)

    def __str__(self):
        return f'{self.username} ({self.first_name} {self.last_name})'
