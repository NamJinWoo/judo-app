import calendar
import json
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Member, TrainingSession, Competition, AttendancePlan, Announcement, Notification
from .forms import TrainingForm, CompetitionForm, AnnouncementForm, MemberForm
from accounts.models import UserProfile
from accounts.models import UserProfile


@login_required
def home(request):
    today = timezone.now().date()
    # 내 향후 출석 예정 (날짜+슬롯별, 다른 참석자 포함)
    my_plans = AttendancePlan.objects.filter(
        user=request.user, date__gte=today
    ).order_by('date', 'time_slot')

    upcoming = []
    for plan in my_plans:
        others = AttendancePlan.objects.filter(
            date=plan.date, time_slot=plan.time_slot
        ).exclude(user=request.user).select_related('user')
        upcoming.append({
            'date': plan.date,
            'slot_label': plan.get_time_slot_display(),
            'others': [p.user.first_name or p.user.username for p in others],
            'total': others.count() + 1,
        })

    # 이번 달 출석 일수 (오늘까지)
    this_month_days = AttendancePlan.objects.filter(
        user=request.user,
        date__year=today.year,
        date__month=today.month,
        date__lte=today,
    ).values('date').distinct().count()

    announcements = Announcement.objects.all()[:3]

    return render(request, 'schedule/home.html', {
        'today': today,
        'upcoming': upcoming,
        'announcements': announcements,
        'this_month_days': this_month_days,
    })


@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('schedule:home')

    today = timezone.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    upcoming_trainings = TrainingSession.objects.filter(date__gte=today).order_by('date', 'start_time')[:5]
    upcoming_competitions = Competition.objects.filter(end_date__gte=today).order_by('start_date')[:5]
    active_members = Member.objects.filter(is_active=True).count()

    # 이번 주 출석 예정
    week_days = [monday + timedelta(days=i) for i in range(7)]
    week_plans = AttendancePlan.objects.filter(date__in=week_days).select_related('user')
    week_day_names = ['월', '화', '수', '목', '금', '토', '일']
    week_attendance = []
    for i, day in enumerate(week_days):
        day_plans = [p for p in week_plans if p.date == day]
        slots = []
        for slot_code, slot_label in AttendancePlan.TIME_SLOT_CHOICES:
            sp = [p for p in day_plans if p.time_slot == slot_code]
            slots.append({
                'code': slot_code,
                'label': slot_label,
                'attendees': [p.user.first_name or p.user.username for p in sp],
                'count': len(sp),
            })
        if day_plans or day >= today:
            week_attendance.append({
                'date': day,
                'day_name': week_day_names[i],
                'slots': slots,
                'total_count': len(day_plans),
                'is_today': day == today,
                'is_past': day < today,
            })

    announcements = Announcement.objects.all()[:5]

    return render(request, 'schedule/dashboard.html', {
        'upcoming_trainings': upcoming_trainings,
        'upcoming_competitions': upcoming_competitions,
        'active_members': active_members,
        'today': today,
        'week_attendance': week_attendance,
        'monday': monday,
        'sunday': sunday,
        'announcements': announcements,
    })


@staff_member_required
def member_list(request):
    members = Member.objects.filter(is_active=True).order_by('name')
    return render(request, 'schedule/member_list.html', {'members': members})


@staff_member_required
def member_create(request):
    form = MemberForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('schedule:member_list')
    return render(request, 'schedule/member_form.html', {'form': form, 'action': '등록'})


@staff_member_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, instance=member)
    if form.is_valid():
        form.save()
        return redirect('schedule:member_detail', pk=pk)
    return render(request, 'schedule/member_form.html', {'form': form, 'action': '수정', 'member': member})


@staff_member_required
@require_POST
def member_delete(request, pk):
    get_object_or_404(Member, pk=pk).delete()
    return redirect('schedule:member_list')


@staff_member_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    recent_trainings = member.trainings.order_by('-date')[:10]
    competition_results = member.competitionresult_set.select_related('competition').order_by('-competition__start_date')
    today = timezone.now().date()
    this_month_trainings = member.trainings.filter(
        date__year=today.year, date__month=today.month
    ).count()
    return render(request, 'schedule/member_detail.html', {
        'member': member,
        'recent_trainings': recent_trainings,
        'competition_results': competition_results,
        'this_month_trainings': this_month_trainings,
        'today': today,
    })


@login_required
def training_list(request):
    trainings = TrainingSession.objects.order_by('-date', '-start_time')
    return render(request, 'schedule/training_list.html', {'trainings': trainings})


@login_required
def competition_list(request):
    today = timezone.now().date()
    upcoming = Competition.objects.filter(end_date__gte=today).order_by('start_date')
    past = Competition.objects.filter(end_date__lt=today).order_by('-start_date')
    return render(request, 'schedule/competition_list.html', {
        'upcoming': upcoming,
        'past': past,
    })


