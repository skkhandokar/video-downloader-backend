from django.urls import path
from .views import get_video_info, download_file

urlpatterns = [
    path('video-info/', get_video_info),          # fetch video info
    path('download-file/', download_file),      # direct download
]