# gg_api/__init__.py
"""
Google AI API package for video processing
"""

try:
    from .get_subtitle import process_video_for_subtitles, get_default_words_per_line
    print("✅ gg_api package initialized successfully")
except ImportError as e:
    print(f"❌ Error initializing gg_api package: {e}")