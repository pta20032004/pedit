# gg_api/get_subtitle.py - ENHANCED VERSION WITH TWO-STEP PROCESSING
"""
Enhanced subtitle generation using Google Gemini API
Step 1: Gemini-2.5-pro for subtitle generation
Step 2: Gemini-2.5-flash for format validation and correction
"""

import os
import subprocess
import tempfile
import time
import json
from typing import Optional, Tuple, List

# Check if google-generativeai is available
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    print("✅ google-generativeai library loaded")
except ImportError:
    GENAI_AVAILABLE = False
    print("❌ google-generativeai not found. Install: pip install google-generativeai")

# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

def load_api_keys() -> List[str]:
    """Load API keys from api_key.json file"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "api_key.json")
        
        if not os.path.exists(json_path):
            return []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            api_data = json.load(f)
        
        keys = []
        for item in api_data:
            if isinstance(item, dict):
                for name, api_key in item.items():
                    if api_key and len(api_key) > 14:
                        keys.append(api_key)
        
        return keys
    except Exception as e:
        print(f"❌ Error loading API keys: {e}")
        return []

def test_api_key_simple(api_key: str, log_callback=None) -> bool:
    """Simple test for API key validity"""
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    try:
        genai.configure(api_key=api_key)
        # Test with simplest model
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say 'test'")
        
        if response and response.text:
            if log_callback:
                log("SUCCESS", f"✅ API key validated: {api_key[:10]}...{api_key[-4:]}")
            return True
        else:
            if log_callback:
                log("ERROR", f"❌ API key test failed: No response")
            return False
            
    except Exception as e:
        if log_callback:
            log("ERROR", f"❌ API key test failed: {str(e)}")
        return False

# =============================================================================
# AUDIO EXTRACTION
# =============================================================================

def extract_audio_from_video(video_path: str, audio_output_path: str, ffmpeg_path: str = None) -> Tuple[bool, str]:
    """Extract audio from video to MP3 format"""
    try:
        if not os.path.exists(video_path):
            return False, f"Video file not found: {video_path}"
        
        # Find FFmpeg
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            import shutil
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                return False, "FFmpeg not found"
        
        # Simple FFmpeg command
        cmd = [
            ffmpeg_path,
            "-i", video_path,
            "-vn",                    # No video
            "-acodec", "mp3",         # MP3 audio
            "-ar", "16000",           # 16kHz sample rate
            "-ac", "1",               # Mono
            "-y",                     # Overwrite
            audio_output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(audio_output_path):
            return True, "Audio extracted successfully"
        else:
            return False, f"FFmpeg error: {result.stderr[:100]}"
            
    except Exception as e:
        return False, f"Audio extraction error: {str(e)}"

# =============================================================================
# PROMPT CREATION
# =============================================================================

def create_subtitle_generation_prompt(source_lang: str, target_lang: str) -> str:
    """Create prompt for initial subtitle generation"""
    
    # Clean language names (remove emoji flags)
    lang_map = {
        "🔍 Auto Detect": "auto-detect",
        "🇺🇸 English": "English", "🇬🇧 English (UK)": "English", 
        "🇨🇦 English (CA)": "English", "🇦🇺 English (AU)": "English",
        "🇨🇳 Chinese": "Chinese", "🇯🇵 Japanese": "Japanese", 
        "🇩🇪 German": "German", "🇮🇳 Hindi": "Hindi",
        "🇫🇷 French": "French", "🇮🇹 Italian": "Italian", 
        "🇧🇷 Portuguese": "Portuguese", "🇰🇷 Korean": "Korean",
        "🇪🇸 Spanish": "Spanish", "🇷🇺 Russian": "Russian", 
        "🇳🇱 Dutch": "Dutch", "🇸🇦 Arabic": "Arabic", 
        "🇦🇪 Arabic (UAE)": "Arabic", "🇻🇳 Vietnamese": "Vietnamese"
    }
    
    source_clean = lang_map.get(source_lang, source_lang)
    target_clean = lang_map.get(target_lang, target_lang)
    
    # Determine task type
    if source_clean == "auto-detect":
        task = f"transcribe and translate the audio into {target_clean}"
    elif source_clean.lower() == target_clean.lower():
        task = f"transcribe the audio in {source_clean}"
    else:
        task = f"translate the {source_clean} audio into {target_clean}"
    
    prompt = f"""Please {task} and provide the result in standard SRT subtitle format.

