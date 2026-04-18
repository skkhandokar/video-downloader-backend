import yt_dlp
import requests
import re
import os
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# নির্ভরযোগ্য ইনভিয়াস ইন্সট্যান্স লিস্ট
INVIDIOUS_INSTANCES = [
    "https://inv.tux.rs",
    "https://invidious.asir.dev",
    "https://iv.melmac.space",
    "https://invidious.perennialte.ch",
    "https://yewtu.be"
]

def get_info_from_invidious(video_id):
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=7) # টাইমআউট একটু বাড়ানো হয়েছে
            if res.status_code == 200:
                data = res.json()
                formats = []
                # ইনভিয়াস থেকে ভিডিও+অডিও কম্বাইন্ড ফরম্যাটগুলো নেওয়া
                for f in data.get("formatStreams", []):
                    formats.append({
                        "quality": f.get("qualityLabel") or f.get("quality", "HD"),
                        "format_id": "invidious_" + str(f.get("itag", "default")),
                        "ext": "mp4",
                        "size": "Unknown",
                        "url": f.get("url")
                    })
                
                if formats: # যদি অন্তত একটি ফরম্যাট পাওয়া যায়
                    return {
                        "title": data.get("title", "YouTube Video"),
                        "thumbnail": data.get("videoThumbnails", [{}])[0].get("url", ""),
                        "formats": formats,
                        "source": "invidious"
                    }
        except Exception as e:
            print(f"Invidious instance {instance} failed: {str(e)}")
            continue
    return None

@api_view(['POST'])
@permission_classes([AllowAny])
def get_video_info(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "URL is required"}, status=400)

    # ভিডিও আইডি এক্সট্রাক্ট করা (Regex উন্নত করা হয়েছে)
    video_id_match = re.search(r"(?:v=|\/|embed\/|youtu.be\/)([0-9A-Za-z_-]{11})", url)
    video_id = video_id_match.group(1) if video_id_match else None

    # ১. প্রথমে yt-dlp দিয়ে চেষ্টা
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'),
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_formats = []
            for f in info.get("formats", []):
                # ভিডিও এবং অডিও দুটোই আছে এমন ফরম্যাট ফিল্টার করা
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
        error_str = str(e)
        print(f"yt-dlp error: {error_str}")
        
        # ২. ইউটিউব ব্লক করলে ইনভিয়াস ট্রাই করা
        if video_id:
            print(f"Attempting Invidious for video: {video_id}")
            invidious_data = get_info_from_invidious(video_id)
            if invidious_data:
                return Response(invidious_data)
        
        # ৩. সব ফেল করলে ইউজারকে পরিষ্কার মেসেজ দেওয়া
        return Response({
            "error": "YouTube high security detected. Please try another link or wait a few minutes.",
            "details": error_str[:100] # ডিবাগিংয়ের জন্য ছোট ডিটেইলস
        }, status=500)