"""
청림유도관 전체 기능 테스트
실행: python manage.py test schedule accounts
"""
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import UserProfile
from schedule.models import (
    Member, AttendancePlan, Announcement,
    FeePayment, BeltPromotion, Notification, PushSubscription,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def next_weekday(weekday):
    """다음으로 오는 특정 요일의 날짜 (0=월 ~ 6=일)"""
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def make_user(name, belt='white', is_staff=False, password='pass1234'):
    user = User.objects.create_user(
        username=name, password=password, first_name=name, is_staff=is_staff
    )
    UserProfile.objects.create(user=user, belt=belt)
    return user


def make_member(name='홍길동', belt='white'):
    return Member.objects.create(name=name, belt=belt)


# ── 1. 모델: 요일별 슬롯 ────────────────────────────────────────────────────────

class AttendanceSlotModelTest(TestCase):
    """AttendancePlan.get_slots_for_date() 요일별 분기"""

    def test_weekday_mon_to_fri(self):
        for wd in range(5):  # 0(월) ~ 4(금)
            d = next_weekday(wd)
            codes = [s[0] for s in AttendancePlan.get_slots_for_date(d)]
            self.assertEqual(codes, ['18:00', '19:30', '21:00'],
                             f"요일 {wd} 슬롯 불일치")

    def test_saturday_slots(self):
        codes = [s[0] for s in AttendancePlan.get_slots_for_date(next_weekday(5))]
        self.assertEqual(codes, ['11:00', '13:00'])

    def test_sunday_slots(self):
        codes = [s[0] for s in AttendancePlan.get_slots_for_date(next_weekday(6))]
        self.assertEqual(codes, ['사유회', '13:00', '15:00'])

    def test_all_days_have_slots(self):
        base = next_weekday(0)
        for i in range(7):
            d = base + timedelta(days=i)
            self.assertGreater(len(AttendancePlan.get_slots_for_date(d)), 0)


# ── 2. 모델: 띠 색상·로마숫자 ──────────────────────────────────────────────────

class BeltModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')

    def _profile(self, belt):
        UserProfile.objects.filter(user=self.user).delete()
        return UserProfile.objects.create(user=self.user, belt=belt)

    def test_color_belt_backgrounds(self):
        expected = {
            'white': '#ffffff', 'yellow': '#ffd700',
            'green': '#198754', 'blue': '#0d6efd', 'brown': '#795548',
        }
        for belt, bg in expected.items():
            self.assertEqual(self._profile(belt).get_belt_color()['bg'], bg)

    def test_black_belt_color(self):
        c = self._profile('black3').get_belt_color()
        self.assertEqual(c['bg'], '#1a1a2e')
        self.assertEqual(c['text'], '#ffd700')

    def test_roman_numerals(self):
        for i, roman in enumerate(['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ'], 1):
            self.assertEqual(self._profile(f'black{i}').get_belt_roman(), roman)

    def test_no_roman_for_color_belts(self):
        for belt in ['white', 'yellow', 'green', 'blue', 'brown']:
            self.assertEqual(self._profile(belt).get_belt_roman(), '')

    def test_no_orange_belt_in_choices(self):
        self.assertNotIn('orange', [c[0] for c in Member.BELT_CHOICES])


# ── 3. 인증 ────────────────────────────────────────────────────────────────────

class AuthTest(TestCase):

    def test_register_success(self):
        resp = self.client.post(reverse('accounts:register'), {
            'name': '신규회원', 'belt': 'white',
            'password1': 'pass1234', 'password2': 'pass1234',
        })
        self.assertRedirects(resp, reverse('schedule:home'))
        self.assertTrue(User.objects.filter(username='신규회원').exists())
        self.assertEqual(UserProfile.objects.get(user__username='신규회원').belt, 'white')

    def test_register_duplicate_name_blocked(self):
        make_user('중복이름')
        resp = self.client.post(reverse('accounts:register'), {
            'name': '중복이름', 'belt': 'white',
            'password1': 'pass1234', 'password2': 'pass1234',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(username='중복이름').count(), 1)

    def test_register_auto_login(self):
        self.client.post(reverse('accounts:register'), {
            'name': '자동로그인', 'belt': 'white',
            'password1': 'pass1234', 'password2': 'pass1234',
        })
        self.assertEqual(self.client.get(reverse('schedule:home')).status_code, 200)

    def test_login_success(self):
        make_user('로그인유저')
        resp = self.client.post(reverse('accounts:login'), {
            'name': '로그인유저', 'password': 'pass1234',
        })
        self.assertRedirects(resp, reverse('schedule:home'))

    def test_login_wrong_password(self):
        make_user('유저')
        resp = self.client.post(reverse('accounts:login'), {
            'name': '유저', 'password': 'wrongpass',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '올바르지 않습니다')

    def test_logout(self):
        make_user('유저')
        self.client.login(username='유저', password='pass1234')
        self.assertRedirects(
            self.client.get(reverse('accounts:logout')),
            reverse('accounts:login')
        )

    def test_unauthenticated_home_redirects(self):
        resp = self.client.get(reverse('schedule:home'))
        self.assertRedirects(
            resp, f"{reverse('accounts:login')}?next={reverse('schedule:home')}"
        )


# ── 4. 홈 ─────────────────────────────────────────────────────────────────────

class HomeTest(TestCase):

    def setUp(self):
        self.user = make_user('홈유저', belt='blue')
        self.client.login(username='홈유저', password='pass1234')

    def test_home_renders(self):
        self.assertEqual(self.client.get(reverse('schedule:home')).status_code, 200)

    def test_home_shows_username(self):
        self.assertContains(self.client.get(reverse('schedule:home')), '홈유저')

    def test_home_shows_this_month_count(self):
        today = date.today()
        AttendancePlan.objects.create(user=self.user, date=today, time_slot='18:00')
        resp = self.client.get(reverse('schedule:home'))
        self.assertContains(resp, '1')

    def test_home_shows_coaches(self):
        make_user('관장님', belt='black3', is_staff=True)
        self.assertContains(self.client.get(reverse('schedule:home')), '관장님')

    def test_home_coach_order_by_belt_desc(self):
        make_user('관장A', belt='black1', is_staff=True)
        make_user('관장B', belt='black3', is_staff=True)
        content = self.client.get(reverse('schedule:home')).content.decode()
        self.assertLess(content.index('관장B'), content.index('관장A'))

    def test_superuser_not_shown_as_coach(self):
        User.objects.create_superuser(username='슈퍼', password='pass1234')
        content = self.client.get(reverse('schedule:home')).content.decode()
        self.assertNotIn('슈퍼', content)


# ── 5. 출석 예정 화면 ──────────────────────────────────────────────────────────

class AttendancePageTest(TestCase):

    def setUp(self):
        self.user = make_user('출석유저')
        self.client.login(username='출석유저', password='pass1234')
        self.monday = next_weekday(0)

    def test_attendance_week_renders(self):
        self.assertEqual(
            self.client.get(reverse('schedule:attendance_week')).status_code, 200
        )

    def test_attendance_week_nav(self):
        iso = self.monday.isocalendar()
        resp = self.client.get(reverse('schedule:attendance_week_nav', args=[iso[0], iso[1]]))
        self.assertEqual(resp.status_code, 200)

    def test_attendance_month_renders(self):
        self.assertEqual(
            self.client.get(reverse('schedule:attendance_month')).status_code, 200
        )

    def test_attendance_month_nav(self):
        resp = self.client.get(reverse('schedule:attendance_month_nav', args=[2026, 6]))
        self.assertEqual(resp.status_code, 200)

    def test_my_attendance_renders(self):
        self.assertEqual(
            self.client.get(reverse('schedule:my_attendance')).status_code, 200
        )


# ── 6. 출석 토글 (핵심 기능) ────────────────────────────────────────────────────

class AttendanceToggleTest(TestCase):

    def setUp(self):
        self.user = make_user('토글유저')
        self.client.login(username='토글유저', password='pass1234')
        self.monday = next_weekday(0)
        self.saturday = next_weekday(5)
        self.sunday = next_weekday(6)

    def _toggle(self, d, slot):
        return self.client.post(reverse('schedule:attendance_toggle'), {
            'date': d.isoformat(), 'time_slot': slot,
        })

    # 정상 등록/취소
    def test_add_weekday_slot(self):
        resp = self._toggle(self.monday, '18:00')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['attending'])
        self.assertTrue(AttendancePlan.objects.filter(
            user=self.user, date=self.monday, time_slot='18:00').exists())

    def test_remove_existing_plan(self):
        AttendancePlan.objects.create(user=self.user, date=self.monday, time_slot='19:30')
        resp = self._toggle(self.monday, '19:30')
        self.assertFalse(resp.json()['attending'])
        self.assertFalse(AttendancePlan.objects.filter(
            user=self.user, date=self.monday, time_slot='19:30').exists())

    def test_all_weekday_slots(self):
        for slot in ['18:00', '19:30', '21:00']:
            resp = self._toggle(self.monday, slot)
            self.assertEqual(resp.status_code, 200, f"슬롯 {slot} 등록 실패")
            self._toggle(self.monday, slot)  # 취소

    # 토요일 슬롯
    def test_saturday_valid_slot(self):
        self.assertEqual(self._toggle(self.saturday, '11:00').status_code, 200)
        self.assertEqual(self._toggle(self.saturday, '13:00').status_code, 200)

    def test_saturday_weekday_slot_rejected(self):
        self.assertEqual(self._toggle(self.saturday, '18:00').status_code, 400)
        self.assertEqual(self._toggle(self.saturday, '19:30').status_code, 400)
        self.assertEqual(self._toggle(self.saturday, '21:00').status_code, 400)

    # 일요일 슬롯
    def test_sunday_valid_slots(self):
        self.assertEqual(self._toggle(self.sunday, '사유회').status_code, 200)
        self.assertEqual(self._toggle(self.sunday, '13:00').status_code, 200)
        self.assertEqual(self._toggle(self.sunday, '15:00').status_code, 200)

    def test_sunday_weekday_slot_rejected(self):
        self.assertEqual(self._toggle(self.sunday, '18:00').status_code, 400)

    # 날짜 검증
    def test_past_date_rejected(self):
        yesterday = date.today() - timedelta(days=1)
        self.assertEqual(self._toggle(yesterday, '18:00').status_code, 400)

    def test_invalid_date_rejected(self):
        resp = self.client.post(reverse('schedule:attendance_toggle'), {
            'date': 'not-a-date', 'time_slot': '18:00',
        })
        self.assertEqual(resp.status_code, 400)

    # 응답 데이터
    def test_response_includes_attendee_names(self):
        other = make_user('같이출석')
        AttendancePlan.objects.create(user=other, date=self.monday, time_slot='18:00')
        data = self._toggle(self.monday, '18:00').json()
        self.assertIn('같이출석', data['names'])
        self.assertEqual(data['count'], 2)

    def test_unauthenticated_redirect(self):
        self.client.logout()
        resp = self._toggle(self.monday, '18:00')
        self.assertEqual(resp.status_code, 302)


# ── 7. 내 정보 수정 ────────────────────────────────────────────────────────────

class ProfileEditTest(TestCase):

    def setUp(self):
        self.user = make_user('프로필유저', belt='blue')
        self.client.login(username='프로필유저', password='pass1234')

    def test_get_renders(self):
        resp = self.client.get(reverse('schedule:my_profile_edit'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '프로필유저')

    def test_name_change(self):
        self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '새이름', 'belt': 'green',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, '새이름')
        self.assertEqual(self.user.first_name, '새이름')

    def test_belt_change(self):
        self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'brown',
        })
        self.assertEqual(UserProfile.objects.get(user=self.user).belt, 'brown')

    def test_duplicate_name_rejected(self):
        make_user('이미있는이름')
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '이미있는이름', 'belt': 'blue',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '이미 사용 중인')

    def test_empty_name_rejected(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '', 'belt': 'blue',
        })
        self.assertContains(resp, '이름을 입력해 주세요')

    def test_password_change_success(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'blue',
            'current_password': 'pass1234',
            'new_password1': 'newpass5678',
            'new_password2': 'newpass5678',
        })
        self.assertRedirects(resp, reverse('schedule:my_attendance'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass5678'))

    def test_wrong_current_password_rejected(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'blue',
            'current_password': 'wrongpass',
            'new_password1': 'newpass5678',
            'new_password2': 'newpass5678',
        })
        self.assertContains(resp, '현재 비밀번호가 올바르지 않습니다')

    def test_password_mismatch_rejected(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'blue',
            'current_password': 'pass1234',
            'new_password1': 'newpass1',
            'new_password2': 'newpass2',
        })
        self.assertContains(resp, '일치하지 않습니다')

    def test_short_password_rejected(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'blue',
            'current_password': 'pass1234',
            'new_password1': 'ab',
            'new_password2': 'ab',
        })
        self.assertContains(resp, '4자 이상')

    def test_success_redirects_to_my_attendance(self):
        resp = self.client.post(reverse('schedule:my_profile_edit'), {
            'name': '프로필유저', 'belt': 'blue',
        })
        self.assertRedirects(resp, reverse('schedule:my_attendance'))