@login_required
def competition_detail(request, pk):
    competition = get_object_or_404(Competition, pk=pk)
    results = competition.competitionresult_set.select_related('member').order_by('result')
    return render(request, 'schedule/competition_detail.html', {
        'competition': competition,
        'results': results,
    })


@login_required
def attendance_week(request, year=None, week=None):
    today = timezone.now().date()
    if year and week:
        try:
            monday = date.fromisocalendar(int(year), int(week), 1)
        except ValueError:
            monday = today - timedelta(days=today.weekday())
    else:
        monday = today - timedelta(days=today.weekday())

    # 이번 주 + 다음 주 14일
    all_days = [monday + timedelta(days=i) for i in range(14)]

    plans = AttendancePlan.objects.filter(date__in=all_days).select_related('user')
    trainings = TrainingSession.objects.filter(date__in=all_days)

    plans_by_date = {}
    for p in plans:
        plans_by_date.setdefault(p.date, []).append(p)

    trainings_by_date = {}
    for t in trainings:
        trainings_by_date.setdefault(t.date, []).append(t)

    day_names = ['월', '화', '수', '목', '금', '토', '일']

    def build_week(days_slice):
        result = []
        for i, day in enumerate(days_slice):
            day_plans = plans_by_date.get(day, [])
            slots = []
            slots_json_data = {}
            for slot_code, slot_label in AttendancePlan.TIME_SLOT_CHOICES:
                sp = [p for p in day_plans if p.time_slot == slot_code]
                names = [p.user.first_name or p.user.username for p in sp]
                user_att = any(p.user_id == request.user.id for p in sp)
                slots.append({
                    'code': slot_code,
                    'label': slot_label,
                    'attendees': names,
                    'user_attending': user_att,
                    'count': len(sp),
                })
                slots_json_data[slot_code] = {
                    'label': slot_label,
                    'attendees': names,
                    'user_attending': user_att,
                    'count': len(sp),
                }
            result.append({
                'date': day,
                'day_name': day_names[i],
                'slots': slots,
                'slots_json': json.dumps(slots_json_data, ensure_ascii=False),
                'trainings': trainings_by_date.get(day, []),
                'user_attending': any(p.user_id == request.user.id for p in day_plans),
                'total_count': len(day_plans),
                'is_today': day == today,
                'is_past': day < today,
                'is_weekend': i >= 5,
            })
        return result

    this_week = build_week(all_days[:7])
    next_week = build_week(all_days[7:])

    all_day_data = this_week + next_week

    prev_monday = monday - timedelta(weeks=1)
    next_monday = monday + timedelta(weeks=1)
    prev_iso = prev_monday.isocalendar()
    next_iso = next_monday.isocalendar()

    # 오늘 출석 현황
    today_plans = AttendancePlan.objects.filter(date=today).select_related('user')
    today_slots = []
    for slot_code, slot_label in AttendancePlan.TIME_SLOT_CHOICES:
        sp = [p for p in today_plans if p.time_slot == slot_code]
        if sp:
            today_slots.append({
                'label': slot_label,
                'attendees': [p.user.first_name or p.user.username for p in sp],
                'count': len(sp),
            })

    announcements = Announcement.objects.all()[:3]

    return render(request, 'schedule/attendance_week.html', {
        'this_week': this_week,
        'next_week': next_week,
        'monday': monday,
        'next_monday': monday + timedelta(weeks=1),
        'sunday': all_days[6],
        'next_sunday': all_days[13],
        'today': today,
        'prev_year': prev_iso[0], 'prev_iso_week': prev_iso[1],
        'next_year': next_iso[0], 'next_iso_week': next_iso[1],
        'today_slots': today_slots,
        'announcements': announcements,
    })


@login_required
def attendance_month(request, year=None, month=None):
    today = timezone.now().date()
    if year and month:
        current = date(int(year), int(month), 1)
    else:
        current = date(today.year, today.month, 1)

    cal = calendar.monthcalendar(current.year, current.month)

    plans = AttendancePlan.objects.filter(
        date__year=current.year, date__month=current.month
    ).select_related('user')

    plans_by_date = {}
    for p in plans:
        plans_by_date.setdefault(p.date, []).append(p)

    weeks = []
    for week in cal:
        week_data = []
        for day_num in week:
            if day_num == 0:
                week_data.append(None)
            else:
                d = date(current.year, current.month, day_num)
                day_plans = plans_by_date.get(d, [])
                week_data.append({
                    'date': d,
                    'count': len(day_plans),
                    'user_attending': any(p.user_id == request.user.id for p in day_plans),
                    'is_today': d == today,
                    'is_past': d < today,
                    'iso': d.isocalendar(),
                })
        weeks.append(week_data)

    if current.month == 1:
        prev = date(current.year - 1, 12, 1)
    else:
        prev = date(current.year, current.month - 1, 1)
    if current.month == 12:
        next_ = date(current.year + 1, 1, 1)
    else:
        next_ = date(current.year, current.month + 1, 1)

    return render(request, 'schedule/attendance_month.html', {
        'weeks': weeks,
        'current': current,
        'today': today,
        'prev': prev,
        'next': next_,
    })


