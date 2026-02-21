# import yt_dlp
# import requests
# from django.http import StreamingHttpResponse, HttpResponse
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# # --- ভিডিওর তথ্য পাওয়ার জন্য ---
# @api_view(['POST'])
# def get_video_info(request):
#     url = request.data.get("url")
#     if not url:
#         return Response({"error": "URL required"}, status=400)

#     ydl_opts = {'quiet': True, 'noplaylist': True}
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             formats = info.get("formats", [])
#             video_formats = []
#             for f in formats:
#                 # শুধু MP4 এবং ভিডিও+অডিও একসাথে আছে এমন ফরম্যাট (No FFmpeg needed)
#                 if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none':
#                     video_formats.append({
#                         "quality": f.get("format_note") or f.get("resolution") or "Standard",
#                         "format_id": f.get("format_id"),
#                         "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
#                     })
            
#             # ডুপ্লিকেট সরানো
#             unique_formats = {f['quality']: f for f in video_formats}.values()
#             return Response({
#                 "title": info.get("title"),
#                 "thumbnail": info.get("thumbnail"),
#                 "formats": list(unique_formats)
#             })
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)

# # --- রিয়েল-টাইম স্ট্রিমিং ডাউনলোড ---
# def download_file(request):
#     url = request.GET.get("url")
#     format_id = request.GET.get("format_id")

#     if not url:
#         return HttpResponse("URL required", status=400)

#     try:
#         ydl_opts = {'format': format_id, 'quiet': True}
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             video_url = info['url'] # ইউটিউবের সরাসরি ভিডিও লিঙ্ক
#             file_size = info.get('filesize') or info.get('filesize_approx')
#             filename = f"{info.get('title', 'video')}.mp4"

#         # ভিডিও ডেটা চাঙ্ক হিসেবে জেনারেট করা
#         def stream_content():
#             # stream=True দিয়ে রিকোয়েস্ট পাঠানো
#             response = requests.get(video_url, stream=True, timeout=60)
#             for chunk in response.iter_content(chunk_size=8192 * 4): # ৩২ কেবি চাঙ্ক
#                 if chunk:
#                     yield chunk

#         response = StreamingHttpResponse(stream_content(), content_type='video/mp4')
        
#         # প্রগ্রেস বারের জন্য এই ৩টি হেডার বাধ্যতামূলক
#         if file_size:
#             response['Content-Length'] = file_size
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
#         response['Access-Control-Expose-Headers'] = 'Content-Length'
        
#         return response

#     except Exception as e:
#         return HttpResponse(f"Error: {str(e)}", status=500)








# import yt_dlp
# import requests
# from django.http import StreamingHttpResponse, HttpResponse
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# # --- ভিডিওর ইনফো দেখার জন্য ---
# @api_view(['POST'])
# def get_video_info(request):
#     url = request.data.get("url")
#     if not url: return Response({"error": "URL required"}, status=400)

#     ydl_opts = {'quiet': True, 'noplaylist': True}
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             formats = info.get("formats", [])
#             video_formats = []
#             for f in formats:
#                 # শুধু MP4 এবং ভিডিও+অডিও একসাথে আছে এমন ফরম্যাট
#                 if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none':
#                     video_formats.append({
#                         "quality": f.get("format_note") or f.get("resolution") or "Standard",
#                         "format_id": f.get("format_id"),
#                         "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
#                     })
            
#             unique_formats = {f['quality']: f for f in video_formats}.values()
#             return Response({
#                 "title": info.get("title"),
#                 "thumbnail": info.get("thumbnail"),
#                 "formats": list(unique_formats)
#             })
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)

# # --- গুগল ডাউনলোডার ফ্রেন্ডলি স্ট্রিমিং ---
# def download_file(request):
#     url = request.GET.get("url")
#     format_id = request.GET.get("format_id")

