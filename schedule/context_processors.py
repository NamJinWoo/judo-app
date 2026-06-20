from django.contrib.auth.models import User
from .models import Notification


def app_context(request):
    if not request.user.is_authenticated:
        return {}
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    pending = User.objects.filter(is_active=False).count() if request.user.is_staff else 0
    return {'unread_notifications': unread, 'pending_members_count': pending}