@login_required
def my_attendance(request, year=None, month=None):
    today = timezone.now().date()
    if year and month:
        current = date(int(year), int(month), 1)
    else:
        current = date(today.year, today.month, 1)

    all_plans = AttendancePlan.objects.filter(
        user=request.user,
        date__year=current.year,
        date__month=current.month,
    ).order_by('date', 'time_slot')

    by_date = {}
    for p in all_plans:
        by_date.setdefault(p.date, []).append(p)

    attended_days = sum(1 for d in by_date if d <= today)

    cal = calendar.monthcalendar(current.year, current.month)
    weeks = []
    for week in cal:
        week_data = []
        for day_num in week:
            if day_num == 0:
                week_data.append(None)
            else:
                d = date(current.year, current.month, day_num)
                day_plans = by_date.get(d, [])
                week_data.append({
                    'date': d,
                    'plans': day_plans,
                    'count': len(day_plans),
                    'is_today': d == today,
                    'is_past': d < today,
                    'is_future': d > today,
                })
        weeks.append(week_data)

    if current.month == 1:
        prev = date(current.year - 1, 12, 1)
    else:
        prev = date(current.year, current.month - 1, 1)
    if current.month == 12:
        next_ = date(current.year + 1, 1, 1)
    else:
        next_ = date(current.year, current.month + 1, 1)

    return render(request, 'schedule/my_attendance.html', {
        'current': current,
        'weeks': weeks,
        'attended_days': attended_days,
        'by_date': by_date,
        'today': today,
        'prev': prev,
        'next': next_,
    })


@login_required
@require_POST
def attendance_toggle(request):
    date_str = request.POST.get('date', '')
    time_slot = request.POST.get('time_slot', '')

    valid_slots = [s[0] for s in AttendancePlan.TIME_SLOT_CHOICES]
    if time_slot not in valid_slots:
        return JsonResponse({'error': '유효하지 않은 시간대입니다.'}, status=400)

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'invalid date'}, status=400)

    if target_date < date.today():
        return JsonResponse({'error': '지난 날짜는 변경할 수 없습니다.'}, status=400)

    plan, created = AttendancePlan.objects.get_or_create(
        user=request.user, date=target_date, time_slot=time_slot
    )
    if not created:
        plan.delete()
        attending = False
        # 같은 날/시간대에 등록한 다른 사용자에게 취소 알림
        others = AttendancePlan.objects.filter(
            date=target_date, time_slot=time_slot
        ).exclude(user=request.user).select_related('user')
        my_name = request.user.first_name or request.user.username
        slot_label = dict(AttendancePlan.TIME_SLOT_CHOICES).get(time_slot, time_slot)
        msg = f'{my_name}님이 {target_date.strftime("%-m월 %-d일")} {slot_label} 참석을 취소했습니다.'
        notifications = [Notification(user=p.user, message=msg, link='/attendance/') for p in others]
        Notification.objects.bulk_create(notifications)
    else:
        attending = True

    slot_plans = AttendancePlan.objects.filter(date=target_date, time_slot=time_slot).select_related('user')
    names = [p.user.first_name or p.user.username for p in slot_plans]
    return JsonResponse({'attending': attending, 'names': names, 'count': len(names), 'time_slot': time_slot})


# ── 알림 ──────────────────────────────────────────────

@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user)[:50]
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'schedule/notifications.html', {'notifications': notifs})


# ── 공지사항 ──────────────────────────────────────────

@login_required
def announcement_list(request):
    announcements = Announcement.objects.all()
    return render(request, 'schedule/announcement_list.html', {'announcements': announcements})