CRITICAL RULES:
1. Return ONLY SRT content - no explanations, no markdown
2. Time format: HH:MM:SS,mmm --> HH:MM:SS,mmm  
3. Start from 00:00:00,000 and follow actual audio timing
4. Sequential numbering (1, 2, 3, 4...)
5. Keep each subtitle SHORT - maximum 6-10 words per subtitle
6. Break long sentences into multiple short subtitles for easy reading
7. Output ONLY the {target_clean} text - do not include original language
8. If translation is needed, provide accurate and natural translation

Format example:
1
00:00:00,000 --> 00:00:03,500
First short subtitle here

2
00:00:03,500 --> 00:00:07,200
Second short subtitle here

IMPORTANT: Each subtitle block has only ONE line of text in {target_clean}.
Begin with subtitle number 1:"""
    
    return prompt

def create_format_correction_prompt(raw_subtitle: str) -> str:
    """Create prompt for format correction using Gemini-2.5-flash"""   
    
    prompt = f"""Find any lines with incorrect formatting that do not follow the standard .srt format "hh:mm:ss,mm --> hh:mm:ss,mmm" and correct them immediately. Each subtitle block must be separated by a blank line. Output must be in the standard .srt file format. Do not write anything else — only the corrected SRT content.
{raw_subtitle}
"""
    
    return prompt


def generate_subtitles_step1(audio_path: str, api_key: str, source_lang: str, 
                           target_lang: str, log_callback=None) -> Tuple[bool, str, str]:
    """Step 1: Generate subtitles using Gemini-2.5-pro"""
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    if not GENAI_AVAILABLE:
        return False, "", "google-generativeai library not available"
    
    try:
        # Configure API
        genai.configure(api_key=api_key)
        log("INFO", "🔑 Gemini API configured for Step 1")
        
        # Upload audio
        log("INFO", f"⬆️ Step 1: Uploading audio file...")
        audio_file = genai.upload_file(path=audio_path, mime_type='audio/mp3')
        
        # Wait for processing
        wait_count = 0
        while audio_file.state.name == "PROCESSING":
            wait_count += 1
            log("INFO", f"⏳ Step 1: Processing audio... ({wait_count * 2}s)")
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)
            
            if wait_count > 30:  # 60 seconds timeout
                return False, "", "Audio processing timeout"
        
        if audio_file.state.name == "FAILED":
            return False, "", f"Audio processing failed: {audio_file.state}"
        
        log("SUCCESS", "✅ Step 1: Audio uploaded and processed")
        
        # Create prompt
        prompt = create_subtitle_generation_prompt(source_lang, target_lang)
        log("INFO", "📝 Step 1: Using Gemini-2.5-pro for subtitle generation...")
        
        # Try Gemini-2.5-pro first
        try:
            model = genai.GenerativeModel("gemini-2.5-pro")
            
            response = model.generate_content(
                [prompt, audio_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=8192
                )
            )
            
            if response.text:
                srt_content = response.text.strip()
                log("SUCCESS", "✅ Step 1: Subtitles generated with Gemini-2.5-pro")
                return True, srt_content, "Generated with Gemini-2.5-pro"
            else:
                log("ERROR", "❌ Step 1: No response from Gemini-2.5-pro")
                return False, "", "No response from Gemini-2.5-pro"
                
        except Exception as e:
            log("ERROR", f"❌ Step 1: Gemini-2.5-pro failed: {str(e)}")
            return False, "", f"Gemini-2.5-pro failed: {str(e)}"
        
    except Exception as e:
        log("ERROR", f"❌ Step 1: API error: {str(e)}")
        return False, "", f"Step 1 API error: {str(e)}"

def generate_subtitles_step2(raw_subtitle: str, api_key: str, log_callback=None) -> Tuple[bool, str, str]:
    """Step 2: Format correction using Gemini-2.5-flash"""
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    if not GENAI_AVAILABLE:
        return False, "", "google-generativeai library not available"
    
    try:
        # Configure API (reuse same key)
        genai.configure(api_key=api_key)
        log("INFO", "🔧 Step 2: Using Gemini-2.5-flash for format correction...")
        
        # Create correction prompt
        correction_prompt = create_format_correction_prompt(raw_subtitle)
        
        # Use Gemini-2.5-flash for correction
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(
            correction_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Very low temperature for format correction
                max_output_tokens=8192
            )
        )
        
        if response.text:
            corrected_srt = response.text.strip()
            log("SUCCESS", "✅ Step 2: Format corrected with Gemini-2.5-flash")
            return True, corrected_srt, "Format corrected with Gemini-2.5-flash"
        else:
            log("WARNING", "⚠️ Step 2: No response from Gemini-2.5-flash, using original")
            return True, raw_subtitle, "Format correction skipped - using original"
            
    except Exception as e:
        log("WARNING", f"⚠️ Step 2: Format correction failed: {str(e)}")
        log("INFO", "📝 Step 2: Using original subtitle without format correction")
        return True, raw_subtitle, f"Format correction failed, using original: {str(e)}"



def process_video_for_subtitles(video_path: str, api_key: str, source_lang: str, 
                               target_lang: str, words_per_line: int = None, 
                               ffmpeg_path: str = None, log_callback=None) -> Tuple[bool, str, str]:
    """
    Enhanced two-step subtitle generation pipeline with API fallback và SRT format fix
    
    Args:
        video_path: Path to video file
        api_key: Primary Google AI API key
        source_lang: Source language (with emoji flags)
        target_lang: Target language (with emoji flags)
        words_per_line: Ignored in this version
        ffmpeg_path: Path to FFmpeg executable
        log_callback: Function to call for logging
    
    Returns:
        Tuple of (success: bool, srt_content: str, message: str)
    """
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
        else:
            print(f"[{level}] {message}")
    
    try:
        log("INFO", f"🎬 Enhanced Processing: {os.path.basename(video_path)}")
        log("INFO", f"🌐 Language: {source_lang} → {target_lang}")
        
        # Step 0: Extract audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            temp_audio = tmp.name
        
        try:
            log("INFO", "🎵 Extracting audio...")
            audio_success, audio_msg = extract_audio_from_video(video_path, temp_audio, ffmpeg_path)
            
            if not audio_success:
                return False, "", f"Audio extraction failed: {audio_msg}"
            
            log("SUCCESS", "✅ Audio extracted successfully")
            
            # Prepare API keys for fallback
            api_keys_to_try = [api_key]  # Start with primary key
            
            # Load backup keys if primary fails
            backup_keys = load_api_keys()
            for backup_key in backup_keys:
                if backup_key != api_key and backup_key not in api_keys_to_try:
                    api_keys_to_try.append(backup_key)
            
            log("INFO", f"🔑 Available API keys: {len(api_keys_to_try)} total")
            
            # Try up to 3 API keys for Step 1
            step1_success = False
            raw_subtitle = ""
            step1_message = ""
            
            for attempt, current_api_key in enumerate(api_keys_to_try[:3], 1):
                log("INFO", f"🔄 Step 1 Attempt {attempt}/3 with key: {current_api_key[:10]}...{current_api_key[-4:]}")
                
                # Test API key first
                if not test_api_key_simple(current_api_key, log_callback):
                    log("WARNING", f"⚠️ API key {attempt} failed validation, trying next...")
                    continue
                
                # Try Step 1: Subtitle generation
                step1_success, raw_subtitle, step1_message = generate_subtitles_step1(
                    temp_audio, current_api_key, source_lang, target_lang, log_callback
                )
                
                if step1_success:
                    log("SUCCESS", f"✅ Step 1 successful with API key {attempt}")
                    api_key = current_api_key  # Use this key for Step 2
                    break
                else:
                    log("ERROR", f"❌ Step 1 failed with API key {attempt}: {step1_message}")
                    if attempt < 3:
                        log("INFO", "🔄 Trying next API key...")
            
            # Check if Step 1 succeeded
            if not step1_success:
                return False, "", f"Step 1 failed with all {min(3, len(api_keys_to_try))} API keys"
            
            # Basic validation of Step 1 output
            if not raw_subtitle or len(raw_subtitle.strip()) < 10:
                return False, "", "Step 1 produced empty or too short subtitle content"
            
            if "1\n" not in raw_subtitle or "-->" not in raw_subtitle:
                log("WARNING", "⚠️ Step 1 output doesn't look like SRT format, proceeding anyway...")
            
            log("INFO", f"📝 Step 1 complete. Subtitle length: {len(raw_subtitle)} characters")
            
            # Step 2: Format correction with Gemini-2.5-flash
            log("INFO", "🔧 Starting Step 2: Format correction...")
            
            step2_success, final_subtitle, step2_message = generate_subtitles_step2(
                raw_subtitle, api_key, log_callback
            )
            
            if step2_success:
                log("SUCCESS", f"🎉 Two-step process complete!")
                log("INFO", f"📋 Final result: {step2_message}")
                
                # 🔥 NEW: Fix SRT format cuối cùng
                if final_subtitle and len(final_subtitle.strip()) > 10:
                    log("INFO", "🔧 Applying final SRT timestamp format fix...")
                    final_subtitle_fixed = fix_srt_timestamps(final_subtitle, log_callback)
                    
                    return True, final_subtitle_fixed, f"Two-step success + format fix: {step1_message} + {step2_message}"
                else:
                    log("WARNING", "⚠️ Final subtitle is empty, using Step 1 output")
                    raw_subtitle_fixed = fix_srt_timestamps(raw_subtitle, log_callback)
                    return True, raw_subtitle_fixed, f"Step 1 only + format fix: {step1_message}"
            else:
                log("WARNING", "⚠️ Step 2 failed, using Step 1 output with format fix")
                raw_subtitle_fixed = fix_srt_timestamps(raw_subtitle, log_callback)
                return True, raw_subtitle_fixed, f"Step 1 only + format fix: {step1_message}"
                
        finally:
            # Cleanup temp audio file
            if os.path.exists(temp_audio):
                try:
                    os.unlink(temp_audio)
                    log("INFO", "🧹 Temporary audio file cleaned up")
                except:
                    pass
            
    except Exception as e:
        log("ERROR", f"❌ Enhanced pipeline error: {str(e)}")
        import traceback
        log("ERROR", f"📋 Traceback: {traceback.format_exc()}")
        return False, "", f"Pipeline error: {str(e)}"


def fix_srt_timestamps(srt_content: str, log_callback=None) -> str:
    """
    🔧 Sửa lỗi timestamp phụ đề .srt mà không làm tròn thời gian.
    Bao gồm:
    - 00:03:500 → 00:00:03,500
    - 03:819 --> 08:449 → 00:03:819 --> 00:08:449
    - 8000 → 800 (truncate milliseconds)
    """
    def log(level, message):
        if log_callback:
            log_callback(level, message)

    try:
        import re

        if log_callback:
            log("INFO", "🔧 SRT timestamp fix - NO ROUNDING, position change only")

        fixed_content = srt_content
        total_fixes = 0

        # ✅ Thêm "00:" nếu timestamp có dạng MM:SSS trước/sau -->
        pattern_pre_fix = r'(?<!\d)(\d{1,2}):(\d{3})(?=\s*-->)'
        pattern_post_fix = r'(?<=-->\s*)(\d{1,2}):(\d{3})(?!\d)'

        def fix_missing_hour_pre(match):
            mm, sss = match.groups()
            return f"00:{mm}:{sss}"

        def fix_missing_hour_post(match):
            mm, sss = match.groups()
            return f"00:{mm}:{sss}"

        fixed_content = re.sub(pattern_pre_fix, fix_missing_hour_pre, fixed_content)
        fixed_content = re.sub(pattern_post_fix, fix_missing_hour_post, fixed_content)

        # ✅ Chuyển HH:MM:SSS thành HH:MM:SS,mmm
        pattern = r'(\d{2}):(\d{2}):(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{3})'

        def fix_timestamp_format(match):
            start_h, start_m, start_sss, end_h, end_m, end_sss = match.groups()

            def convert_sss_to_seconds_milliseconds(sss_str):
                sss = int(sss_str)
                if sss >= 100:
                    seconds = sss // 100
                    centiseconds = sss % 100
                    milliseconds = centiseconds * 10
                else:
                    seconds = 0
                    milliseconds = sss * 10
                return seconds, milliseconds

            start_seconds, start_ms = convert_sss_to_seconds_milliseconds(start_sss)
            start_minutes = int(start_m) + (start_seconds // 60)
            start_seconds = start_seconds % 60
            start_hours = int(start_h) + (start_minutes // 60)
            start_minutes = start_minutes % 60
            start_final = f"{start_hours:02d}:{start_minutes:02d}:{start_seconds:02d},{start_ms:03d}"

            end_seconds, end_ms = convert_sss_to_seconds_milliseconds(end_sss)
            end_minutes = int(end_m) + (end_seconds // 60)
            end_seconds = end_seconds % 60
            end_hours = int(end_h) + (end_minutes // 60)
            end_minutes = end_minutes % 60
            end_final = f"{end_hours:02d}:{end_minutes:02d}:{end_seconds:02d},{end_ms:03d}"

            return f"{start_final} --> {end_final}"

        matches = re.findall(pattern, fixed_content)
        if matches:
            fixed_content = re.sub(pattern, fix_timestamp_format, fixed_content)
            total_fixes += len(matches)
            if log_callback:
                log("SUCCESS", f"✅ Fixed {len(matches)} timestamps (NO ROUNDING)")
                for i, match in enumerate(matches[:3]):
                    original = f"{match[0]}:{match[1]}:{match[2]} --> {match[3]}:{match[4]}:{match[5]}"
                    log("INFO", f"   Example {i+1}: {original}")

        # ✅ Thêm giờ nếu thiếu (MM:SS,mmm)
        pattern2 = r'(\d{1,2}):(\d{2}),(\d{3})\s*-->\s*(\d{1,2}):(\d{2}),(\d{3})'

        def add_hours(match):
            start_min, start_sec, start_ms, end_min, end_sec, end_ms = match.groups()
            start_fixed = f"00:{start_min:0>2}:{start_sec},{start_ms}"
            end_fixed = f"00:{end_min:0>2}:{end_sec},{end_ms}"
            return f"{start_fixed} --> {end_fixed}"

        matches2 = re.findall(pattern2, fixed_content)
        if matches2:
            fixed_content = re.sub(pattern2, add_hours, fixed_content)
            total_fixes += len(matches2)
            if log_callback:
                log("SUCCESS", f"✅ Added missing hours: {len(matches2)} timestamps")

        # ✅ Pad milliseconds ngắn
        pattern3 = r'(\d{2}:\d{2}:\d{2}),(\d{1,2})(\s*-->\s*)(\d{2}:\d{2}:\d{2}),(\d{1,2})'

        def pad_milliseconds(match):
            start_time, start_ms, arrow, end_time, end_ms = match.groups()
            start_ms_padded = start_ms.ljust(3, '0')
            end_ms_padded = end_ms.ljust(3, '0')
            return f"{start_time},{start_ms_padded}{arrow}{end_time},{end_ms_padded}"

        matches3 = re.findall(pattern3, fixed_content)
        if matches3:
            fixed_content = re.sub(pattern3, pad_milliseconds, fixed_content)
            total_fixes += len(matches3)
            if log_callback:
                log("SUCCESS", f"✅ Padded short milliseconds: {len(matches3)} timestamps")

        # ✅ Truncate milliseconds quá dài
        pattern5 = r'(\d{2}:\d{2}:\d{2}),(\d{4,})(\s*-->\s*\d{2}:\d{2}:\d{2}),(\d{4,})'

        def truncate_milliseconds(match):
            start_time, start_ms, arrow, end_ms = match.groups()
            return f"{start_time},{start_ms[:3]}{arrow}{end_ms[:3]}"

        matches5 = re.findall(pattern5, fixed_content)
        if matches5:
            fixed_content = re.sub(pattern5, truncate_milliseconds, fixed_content)
            total_fixes += len(matches5)
            if log_callback:
                log("SUCCESS", f"✅ Truncated long milliseconds: {len(matches5)} timestamps")

        # ✅ Tách các block bị dính
        pattern4 = r'([^\n]+)\n(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})'

        def separate_blocks(match):
            text_line, number, timing = match.groups()
            return f"{text_line}\n\n{number}\n{timing}"

        matches4 = re.findall(pattern4, fixed_content)
        if matches4:
            fixed_content = re.sub(pattern4, separate_blocks, fixed_content)
            total_fixes += len(matches4)
            if log_callback:
                log("SUCCESS", f"✅ Separated stuck blocks: {len(matches4)}")

        # ✅ Xóa dòng trắng thừa
        fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)

        if total_fixes > 0:
            if log_callback:
                log("SUCCESS", f"🎉 SRT format fixed: {total_fixes} changes (NO NUMBERS ROUNDED)")
        else:
            if log_callback:
                log("INFO", "✅ SRT format was already correct")

        return fixed_content.strip()

    except Exception as e:
        if log_callback:
            log("ERROR", f"❌ Error in SRT fix: {str(e)}")
        return srt_content


    
def get_default_words_per_line(target_language: str) -> int:
    """Get default words per line for target language"""
    # Language-specific defaults (kept for compatibility)
    defaults = {
        "Chinese": 6,
        "Japanese": 8,
        "Korean": 7,
        "Arabic": 6,
        "English": 8,
        "Spanish": 8,
        "French": 8,
        "German": 6,
        "Russian": 7,
        "Vietnamese": 8
    }
    
    # Clean language name
    clean_lang = target_language.split(" ")[1] if " " in target_language else target_language
    clean_lang = clean_lang.replace("🇺🇸", "").replace("🇨🇳", "").strip()
    
    return defaults.get(clean_lang, 8)