# ── 8. 공지사항 ────────────────────────────────────────────────────────────────

class AnnouncementTest(TestCase):

    def setUp(self):
        self.regular = make_user('일반유저')
        self.staff = make_user('관장', is_staff=True)
        self.ann = Announcement.objects.create(
            title='테스트 공지', content='공지 내용입니다.', author=self.staff
        )

    def test_list_visible_to_regular(self):
        self.client.login(username='일반유저', password='pass1234')
        resp = self.client.get(reverse('schedule:announcement_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '테스트 공지')

    def test_detail_visible_to_regular(self):
        self.client.login(username='일반유저', password='pass1234')
        resp = self.client.get(reverse('schedule:announcement_detail', args=[self.ann.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '공지 내용입니다.')

    def test_create_blocked_for_regular(self):
        self.client.login(username='일반유저', password='pass1234')
        resp = self.client.get(reverse('schedule:announcement_create'))
        self.assertNotEqual(resp.status_code, 200)

    def test_create_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(reverse('schedule:announcement_create'), {
            'title': '새 공지', 'content': '새 내용', 'is_pinned': False,
        })
        self.assertRedirects(resp, reverse('schedule:announcement_list'))
        self.assertTrue(Announcement.objects.filter(title='새 공지').exists())

    def test_edit_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:announcement_edit', args=[self.ann.pk]), {
            'title': '수정된 공지', 'content': '수정 내용', 'is_pinned': False,
        })
        self.ann.refresh_from_db()
        self.assertEqual(self.ann.title, '수정된 공지')

    def test_delete_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:announcement_delete', args=[self.ann.pk]))
        self.assertFalse(Announcement.objects.filter(pk=self.ann.pk).exists())


# ── 9. 회원 관리 (관장 전용) ───────────────────────────────────────────────────

class MemberManagementTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.regular = make_user('일반')
        self.member = make_member('김철수', belt='blue')

    def test_member_list_blocked_for_regular(self):
        self.client.login(username='일반', password='pass1234')
        self.assertNotEqual(
            self.client.get(reverse('schedule:member_list')).status_code, 200
        )

    def test_member_list_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.get(reverse('schedule:member_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '김철수')

    def test_member_create(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(reverse('schedule:member_create'), {
            'name': '신규회원', 'belt': 'white',
            'weight_class': '', 'phone': '', 'note': '',
        })
        self.assertRedirects(resp, reverse('schedule:member_list'))
        self.assertTrue(Member.objects.filter(name='신규회원').exists())

    def test_member_detail(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.get(reverse('schedule:member_detail', args=[self.member.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '김철수')

    def test_member_edit(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:member_edit', args=[self.member.pk]), {
            'name': '김철수', 'belt': 'brown',
            'weight_class': '', 'phone': '', 'note': '',
        })
        self.member.refresh_from_db()
        self.assertEqual(self.member.belt, 'brown')

    def test_member_delete(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:member_delete', args=[self.member.pk]))
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())


# ── 10. 띠 승급 이력 ────────────────────────────────────────────────────────────

class BeltPromotionTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.member = make_member('이영희', belt='blue')

    def test_belt_promote(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:belt_promote', args=[self.member.pk]), {
            'belt': 'brown', 'promoted_at': '2026-06-01', 'note': '',
        })
        self.member.refresh_from_db()
        self.assertEqual(self.member.belt, 'brown')
        self.assertTrue(BeltPromotion.objects.filter(member=self.member, belt='brown').exists())

    def test_belt_promotion_delete_reverts_to_previous(self):
        self.client.login(username='관장', password='pass1234')
        BeltPromotion.objects.create(member=self.member, belt='blue', promoted_at='2025-01-01')
        promo = BeltPromotion.objects.create(member=self.member, belt='brown', promoted_at='2026-01-01')
        self.client.post(reverse('schedule:belt_promotion_delete', args=[promo.pk]))
        self.assertFalse(BeltPromotion.objects.filter(pk=promo.pk).exists())
        self.member.refresh_from_db()
        self.assertEqual(self.member.belt, 'blue')


# ── 11. 회비 납부 ────────────────────────────────────────────────────────────────

class FeePaymentTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.member = make_member('박지성')
        self.today = date.today()

    def test_fee_list_renders(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.get(reverse('schedule:fee_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '박지성')

    def test_fee_toggle_to_paid(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(reverse('schedule:fee_toggle', args=[self.member.pk]), {
            'year': self.today.year, 'month': self.today.month,
        })
        self.assertTrue(resp.json()['paid'])
        self.assertTrue(FeePayment.objects.get(
            member=self.member, year=self.today.year, month=self.today.month
        ).paid)

    def test_fee_toggle_to_unpaid(self):
        FeePayment.objects.create(
            member=self.member, year=self.today.year, month=self.today.month, paid=True
        )
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(reverse('schedule:fee_toggle', args=[self.member.pk]), {
            'year': self.today.year, 'month': self.today.month,
        })
        self.assertFalse(resp.json()['paid'])

    def test_fee_blocked_for_regular(self):
        make_user('일반')
        self.client.login(username='일반', password='pass1234')
        resp = self.client.get(reverse('schedule:fee_list'))
        self.assertNotEqual(resp.status_code, 200)


# ── 12. 사용자 관리 ──────────────────────────────────────────────────────────────

class UserManagementTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.regular = make_user('일반유저')

    def test_user_list_blocked_for_regular(self):
        self.client.login(username='일반유저', password='pass1234')
        self.assertNotEqual(
            self.client.get(reverse('schedule:user_list')).status_code, 200
        )

    def test_user_list_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        self.assertEqual(self.client.get(reverse('schedule:user_list')).status_code, 200)

    def test_toggle_staff_status(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:user_toggle_staff', args=[self.regular.pk]))
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.is_staff)

    def test_toggle_active_status(self):
        self.client.login(username='관장', password='pass1234')
        self.client.post(reverse('schedule:user_toggle_active', args=[self.regular.pk]))
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_active)

    def test_cannot_toggle_self(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(
            reverse('schedule:user_toggle_staff', args=[self.staff.pk])
        )
        self.assertEqual(resp.status_code, 400)


# ── 13. 대시보드 ──────────────────────────────────────────────────────────────────

class DashboardTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.regular = make_user('일반')

    def test_redirects_non_staff(self):
        self.client.login(username='일반', password='pass1234')
        self.assertRedirects(
            self.client.get(reverse('schedule:dashboard')),
            reverse('schedule:home')
        )

    def test_accessible_by_staff(self):
        self.client.login(username='관장', password='pass1234')
        self.assertEqual(self.client.get(reverse('schedule:dashboard')).status_code, 200)


# ── 14. 출석 확인 (관장용) ──────────────────────────────────────────────────────

class AttendanceConfirmTest(TestCase):

    def setUp(self):
        self.staff = make_user('관장', is_staff=True)
        self.regular = make_user('관원')
        self.monday = next_weekday(0)
        self.plan = AttendancePlan.objects.create(
            user=self.regular, date=self.monday, time_slot='18:00'
        )

    def test_confirm_page_renders(self):
        self.client.login(username='관장', password='pass1234')
        self.assertEqual(
            self.client.get(reverse('schedule:attendance_confirm')).status_code, 200
        )

    def test_confirm_specific_date_shows_attendee(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.get(
            reverse('schedule:attendance_confirm_date', args=[self.monday.isoformat()])
        )
        self.assertContains(resp, '관원')

    def test_confirm_toggle(self):
        self.client.login(username='관장', password='pass1234')
        resp = self.client.post(
            reverse('schedule:attendance_confirm_toggle'), {'plan_id': self.plan.pk}
        )
        self.assertEqual(resp.status_code, 200)
        self.plan.refresh_from_db()
        self.assertTrue(self.plan.confirmed)

    def test_confirm_blocked_for_regular(self):
        self.client.login(username='관원', password='pass1234')
        self.assertNotEqual(
            self.client.get(reverse('schedule:attendance_confirm')).status_code, 200
        )


# ── 15. Web Push 구독 ──────────────────────────────────────────────────────────

class PushSubscriptionTest(TestCase):

    def setUp(self):
        self.user = make_user('푸시유저')
        self.client.login(username='푸시유저', password='pass1234')
        self.sub_payload = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/test-endpoint',
            'keys': {
                'p256dh': 'BNxEGbqNifQQbDi2tE7H5SAvEdkpFacXTkFKJfDmGcBa',
                'auth': 'testauth1234',
            },
        }

    def _subscribe(self):
        import json
        return self.client.post(
            reverse('schedule:push_subscribe'),
            data=json.dumps(self.sub_payload),
            content_type='application/json',
        )

    def _unsubscribe(self):
        return self.client.post(reverse('schedule:push_unsubscribe'))

    def test_subscribe_creates_record(self):
        resp = self._subscribe()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        sub = PushSubscription.objects.get(user=self.user)
        self.assertEqual(sub.endpoint, self.sub_payload['endpoint'])
        self.assertEqual(sub.p256dh, self.sub_payload['keys']['p256dh'])
        self.assertEqual(sub.auth, self.sub_payload['keys']['auth'])

    def test_subscribe_upserts_on_repeat(self):
        self._subscribe()
        import json
        updated = dict(self.sub_payload, endpoint='https://fcm.googleapis.com/new-endpoint')
        self.client.post(
            reverse('schedule:push_subscribe'),
            data=json.dumps(updated),
            content_type='application/json',
        )
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)
        self.assertEqual(PushSubscription.objects.get(user=self.user).endpoint, updated['endpoint'])

    def test_unsubscribe_removes_record(self):
        self._subscribe()
        resp = self._unsubscribe()
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PushSubscription.objects.filter(user=self.user).exists())

    def test_unsubscribe_without_subscription_is_safe(self):
        resp = self._unsubscribe()
        self.assertEqual(resp.status_code, 200)

    def test_subscribe_requires_login(self):
        self.client.logout()
        import json
        resp = self.client.post(
            reverse('schedule:push_subscribe'),
            data=json.dumps(self.sub_payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 302)

    def test_subscribe_get_not_allowed(self):
        resp = self.client.get(reverse('schedule:push_subscribe'))
        self.assertEqual(resp.status_code, 405)


# ── 16. 출석 토글 → 알림 생성 ────────────────────────────────────────────────

class AttendanceToggleNotificationTest(TestCase):

    def setUp(self):
        self.user_a = make_user('유저A')
        self.user_b = make_user('유저B')
        self.monday = next_weekday(0)

    def _toggle(self, client, d, slot):
        return client.post(reverse('schedule:attendance_toggle'), {
            'date': d.isoformat(), 'time_slot': slot,
        })

    def test_new_registration_notifies_existing_attendees(self):
        # 유저A 먼저 등록
        AttendancePlan.objects.create(user=self.user_a, date=self.monday, time_slot='18:00')
        # 유저B가 같은 슬롯 등록
        client_b = self.client_class()
        client_b.login(username='유저B', password='pass1234')
        self._toggle(client_b, self.monday, '18:00')
        # 유저A에게 알림 생성 확인
        self.assertTrue(
            Notification.objects.filter(user=self.user_a, message__contains='유저B').exists()
        )

    def test_cancellation_notifies_remaining_attendees(self):
        # 둘 다 등록
        AttendancePlan.objects.create(user=self.user_a, date=self.monday, time_slot='18:00')
        AttendancePlan.objects.create(user=self.user_b, date=self.monday, time_slot='18:00')
        # 유저B가 취소
        client_b = self.client_class()
        client_b.login(username='유저B', password='pass1234')
        self._toggle(client_b, self.monday, '18:00')
        # 유저A에게 취소 알림 생성 확인
        self.assertTrue(
            Notification.objects.filter(user=self.user_a, message__contains='취소').exists()
        )

    def test_no_notification_when_alone(self):
        # 혼자 등록할 때는 알림 없어야 함
        client_a = self.client_class()
        client_a.login(username='유저A', password='pass1234')
        self._toggle(client_a, self.monday, '18:00')
        self.assertEqual(Notification.objects.count(), 0)
