from django.urls import path
from .views import get_video_info, download_file

urlpatterns = [
    # ফ্রন্টএন্ডের সাথে মিল রেখে পাথ সেট করুন
    path('get-video-info/', get_video_info, name='get_video_info'),
    path('download-file/', download_file, name='download_file'),
]