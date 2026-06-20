from django.urls import path
from . import views

urlpatterns = [
    path('api/profile', views.profile_endpoint, name='profile_endpoint'),
    path('api/upload', views.upload_endpoint, name='upload_endpoint'),
    path('api/scans', views.scan_log_endpoint, name='scan_log_endpoint'),
]