@login_required
def announcement_detail(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    return render(request, 'schedule/announcement_detail.html', {'announcement': ann})


@staff_member_required
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if form.is_valid():
        ann = form.save(commit=False)
        ann.author = request.user
        ann.save()
        return redirect('schedule:announcement_list')
    return render(request, 'schedule/announcement_form.html', {'form': form, 'action': '등록'})


@staff_member_required
def announcement_edit(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, instance=ann)
    if form.is_valid():
        form.save()
        return redirect('schedule:announcement_detail', pk=pk)
    return render(request, 'schedule/announcement_form.html', {'form': form, 'action': '수정'})


@staff_member_required
@require_POST
def announcement_delete(request, pk):
    get_object_or_404(Announcement, pk=pk).delete()
    return redirect('schedule:announcement_list')


# ── 훈련 일정 등록/수정/삭제 ───────────────────────────

@staff_member_required
def training_create(request):
    form = TrainingForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('schedule:training_list')
    return render(request, 'schedule/training_form.html', {'form': form, 'action': '등록'})


@staff_member_required
def training_edit(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    form = TrainingForm(request.POST or None, instance=training)
    if form.is_valid():
        form.save()
        return redirect('schedule:training_list')
    return render(request, 'schedule/training_form.html', {'form': form, 'action': '수정', 'training': training})


@staff_member_required
@require_POST
def training_delete(request, pk):
    get_object_or_404(TrainingSession, pk=pk).delete()
    return redirect('schedule:training_list')


# ── 대회 등록/수정/삭제 ───────────────────────────────

@staff_member_required
def competition_create(request):
    form = CompetitionForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('schedule:competition_list')
    return render(request, 'schedule/competition_form.html', {'form': form, 'action': '등록'})


@staff_member_required
def competition_edit(request, pk):
    competition = get_object_or_404(Competition, pk=pk)
    form = CompetitionForm(request.POST or None, instance=competition)
    if form.is_valid():
        form.save()
        return redirect('schedule:competition_list')
    return render(request, 'schedule/competition_form.html', {'form': form, 'action': '수정', 'competition': competition})


@staff_member_required
@require_POST
def competition_delete(request, pk):
    get_object_or_404(Competition, pk=pk).delete()
    return redirect('schedule:competition_list')


# ── 출석 확인 (관장용) ────────────────────────────────

@staff_member_required
def attendance_confirm(request, target_date_str=None):
    today = timezone.now().date()
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            target_date = today
    else:
        target_date = today

    plans = AttendancePlan.objects.filter(date=target_date).select_related('user').order_by('time_slot')
    slots = []
    for slot_code, slot_label in AttendancePlan.TIME_SLOT_CHOICES:
        sp = [p for p in plans if p.time_slot == slot_code]
        slots.append({'code': slot_code, 'label': slot_label, 'plans': sp})

    return render(request, 'schedule/attendance_confirm.html', {
        'target_date': target_date,
        'slots': slots,
        'today': today,
    })


@staff_member_required
@require_POST
def attendance_confirm_toggle(request):
    plan_id = request.POST.get('plan_id')
    plan = get_object_or_404(AttendancePlan, pk=plan_id)
    plan.confirmed = not plan.confirmed
    plan.save()
    return JsonResponse({'confirmed': plan.confirmed})


# ── 내 정보 수정 ──────────────────────────────────────

@login_required
def my_profile_edit(request):
    from accounts.models import UserProfile
    from accounts.forms import RegistrationForm
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    belt_choices = UserProfile._meta.get_field('belt').choices

    if request.method == 'POST':
        belt = request.POST.get('belt', '')
        valid_belts = [c[0] for c in belt_choices]
        if belt in valid_belts:
            profile.belt = belt
            profile.save()
            return redirect('schedule:my_attendance')

    return render(request, 'schedule/my_profile_edit.html', {
        'profile': profile,
        'belt_choices': belt_choices,
    })


@login_required
@require_POST
def attendance_batch(request):
    """여러 날짜를 한번에 등록하거나 취소."""
    dates_str = request.POST.getlist('dates')
    action = request.POST.get('action', 'add')
    today = date.today()
    results = []

    for date_str in dates_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        if target_date < today:
            continue

        if action == 'add':
            AttendancePlan.objects.get_or_create(user=request.user, date=target_date)
            results.append({'date': date_str, 'attending': True})
        elif action == 'remove':
            AttendancePlan.objects.filter(user=request.user, date=target_date).delete()
            results.append({'date': date_str, 'attending': False})

    return JsonResponse({'results': results})


# ── 사용자 관리 ───────────────────────────────────────

@staff_member_required
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    # 프로필이 없는 유저는 생성
    for u in users:
        UserProfile.objects.get_or_create(user=u)
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    return render(request, 'schedule/user_list.html', {'users': users})


@staff_member_required
@require_POST
def user_toggle_staff(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        return JsonResponse({'error': '자기 자신의 권한은 변경할 수 없습니다.'}, status=400)
    target.is_staff = not target.is_staff
    target.save()
    return JsonResponse({'is_staff': target.is_staff})


@staff_member_required
@require_POST
def user_toggle_active(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        return JsonResponse({'error': '자기 자신의 상태는 변경할 수 없습니다.'}, status=400)
    target.is_active = not target.is_active
    target.save()
    return JsonResponse({'is_active': target.is_active})
