


# import yt_dlp
# import requests
# from django.http import StreamingHttpResponse, HttpResponse
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# # --- ১. ভিডিওর ইনফরমেশন পাওয়ার জন্য API ---
# @api_view(['POST'])
# def get_video_info(request):
#     url = request.data.get("url")
#     if not url:
#         return Response({"error": "URL is required"}, status=400)

#     # yt-dlp অপশন: শুধু সেই ফাইলগুলো নিবে যেগুলোতে ভিডিও ও অডিও দুইটাই আছে
#     ydl_opts = {
#         'quiet': True,
#         'noplaylist': True,
#     }

#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             formats = info.get("formats", [])
            
#             video_formats = []
#             for f in formats:
#                 # Progressive Formats (ভিডিও + অডিও একসাথে) ফিল্টার করা
#                 if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
#                     filesize = f.get("filesize") or f.get("filesize_approx") or 0
#                     video_formats.append({
#                         "quality": f.get("format_note") or f.get("resolution"),
#                         "format_id": f.get("format_id"),
#                         "ext": f.get("ext"),
#                         "size": f"{round(filesize / (1024*1024), 2)} MB" if filesize else "Unknown"
#                     })

#             # রেজোলিউশন অনুযায়ী সাজানো (যেমন ৭২০পি আগে থাকবে)
#             unique_formats = sorted(
#                 {f['quality']: f for f in video_formats}.values(),
#                 key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'].lower() else 0,
#                 reverse=True
#             )

#             return Response({
#                 "title": info.get("title"),
#                 "thumbnail": info.get("thumbnail"),
#                 "formats": list(unique_formats)
#             })

#     except Exception as e:
#         return Response({"error": str(e)}, status=500)


# # --- ২. রিয়েল-টাইম স্ট্রিমিং ডাউনলোড ফাংশন ---
# def download_file(request):
#     video_url_input = request.GET.get("url")
#     format_id = request.GET.get("format_id")

#     if not video_url_input or not format_id:
#         return HttpResponse("Missing params", status=400)

#     try:
#         # ১. ইউটিউব থেকে সরাসরি ডাউনলোড লিঙ্ক বের করা
#         ydl_opts = {'format': format_id, 'quiet': True}
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(video_url_input, download=False)
#             video_direct_url = info.get('url')
#             file_size = info.get('filesize') or info.get('filesize_approx')
#             # টাইটেল থেকে স্পেশাল ক্যারেক্টার সরানো
#             clean_title = "".join([c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '.', '_')]).strip()
#             filename = f"{clean_title}.mp4"

#         # ২. গুগল সার্ভার থেকে ডেটা স্ট্রীম করার জন্য রিকোয়েস্ট (Headers জরুরি)
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }

#         def stream_generator():
#             # stream=True মানে পুরো ফাইল একবারে মেমোরিতে লোড হবে না
#             with requests.get(video_direct_url, headers=headers, stream=True, timeout=60) as r:
#                 r.raise_for_status()
#                 for chunk in r.iter_content(chunk_size=1024 * 1024): # ১ এমবি করে চাঙ্ক পাঠাবে
#                     if chunk:
#                         yield chunk

#         # ৩. Django Streaming Response তৈরি
#         response = StreamingHttpResponse(stream_generator(), content_type='video/mp4')
        
#         # প্রগ্রেস বার দেখার জন্য Content-Length দেওয়া খুব জরুরি
#         if file_size:
#             response['Content-Length'] = file_size
        
#         # ব্রাউজারকে জানানো যে এটি একটি ডাউনলোড ফাইল
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
#         response['X-Content-Type-Options'] = 'nosniff' # সিকিউরিটির জন্য

#         return response

#     except Exception as e:
#         return HttpResponse(f"Server Error: {str(e)}", status=500)








import yt_dlp
import requests
import re
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# --- ১. ভিডিওর ইনফরমেশন পাওয়ার জন্য API ---
@api_view(['POST'])
@permission_classes([AllowAny])
def get_video_info(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "URL is required"}, status=400)

    # yt-dlp অপশন: ফেসবুকের জন্য 'format': 'best' দেওয়া ভালো
    ydl_opts = {
    'quiet': True,
    'noplaylist': True,
    'format': 'best',
    'nocheckcertificate': True,
    'cachedir': False,
    # ইউটিউব বট ডিটেকশন এড়াতে এই হেডারগুলো যোগ করুন
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    },
    # প্রক্সি এরর বা বট ডিটেকশন কমাতে এটি সাহায্য করতে পারে
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
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
        # ইউটিউব/ফেসবুক থেকে সরাসরি লিঙ্ক বের করা
        ydl_opts = {
            'format': format_id, 
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url_input, download=False)
            video_direct_url = info.get('url')
            file_size = info.get('filesize') or info.get('filesize_approx')
            
            # টাইটেল ক্লিনআপ
            clean_title = "".join([c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '.', '_')]).strip()
            filename = f"{clean_title}.mp4"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        def stream_generator():
            # স্ট্রিমিং এর মাধ্যমে ডেটা পাঠানো (মেমোরি সেভ করতে)
            with requests.get(video_direct_url, headers=headers, stream=True, timeout=120) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 1024): 
                    if chunk:
                        yield chunk

        response = StreamingHttpResponse(stream_generator(), content_type='video/mp4')
        
        if file_size:
            response['Content-Length'] = file_size
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'

        return response

    except Exception as e:
        return HttpResponse(f"Server Error: {str(e)}", status=500)