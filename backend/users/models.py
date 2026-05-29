from django.contrib.auth.models import AbstractUser
from django.db import models

from constants import EMAIL_MAX_LENGTH, USER_FIELD_MAX_LENGTH


class User(AbstractUser):
    email = models.EmailField(
        'адрес электронной почты',
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        'имя',
        max_length=USER_FIELD_MAX_LENGTH,
    )
    last_name = models.CharField(
        'фамилия',
        max_length=USER_FIELD_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'аватар',
        upload_to='users/',
        blank=True,
        null=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return self.email


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='пользователь',
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    author = models.ForeignKey(
        User,
        verbose_name='автор',
        on_delete=models.CASCADE,
        related_name='subscribers',
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_subscription',
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_subscription',
            ),
        ]

    def __str__(self):
        return f'{self.user} -> {self.author}'
