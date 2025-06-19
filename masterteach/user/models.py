# user/models.py
from django.contrib.auth.models import AbstractUser, Group, Permission 
from django.db import models
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    email = models.EmailField(
        _('email address'),
        unique=True,
        validators=[EmailValidator()],
        error_messages={
            'unique': _("A user with that email already exists."),
        }
    )
    mfa_secret = models.CharField(max_length=32, blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