#     try:
#         ydl_opts = {'format': format_id, 'quiet': True}
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             video_url = info['url'] 
#             file_size = info.get('filesize') or info.get('filesize_approx')
#             # ফাইলের নাম পরিষ্কার করা
#             clean_title = "".join([c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '.', '_')]).strip()
#             filename = f"{clean_title}.mp4"

#         def stream_content():
#             with requests.get(video_url, stream=True, timeout=60) as r:
#                 r.raise_for_status()
#                 for chunk in r.iter_content(chunk_size=1024 * 1024): # ১ এমবি করে চাঙ্ক পাঠাবে
#                     if chunk:
#                         yield chunk

#         response = StreamingHttpResponse(stream_content(), content_type='video/mp4')
        
#         # গুগল ক্রোম বা IDM-এর জন্য এই হেডারগুলোই আসল
#         if file_size:
#             response['Content-Length'] = file_size
        
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
#         # ব্রাউজারকে জানানো যে এটি একটি ডাউনলোড ফাইল
#         response['Content-Type'] = 'application/octet-stream' 
        
#         return response

#     except Exception as e:
#         return HttpResponse(f"Error: {str(e)}", status=500)












import yt_dlp
import subprocess
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def get_video_info(request):
    url = request.data.get("url")
    if not url: return Response({"error": "URL required"}, status=400)
    
    ydl_opts = {'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            video_formats = []
            for f in formats:
                # vcodec != 'none' মানে এটি ভিডিও ফরম্যাট
                if f.get('vcodec') != 'none':
                    video_formats.append({
                        "quality": f.get("format_note") or f.get("resolution") or "Video",
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                    })
            
            # রেজোলিউশন অনুযায়ী সাজানো
            unique_formats = sorted(
                {f['quality']: f for f in video_formats}.values(),
                key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'].lower() else 0,
                reverse=True
            )
            return Response({
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "formats": unique_formats
            })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

def download_file(request):
    url = request.GET.get("url")
    format_id = request.GET.get("format_id")

    if not url or not format_id:
        return HttpResponse("Missing params", status=400)

    try:
        # yt-dlp ব্যবহার করে সরাসরি ভিডিও এবং অডিও লিঙ্ক বের করা
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # ভিডিও লিঙ্ক
            video_url = ""
            for f in info['formats']:
                if f['format_id'] == format_id:
                    video_url = f['url']
                    break
            
            # বেস্ট অডিও লিঙ্ক
            audio_url = ""
            for f in info['formats']:
                if f['vcodec'] == 'none' and f['acodec'] != 'none':
                    audio_url = f['url'] # এখানে চাইলে আরও ফিল্টার করা যায়
                    break

        if not video_url or not audio_url:
            return HttpResponse("Links not found", status=404)

        # FFmpeg কমান্ড - যা ভিডিও এবং অডিওকে মার্জ করে সরাসরি আউটপুট পাইপে দিবে
        # আপনার পিসিতে 'ffmpeg' কমান্ডটি গ্লোবালি সেট থাকতে হবে
        ffmpeg_cmd = [
            'ffmpeg',
            '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5', # নেটওয়ার্ক ড্রপ হ্যান্ডেল করতে
            '-i', video_url,
            '-i', audio_url,
            '-c:v', 'copy',  # ভিডিও এনকোড হবে না, শুধু কপি হবে (খুব দ্রুত)
            '-c:a', 'aac',   # অডিও এএসি তে কনভার্ট হবে মার্জ করার জন্য
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov', # এটি গুগল ডাউনলোডে স্ট্রিমিং করার জন্য অত্যন্ত জরুরি
            'pipe:1'
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        def stream_generator():
            try:
                while True:
                    chunk = process.stdout.read(1024 * 128) # ১২৮ কেবি চাঙ্ক
                    if not chunk:
                        break
                    yield chunk
            finally:
                process.kill()

        response = StreamingHttpResponse(stream_generator(), content_type='video/mp4')
        response['Content-Disposition'] = f'attachment; filename="video_vault_1080p.mp4"'
        
        return response

    except Exception as e:
        return HttpResponse(f"Server Error: {str(e)}", status=500)