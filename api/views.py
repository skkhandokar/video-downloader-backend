import yt_dlp
import os
import re
import requests
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# --- ১. ভিডিও ইনফরমেশন API ---
@api_view(['POST'])
@permission_classes([AllowAny])
def get_video_info(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "URL is required"}, status=400)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # 'cookies.txt' ফাইলটি অবশ্যই প্রোজেক্টের মেইন ফোল্ডারে রাখবেন
        'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'),
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['web_embedded_launch_config'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Android 14; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            
            video_formats = []
            for f in formats:
                # 'acodec' != 'none' মানে হলো ভিডিওতে অডিও আছে (Progressive)
                # ইউটিউবে ১০৮০পি এর উপরের ভিডিওতে অডিও আলাদা থাকে, তাই আমরা best এবং progressive দুইটাই নিব
                if f.get('vcodec') != 'none' and f.get('ext') == 'mp4':
                    filesize = f.get("filesize") or f.get("filesize_approx") or 0
                    quality = f.get("format_note") or f.get("resolution") or "Standard"
                    
                    video_formats.append({
                        "quality": quality,
                        "format_id": f.get("format_id"),
                        "ext": "mp4",
                        "size": f"{round(filesize / (1024*1024), 2)} MB" if filesize else "Unknown"
                    })

            # ডুপ্লিকেট রিমুভ এবং সর্টিং
            unique_formats = {f['quality']: f for f in video_formats}.values()
            sorted_formats = sorted(unique_formats, key=lambda x: int(re.search(r'\d+', str(x['quality'])).group()) if re.search(r'\d+', str(x['quality'])) else 0, reverse=True)

            return Response({
                "title": info.get("title", "video"),
                "thumbnail": info.get("thumbnail"),
                "formats": sorted_formats
            })

    except Exception as e:
        return Response({"error": str(e)}, status=500)

# --- ২. ডাউনলোড এবং স্ট্রিমিং ফাংশন ---
def download_file(request):
    video_url = request.GET.get("url")
    format_id = request.GET.get("format_id")

    if not video_url or not format_id:
        return HttpResponse("Params missing", status=400)

    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'),
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            # সরাসরি স্ট্রিমিং লিঙ্ক (ইউটিউব সার্ভার থেকে)
            direct_url = info.get('url')
            filesize = info.get('filesize') or info.get('filesize_approx')
            
            clean_title = re.sub(r'[^\w\s-]', '', info.get('title', 'video')).strip().replace(' ', '_')

        def stream_iterator(url):
            headers = {'User-Agent': 'Mozilla/5.0 (Android 14; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0'}
            with requests.get(url, headers=headers, stream=True, timeout=120) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 64): # ৬৪ কেবি চাঙ্ক
                    if chunk:
                        yield chunk

        response = StreamingHttpResponse(stream_iterator(direct_url), content_type='application/octet-stream')
        if filesize:
            response['Content-Length'] = filesize
        response['Content-Disposition'] = f'attachment; filename="{clean_title}.mp4"'
        # CORS এর জন্য এই হেডারগুলো জরুরি
        response['Access-Control-Expose-Headers'] = 'Content-Length, Content-Disposition'
        return response

    except Exception as e:
        return HttpResponse(str(e), status=500)