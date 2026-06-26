from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('members/', views.member_list, name='member_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('trainings/', views.training_list, name='training_list'),
    path('competitions/', views.competition_list, name='competition_list'),
    path('competitions/<int:pk>/', views.competition_detail, name='competition_detail'),
    # 출석 예정
    path('attendance/', views.attendance_week, name='attendance_week'),
    path('attendance/week/<int:year>/<int:week>/', views.attendance_week, name='attendance_week_nav'),
    path('attendance/month/', views.attendance_month, name='attendance_month'),
    path('attendance/month/<int:year>/<int:month>/', views.attendance_month, name='attendance_month_nav'),
    path('attendance/toggle/', views.attendance_toggle, name='attendance_toggle'),
    path('attendance/batch/', views.attendance_batch, name='attendance_batch'),
    # 내 출석 기록
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    path('my-attendance/<int:year>/<int:month>/', views.my_attendance, name='my_attendance_nav'),
    # 내 정보 수정
    path('my-profile/edit/', views.my_profile_edit, name='my_profile_edit'),
    # 알림
    path('notifications/', views.notifications_list, name='notifications_list'),
    # 공지사항
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
    # 훈련 일정 관리
    path('trainings/create/', views.training_create, name='training_create'),
    path('trainings/<int:pk>/edit/', views.training_edit, name='training_edit'),
    path('trainings/<int:pk>/delete/', views.training_delete, name='training_delete'),
    # 대회 일정 관리
    path('competitions/create/', views.competition_create, name='competition_create'),
    path('competitions/<int:pk>/edit/', views.competition_edit, name='competition_edit'),
    path('competitions/<int:pk>/delete/', views.competition_delete, name='competition_delete'),
    # 회비 납부 관리
    path('fees/', views.fee_list, name='fee_list'),
    path('fees/<int:member_pk>/toggle/', views.fee_toggle, name='fee_toggle'),
    # 띠 승급 이력
    path('members/<int:member_pk>/promote/', views.belt_promote, name='belt_promote'),
    path('promotions/<int:pk>/delete/', views.belt_promotion_delete, name='belt_promotion_delete'),
    # 사용자 관리
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/toggle-staff/', views.user_toggle_staff, name='user_toggle_staff'),
    path('users/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    # 출석 확인 (관장용) — toggle은 반드시 <str> 패턴보다 먼저 정의
    path('attendance/confirm/', views.attendance_confirm, name='attendance_confirm'),
    path('attendance/confirm/toggle/', views.attendance_confirm_toggle, name='attendance_confirm_toggle'),
    path('attendance/confirm/<str:target_date_str>/', views.attendance_confirm, name='attendance_confirm_date'),
]
