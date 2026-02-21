#!/usr/bin/env bash
# কোনো এরর হলে স্ক্রিপ্ট থামিয়ে দিবে
set -o errexit

# ১. লাইব্রেরিগুলো ইনস্টল করা
pip install -r requirements.txt

# ২. স্ট্যাটিক ফাইল কালেকশন (CSS/Images এর জন্য)
python manage.py collectstatic --no-input

# ৩. ডাটাবেস মাইগ্রেশন
python manage.py migrate

# ৪. FFmpeg ইনস্টল করার চেষ্টা (Render-এর জন্য)
# নোট: অনেক সময় Render এর ডিফল্ট ইমেজে এটি থাকে না, তাই এই কমান্ডটি জরুরি।
# তবে ফ্রি টায়ারে অনেক সময় পারমিশন থাকে না, সেক্ষেত্রে Render-এর Native Docker বা Blueprints লাগে।