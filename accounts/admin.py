from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = '유도 정보'


class JudoUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['get_full_name', 'get_belt', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff']
    actions = ['approve_users', 'set_as_staff', 'unset_staff']

    @admin.display(description='이름')
    def get_full_name(self, obj):
        return obj.first_name or obj.username

    @admin.display(description='띠/단')
    def get_belt(self, obj):
        try:
            return obj.profile.get_belt_display()
        except UserProfile.DoesNotExist:
            return '-'

    @admin.action(description='선택한 사용자 승인')
    def approve_users(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f'{updated}명을 승인했습니다.')

    @admin.action(description='관장님으로 지정 (관리자 권한 부여)')
    def set_as_staff(self, request, queryset):
        updated = queryset.update(is_active=True, is_staff=True)
        self.message_user(request, f'{updated}명을 관장님으로 지정했습니다.')

    @admin.action(description='일반 관원으로 변경 (관리자 권한 해제)')
    def unset_staff(self, request, queryset):
        updated = queryset.exclude(is_superuser=True).update(is_staff=False)
        self.message_user(request, f'{updated}명을 일반 관원으로 변경했습니다.')


admin.site.unregister(User)
admin.site.register(User, JudoUserAdmin)
