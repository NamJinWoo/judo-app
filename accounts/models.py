from django.db import models
from django.contrib.auth.models import User
from schedule.models import Member


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    belt = models.CharField('띠/단', max_length=20, choices=Member.BELT_CHOICES)

    class Meta:
        verbose_name = '사용자 프로필'
        verbose_name_plural = '사용자 프로필 목록'

    BELT_COLORS = {
        'white':  {'bg': '#ffffff', 'text': '#1a1a2e', 'border': '#ced4da'},
        'yellow': {'bg': '#ffd700', 'text': '#1a1a2e', 'border': '#ffd700'},
        'green':  {'bg': '#198754', 'text': '#ffffff', 'border': '#198754'},
        'blue':   {'bg': '#0d6efd', 'text': '#ffffff', 'border': '#0d6efd'},
        'brown':  {'bg': '#795548', 'text': '#ffffff', 'border': '#795548'},
    }

    ROMAN = {'1': 'Ⅰ', '2': 'Ⅱ', '3': 'Ⅲ', '4': 'Ⅳ', '5': 'Ⅴ', '6': 'Ⅵ'}

    def get_belt_color(self):
        if self.belt and self.belt.startswith('black'):
            return {'bg': '#1a1a2e', 'text': '#ffd700', 'border': '#1a1a2e'}
        return self.BELT_COLORS.get(self.belt, {'bg': '#ffc107', 'text': '#1a1a2e', 'border': '#ffc107'})

    def get_belt_roman(self):
        if self.belt and self.belt.startswith('black'):
            return self.ROMAN.get(self.belt[-1], '')
        return ''

    def __str__(self):
        status = '승인됨' if self.user.is_active else '대기중'
        return f'{self.user.get_full_name()} ({self.get_belt_display()}) - {status}'
