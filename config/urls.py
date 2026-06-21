from django.contrib import admin
from django.urls import path, include
from schedule import views as schedule_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manifest.json', schedule_views.manifest, name='manifest'),
    path('sw.js', schedule_views.service_worker, name='sw'),
    path('', include('accounts.urls')),
    path('', include('schedule.urls')),
]
