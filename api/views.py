


import yt_dlp
import requests
import re
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import os
from django.conf import settings
# --- ১. ভিডিওর ইনফরমেশন পাওয়ার জন্য API ---
@api_view(['POST'])
@permission_classes([AllowAny])
def get_video_info(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "URL is required"}, status=400)

    
    ydl_opts = {
    'quiet': True,
    'format': 'best',
    'nocheckcertificate': True,
    'cachedir': False,
    # কুকি ফাইলটি অবশ্যই রেন্ডারের 'Secret Files'-এ আপডেট করে রাখুন
    'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'), 
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    },
    'extractor_args': {
        'youtube': {
            # ইউটিউব এখন 'ios' ক্লায়েন্টকে কম ব্লক করে
            'player_client': ['ios'],
            # PoToken জেনারেট করার চেষ্টা করবে
            'po_token': ['web+https://www.youtube.com/'],
        }
    },
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            
            video_formats = []
            
            # ফেসবুক ভিডিও সাধারণত সিঙ্গেল ভিডিও ফরম্যাটেই থাকে
            # তাই আমরা vcodec এবং acodec এর কড়াকড়ি কিছুটা কমিয়ে দিচ্ছি
            for f in formats:
                # Progressive অথবা অন্তত ভিডিও স্ট্রিম থাকলে নিবে
                if f.get('vcodec') != 'none':
                    filesize = f.get("filesize") or f.get("filesize_approx") or 0
                    quality = f.get("format_note") or f.get("resolution") or "Standard"
                    
                    video_formats.append({
                        "quality": quality,
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext", "mp4"),
                        "size": f"{round(filesize / (1024*1024), 2)} MB" if filesize else "Unknown"
                    })

            # ডুপ্লিকেট রেজোলিউশন বাদ দেওয়া এবং সুন্দরভাবে সাজানো
            unique_formats = {}
            for f in video_formats:
                q = f['quality']
                # একই কোয়ালিটির জন্য বড় সাইজটি রাখা ভালো
                if q not in unique_formats:
                    unique_formats[q] = f

            # সর্টিং (৭২০পি, ১০৮০পি ইত্যাদি অনুসারে)
            sorted_formats = sorted(
                unique_formats.values(),
                key=lambda x: int(re.search(r'\d+', str(x['quality'])).group()) if re.search(r'\d+', str(x['quality'])) else 0,
                reverse=True
            )

            return Response({
                "title": info.get("title", "No Title Found"),
                "thumbnail": info.get("thumbnail"),
                "formats": list(sorted_formats)
            })

    except Exception as e:
        return Response({"error": str(e)}, status=500)


# --- ২. রিয়েল-টাইম স্ট্রিমিং ডাউনলোড ফাংশন ---
def download_file(request):
    video_url_input = request.GET.get("url")
    format_id = request.GET.get("format_id")

    if not video_url_input or not format_id:
        return HttpResponse("Missing params", status=400)

    try:
        # Vidmate স্টাইল ডাউনলোড নিশ্চিত করতে headers আরও উন্নত করা
        ydl_opts = {
            'format': f'{format_id}+bestaudio/best', # ভিডিওর সাথে অডিও যোগ করার চেষ্টা
            'quiet': True,
            'cookiefile': os.path.join(settings.BASE_DIR, 'cookies.txt'),
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url_input, download=False)
            video_direct_url = info.get('url')
            
            # অনেক সময় 'url' সরাসরি পাওয়া যায় না যদি এটি DASH ফরম্যাট হয়
            # সেক্ষেত্রে সরাসরি স্ট্রিমিং লিঙ্কটি নিতে হবে
            if not video_direct_url:
                video_direct_url = info.get('formats')[0].get('url')

            file_size = info.get('filesize') or info.get('filesize_approx')
            clean_title = "".join([c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '.', '_')]).strip()
            filename = f"{clean_title}.mp4"

        # রেসপন্স স্ট্রিম করা
        response = StreamingHttpResponse(
            stream_generator(video_direct_url), 
            content_type='application/octet-stream' # এটি ডাউনলোড প্রম্পট নিশ্চিত করে
        )
        
        if file_size:
            response['Content-Length'] = file_size
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return HttpResponse(f"Server Error: {str(e)}", status=500)

def stream_generator(url):
    # ইন্টারনাল রিকোয়েস্টের জন্য টাইমআউট বাড়ানো
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192): # চাঙ্ক সাইজ ছোট রাখা স্ট্যাবিলিটির জন্য ভালো
            yield chunk