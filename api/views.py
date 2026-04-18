import yt_dlp
import requests
import re
import os
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# --- Invidious Helper Function ---
def get_info_from_invidious(video_id):
    # ইনভিয়াস এর কিছু নির্ভরযোগ্য পাবলিক ইন্সট্যান্স
    instances = [
        "https://inv.tux.rs",
        "https://invidious.asir.dev",
        "https://iv.melmac.space",
        "https://invidious.perennialte.ch"
    ]
    
    for instance in instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                formats = []
                # ইনভিয়াস ফরম্যাটগুলোকে আপনার ফ্রন্টএন্ডের উপযোগী করে সাজানো
                for f in data.get("formatStreams", []):
                    formats.append({
                        "quality": f.get("qualityLabel") or f.get("quality"),
                        "format_id": "invidious_" + f.get("itag", ""), # আইডেন্টিফায়ার
                        "ext": "mp4",
                        "size": "Unknown",
                        "url": f.get("url") # সরাসরি ডাউনলোড লিঙ্ক
                    })
                
                return {
                    "title": data.get("title"),
                    "thumbnail": data.get("videoThumbnails")[0]["url"] if data.get("videoThumbnails") else "",
                    "formats": formats,
                    "source": "invidious"
                }
        except:
            continue
    return None

# --- ১. ভিডিওর ইনফরমেশন পাওয়ার জন্য API ---
@api_view(['POST'])
@permission_classes([AllowAny])
def get_video_info(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "URL is required"}, status=400)

    # ভিডিও আইডি এক্সট্রাক্ট করা
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    video_id = video_id_match.group(1) if video_id_match else None

    # প্রথমে yt-dlp দিয়ে চেষ্টা
    ydl_opts = {
        'quiet': True,
        'format': 'best',
        'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'),
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_formats = []
            for f in info.get("formats", []):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    filesize = f.get("filesize") or f.get("filesize_approx") or 0
                    video_formats.append({
                        "quality": f.get("format_note") or f.get("resolution") or "HD",
                        "format_id": f.get("format_id"),
                        "ext": "mp4",
                        "size": f"{round(filesize / (1024*1024), 2)} MB" if filesize else "Unknown"
                    })
            
            return Response({
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "formats": video_formats,
                "source": "youtube"
            })

    except Exception as e:
        # যদি ইউটিউব ব্লক করে (Bot Error), তবে ইনভিয়াস ব্যবহার করবে
        if "Sign in to confirm" in str(e) and video_id:
            print("YouTube blocked. Switching to Invidious...")
            data = get_info_from_invidious(video_id)
            if data:
                return Response(data)
        
        return Response({"error": "ইউটিউব বর্তমানে এই ভিডিওটি ব্লক করছে। অনুগ্রহ করে পরে চেষ্টা করুন।"}, status=500)

# --- ২. ডাউনলোড ফাংশন ---
def download_file(request):
    video_url_input = request.GET.get("url")
    format_id = request.GET.get("format_id")

    if not video_url_input or not format_id:
        return HttpResponse("Missing params", status=400)

    try:
        # যদি ইনভিয়াস থেকে ডাউনলোড রিকোয়েস্ট আসে
        if format_id.startswith("invidious_"):
            # ইনভিয়াস ফরম্যাট আইডি থেকে সরাসরি লিঙ্ক বের করার জন্য আবার API কল করা যেতে পারে
            # অথবা ফ্রন্টএন্ড থেকে সরাসরি লিঙ্ক পাঠানো যেতে পারে। 
            # নিরাপত্তার জন্য আমরা আবার URL বের করছি:
            video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", video_url_input)
            data = get_info_from_invidious(video_id_match.group(1))
            target_url = next((f['url'] for f in data['formats'] if f['format_id'] == format_id), None)
            clean_title = data['title']
        else:
            # yt-dlp এর মাধ্যমে ইউটিউব থেকে লিঙ্ক বের করা
            ydl_opts = {'format': format_id, 'quiet': True, 'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt')}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url_input, download=False)
                target_url = info.get('url')
                clean_title = info.get('title')

        # স্ট্রিমিং রেসপন্স
        def stream_generator(url):
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    yield chunk

        response = StreamingHttpResponse(stream_generator(target_url), content_type='video/mp4')
        response['Content-Disposition'] = f'attachment; filename="video.mp4"'
        return response

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)