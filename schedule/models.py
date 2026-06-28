from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    BELT_CHOICES = [
        ('white', '흰띠'),
        ('yellow', '노란띠'),
        ('green', '초록띠'),
        ('blue', '파란띠'),
        ('brown', '갈색띠'),
        ('black1', '검은띠 1단'),
        ('black2', '검은띠 2단'),
        ('black3', '검은띠 3단'),
        ('black4', '검은띠 4단'),
        ('black5', '검은띠 5단'),
        ('black6', '검은띠 6단'),
    ]
    WEIGHT_CHOICES = [
        ('u60', '-60kg'),
        ('u66', '-66kg'),
        ('u73', '-73kg'),
        ('u81', '-81kg'),
        ('u90', '-90kg'),
        ('u100', '-100kg'),
        ('o100', '+100kg'),
        ('u48', '-48kg (여)'),
        ('u52', '-52kg (여)'),
        ('u57', '-57kg (여)'),
        ('u63', '-63kg (여)'),
        ('u70', '-70kg (여)'),
        ('u78', '-78kg (여)'),
        ('o78', '+78kg (여)'),
    ]

    name = models.CharField('이름', max_length=50)
    birth_date = models.DateField('생년월일', null=True, blank=True)
    belt = models.CharField('띠/단', max_length=20, choices=BELT_CHOICES, default='white')
    weight_class = models.CharField('체급', max_length=10, choices=WEIGHT_CHOICES, blank=True)
    phone = models.CharField('연락처', max_length=20, blank=True)
    join_date = models.DateField('등록일', auto_now_add=True)
    is_active = models.BooleanField('활성', default=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '회원'
        verbose_name_plural = '회원 목록'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_belt_display()})'


class TrainingSession(models.Model):
    date = models.DateField('날짜')
    start_time = models.TimeField('시작 시간')
    end_time = models.TimeField('종료 시간')
    title = models.CharField('훈련 제목', max_length=100)
    location = models.CharField('장소', max_length=100, blank=True)
    description = models.TextField('훈련 내용', blank=True)
    attendees = models.ManyToManyField(Member, verbose_name='참석자', blank=True, related_name='trainings')

    class Meta:
        verbose_name = '훈련 일정'
        verbose_name_plural = '훈련 일정 목록'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f'{self.date} {self.title}'


class Competition(models.Model):
    name = models.CharField('대회명', max_length=200)
    start_date = models.DateField('시작일')
    end_date = models.DateField('종료일')
    location = models.CharField('장소', max_length=200, blank=True)
    organizer = models.CharField('주최', max_length=100, blank=True)
    participants = models.ManyToManyField(
        Member, verbose_name='참가 선수', blank=True,
        through='CompetitionResult', related_name='competitions'
    )
    note = models.TextField('비고', blank=True)

    class Meta:
        verbose_name = '대회 일정'
        verbose_name_plural = '대회 일정 목록'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.name} ({self.start_date})'


class CompetitionResult(models.Model):
    RESULT_CHOICES = [
        ('gold', '금메달'),
        ('silver', '은메달'),
        ('bronze', '동메달'),
        ('participated', '참가'),
        ('withdrew', '기권'),
    ]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, verbose_name='대회')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name='선수')
    weight_class = models.CharField('체급', max_length=20, blank=True)
    result = models.CharField('결과', max_length=20, choices=RESULT_CHOICES, default='participated')
    note = models.TextField('비고', blank=True)

    class Meta:
        verbose_name = '대회 결과'
        verbose_name_plural = '대회 결과 목록'

    def __str__(self):
        return f'{self.member.name} - {self.competition.name} ({self.get_result_display()})'


class AttendancePlan(models.Model):
    TIME_SLOT_CHOICES = [
        ('18:00', '오후 6시'),
        ('19:30', '오후 7시 30분'),
        ('21:00', '오후 9시'),
        ('11:00', '오전 11시'),
        ('13:00', '오후 1시'),
        ('15:00', '오후 3시'),
        ('사유회', '사유회'),
    ]

    # 요일(0=월 ~ 6=일)별 슬롯 순서
    WEEKDAY_SLOTS = {
        0: ['18:00', '19:30', '21:00'],
        1: ['18:00', '19:30', '21:00'],
        2: ['18:00', '19:30', '21:00'],
        3: ['18:00', '19:30', '21:00'],
        4: ['18:00', '19:30', '21:00'],
        5: ['11:00', '13:00'],
        6: ['사유회', '13:00', '15:00'],
    }

    @classmethod
    def get_slots_for_date(cls, d):
        codes = cls.WEEKDAY_SLOTS.get(d.weekday(), ['18:00', '19:30', '21:00'])
        label_map = dict(cls.TIME_SLOT_CHOICES)
        return [(code, label_map[code]) for code in codes]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자', related_name='attendance_plans')
    date = models.DateField('날짜')
    time_slot = models.CharField('시간대', max_length=10, choices=TIME_SLOT_CHOICES, default='18:00')
    confirmed = models.BooleanField('실제 출석 확인', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '참석 예정'
        verbose_name_plural = '참석 예정 목록'
        unique_together = ['user', 'date', 'time_slot']
        ordering = ['date', 'time_slot']

    def __str__(self):
        return f'{self.user.first_name} - {self.date} {self.get_time_slot_display()}'


class Announcement(models.Model):
    title = models.CharField('제목', max_length=200)
    content = models.TextField('내용')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작성자')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField('상단 고정', default=False)

    class Meta:
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항 목록'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class FeePayment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='fee_payments', verbose_name='회원')
    year = models.IntegerField('연도')
    month = models.IntegerField('월')
    paid = models.BooleanField('납부 여부', default=False)
    paid_at = models.DateField('납부일', null=True, blank=True)
    note = models.CharField('메모', max_length=100, blank=True)

    class Meta:
        verbose_name = '회비 납부'
        verbose_name_plural = '회비 납부 목록'
        unique_together = ['member', 'year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.member.name} {self.year}.{self.month:02d} {"납부" if self.paid else "미납"}'


class BeltPromotion(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='belt_promotions', verbose_name='회원')
    belt = models.CharField('승급 띠/단', max_length=20, choices=Member.BELT_CHOICES)
    promoted_at = models.DateField('승급일')
    note = models.CharField('메모', max_length=200, blank=True)

    class Meta:
        verbose_name = '띠 승급 이력'
        verbose_name_plural = '띠 승급 이력 목록'
        ordering = ['-promoted_at']

    def __str__(self):
        return f'{self.member.name} → {self.get_belt_display()} ({self.promoted_at})'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField('메시지', max_length=300)
    link = models.CharField('링크', max_length=200, blank=True)
    is_read = models.BooleanField('읽음', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '알림'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.first_name} - {self.message[:30]}'


class PushSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='push_subscription')
    endpoint = models.TextField()
    p256dh = models.TextField()
    auth = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '푸시 구독'

    def __str__(self):
        return f'{self.user.first_name} - push'
