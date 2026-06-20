from django.db import models
from django.contrib.auth.models import User
from schedule.models import Member


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    belt = models.CharField('띠/단', max_length=20, choices=Member.BELT_CHOICES)

    class Meta:
        verbose_name = '사용자 프로필'
        verbose_name_plural = '사용자 프로필 목록'

    def __str__(self):
        status = '승인됨' if self.user.is_active else '대기중'
        return f'{self.user.get_full_name()} ({self.get_belt_display()}) - {status}'
