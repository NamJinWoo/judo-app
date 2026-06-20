from django.contrib import admin
from .models import Member, TrainingSession, Competition, CompetitionResult


class CompetitionResultInline(admin.TabularInline):
    model = CompetitionResult
    extra = 1


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'belt', 'weight_class', 'phone', 'join_date', 'is_active']
    list_filter = ['belt', 'weight_class', 'is_active']
    search_fields = ['name', 'phone']
    list_editable = ['is_active']


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['date', 'title', 'start_time', 'end_time', 'location']
    list_filter = ['date']
    search_fields = ['title', 'location']
    filter_horizontal = ['attendees']
    date_hierarchy = 'date'


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'location', 'organizer']
    list_filter = ['start_date']
    search_fields = ['name', 'location', 'organizer']
    date_hierarchy = 'start_date'
    inlines = [CompetitionResultInline]


@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ['member', 'competition', 'weight_class', 'result']
    list_filter = ['result', 'competition']
    search_fields = ['member__name', 'competition__name']
