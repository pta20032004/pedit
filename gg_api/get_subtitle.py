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
import re
import random

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
        
        # print("=================== FFmpeg Command ===================")
        # print(' '.join(cmd))
        # print("======================================================")

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
    
    # Clean language names - ONLY POPULAR LANGUAGES
    lang_map = {
        # === AUTO DETECT ===
    "🔍 Auto Detect": "auto-detect",
    
    # === A ===
    "🇦🇱 Albanian": "Albanian",
    "🇸🇦 Arabic": "Arabic",
    "🇦🇪 Arabic (UAE)": "Arabic", 
    "🇪🇬 Arabic (Egypt)": "Arabic",
    "🇦🇷 Argentina (Spanish)": "Spanish",
    
    # === B ===
    "🇧🇩 Bangladesh": "Bengali",
    "🇧🇩 Bengali": "Bengali",
    "🇧🇦 Bosnian": "Bosnian",
    "🇧🇷 Brazil (Portuguese)": "Portuguese",
    "🇧🇬 Bulgaria": "Bulgarian",
    "🇧🇬 Bulgarian": "Bulgarian",
    
    # === C ===
    "🇪🇸 Catalan": "Catalan",
    "🇨🇱 Chile (Spanish)": "Spanish",
    "🇨🇳 China (Simplified)": "Chinese",
    "🇨🇳 Chinese": "Chinese", 
    "🇨🇳 Chinese (Simplified)": "Chinese",
    "🇹🇼 Chinese (Traditional)": "Chinese",
    "🇨🇴 Colombia (Spanish)": "Spanish",
    "🇭🇷 Croatia": "Croatian",
    "🇭🇷 Croatian": "Croatian",
    "🇨🇿 Czech": "Czech",
    "🇨🇿 Czech Republic": "Czech",
    
    # === D ===
    "🇩🇰 Danish": "Danish",
    "🇩🇰 Denmark": "Danish",
    "🇳🇱 Dutch": "Dutch",
    
    # === E ===
    "🇺🇸 English": "English", 
    "🇺🇸 English (US)": "English",
    "🇬🇧 English (UK)": "English", 
    "🇨🇦 English (CA)": "English", 
    "🇨🇦 English (Canada)": "English",
    "🇦🇺 English (Australia)": "English",
    "🇳🇿 English (New Zealand)": "English",
    "🇮🇪 English (Ireland)": "English",
    "🇿🇦 English (South Africa)": "English",
    "🇪🇪 Estonia": "Estonian",
    "🇪🇪 Estonian": "Estonian",
    
    # === F ===
    "🇵🇭 Filipino": "Filipino",
    "🇫🇮 Finland": "Finnish",
    "🇫🇮 Finnish": "Finnish",
    "🇫🇷 France": "French", 
    "🇫🇷 French": "French", 
    
    # === G ===
    "🇩🇪 German": "German", 
    "🇩🇪 Germany": "German",
    "🇬🇷 Greece": "Greek",
    "🇬🇷 Greek": "Greek",
    "🇮🇳 Gujarati": "Gujarati",
    
    # === H ===
    "🇮🇱 Hebrew": "Hebrew",
    "🇮🇳 Hindi": "Hindi",
    "🇮🇳 India (Hindi)": "Hindi",
    "🇭🇺 Hungary": "Hungarian",
    "🇭🇺 Hungarian": "Hungarian",
    
    # === I ===
    "🇮🇩 Indonesia": "Indonesian", 
    "🇮🇩 Indonesian": "Indonesian", 
    "🇮🇹 Italian": "Italian", 
    "🇮🇹 Italy": "Italian",
    
    # === J ===
    "🇯🇵 Japan": "Japanese", 
    "🇯🇵 Japanese": "Japanese", 
    
    # === K ===
    "🇮🇳 Kannada": "Kannada",
    "🇰🇷 Korean": "Korean",
    "🇰🇷 South Korea": "Korean",
    
    # === L ===
    "🇱🇻 Latvia": "Latvian",
    "🇱🇻 Latvian": "Latvian",
    "🇱🇹 Lithuania": "Lithuanian",
    "🇱🇹 Lithuanian": "Lithuanian",
    
    # === M ===
    "🇲🇰 Macedonian": "Macedonian",
    "🇲🇾 Malay": "Malay",
    "🇲🇾 Malaysia": "Malay",
    "🇮🇳 Malayalam": "Malayalam",
    "🇮🇳 Marathi": "Marathi", 
    "🇲🇽 Mexico (Spanish)": "Spanish",
    
    # === N ===
    "🇳🇱 Netherlands": "Dutch",
    "🇳🇴 Norway": "Norwegian", 
    "🇳🇴 Norwegian": "Norwegian", 
    
    # === P ===
    "🇵🇰 Pakistan": "Urdu",
    "🇮🇷 Persian": "Persian",
    "🇵🇪 Peru (Spanish)": "Spanish",
    "🇵🇭 Philippines": "Filipino",
    "🇵🇱 Poland": "Polish",
    "🇵🇱 Polish": "Polish",
    "🇵🇹 Portugal": "Portuguese",
    "🇵🇹 Portuguese": "Portuguese", 
    
    # === R ===
    "🇷🇴 Romania": "Romanian",
    "🇷🇴 Romanian": "Romanian", 
    "🇷🇺 Russia": "Russian",
    "🇷🇺 Russian": "Russian", 
    
    # === S ===
    "🇷🇸 Serbia": "Serbian",
    "🇷🇸 Serbian": "Serbian",
    "🇸🇰 Slovakia": "Slovak",
    "🇸🇰 Slovak": "Slovak",
    "🇸🇮 Slovenia": "Slovenian",
    "🇸🇮 Slovenian": "Slovenian",
    "🇪🇸 Spain": "Spanish",
    "🇪🇸 Spanish": "Spanish", 
    "🇸🇪 Sweden": "Swedish",
    "🇸🇪 Swedish": "Swedish",
    
    # === T ===
    "🇮🇳 Tamil": "Tamil",
    "🇮🇳 Telugu": "Telugu", 
    "🇹🇭 Thai": "Thai",
    "🇹🇭 Thailand": "Thai",
    "🇹🇼 Taiwan (Traditional)": "Chinese",
    "🇹🇷 Turkey": "Turkish",
    "🇹🇷 Turkish": "Turkish",
    
    # === U ===
    "🇺🇦 Ukraine": "Ukrainian",
    "🇺🇦 Ukrainian": "Ukrainian",
    "🇵🇰 Urdu": "Urdu",
    
    # === V ===
    "🇻🇪 Venezuela (Spanish)": "Spanish",
    "🇻🇳 Vietnam": "Vietnamese",
    "🇻🇳 Vietnamese": "Vietnamese"

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


def generate_subtitles_step1(audio_path: str, api_key: str, source_lang: str, 
                                    target_lang: str, log_callback=None) -> Tuple[bool, str, str]:
    """
    🔥 ENHANCED: Step 1 với fallback Gemini 2.5 Flash và random API pool
    """
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    if not GENAI_AVAILABLE:
        return False, "", "google-generativeai library not available"
    
    try:
        # Configure API
        genai.configure(api_key=api_key)
        log("INFO", "🔑 Gemini API configured for Enhanced Step 1")
        
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
        
        # 🔥 BƯỚC 1: Thử Gemini-2.5-pro trước
        log("INFO", "📝 Step 1.1: Trying Gemini-2.5-pro for subtitle generation...")
        
        try:
            model = genai.GenerativeModel("gemini-2.5-pro")
            
            response = model.generate_content(
                [prompt, audio_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                srt_content = response.text.strip()
                log("SUCCESS", "✅ Step 1.1: Subtitles generated with Gemini-2.5-pro")
                return True, srt_content, "Generated with Gemini-2.5-pro"
            else:
                log("WARNING", "⚠️ Step 1.1: Gemini-2.5-pro returned empty/short response")
                
        except Exception as e:
            log("WARNING", f"⚠️ Step 1.1: Gemini-2.5-pro failed: {str(e)}")
        
        # 🔥 BƯỚC 1.1: Fallback to Gemini-2.5-flash
        log("INFO", "📝 Step 1.2: Fallback to Gemini-2.5-flash...")
        
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            response = model.generate_content(
                [prompt, audio_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                srt_content = response.text.strip()
                log("SUCCESS", "✅ Step 1.2: Subtitles generated with Gemini-2.5-flash")
                return True, srt_content, "Generated with Gemini-2.5-flash"
            else:
                log("WARNING", "⚠️ Step 1.2: Gemini-2.5-flash returned empty/short response")
                
        except Exception as e:
            log("WARNING", f"⚠️ Step 1.2: Gemini-2.5-flash failed: {str(e)}")
        
        # 🔥 BƯỚC 1.2: Random API pool fallback
        log("INFO", "📝 Step 1.3: Trying random API keys from pool...")
        
        # Load backup API keys
        backup_keys = load_api_keys()
        if backup_keys:
            # Remove current key from backup list
            backup_keys = [key for key in backup_keys if key != api_key]
            
            # Randomly select up to 5 keys
            random_keys = random.sample(backup_keys, min(5, len(backup_keys)))
            log("INFO", f"🎲 Step 1.3: Trying {len(random_keys)} random API keys...")
            
            for attempt, random_key in enumerate(random_keys, 1):
                log("INFO", f"🔄 Step 1.3.{attempt}: Trying API key {random_key[:10]}...{random_key[-4:]}")
                
                try:
                    # Test key first
                    if not test_api_key_simple(random_key, log_callback):
                        log("WARNING", f"⚠️ API key {attempt} failed validation, skipping...")
                        continue
                    
                    # Configure with random key
                    genai.configure(api_key=random_key)
                    
                    # Try with Gemini-2.5-flash (faster model for fallback)
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    response = model.generate_content(
                        [prompt, audio_file],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=8192
                        )
                    )
                    
                    if response.text and len(response.text.strip()) > 50:
                        srt_content = response.text.strip()
                        log("SUCCESS", f"✅ Step 1.3.{attempt}: Success with random API key!")
                        return True, srt_content, f"Generated with random API key #{attempt}"
                    else:
                        log("WARNING", f"⚠️ Step 1.3.{attempt}: Empty response from random key")
                        
                except Exception as e:
                    log("WARNING", f"⚠️ Step 1.3.{attempt}: Random key failed: {str(e)}")
                    continue
        else:
            log("WARNING", "⚠️ Step 1.3: No backup API keys available")
        
        # 🔥 THẤT BẠI HOÀN TOÀN
        log("ERROR", "❌ Step 1: All generation methods failed")
        return False, "", "All subtitle generation methods failed"
        
    except Exception as e:
        log("ERROR", f"❌ Step 1: Critical API error: {str(e)}")
        return False, "", f"Step 1 critical error: {str(e)}"


def generate_subtitles_step2(raw_subtitle: str, api_key: str, log_callback=None) -> Tuple[bool, str, str]:
    """
    🔥 NEW VERSION: Step 2 với custom format fixing logic thay thế hoàn toàn logic cũ
    """
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    if not GENAI_AVAILABLE:
        return False, "", "google-generativeai library not available"
    
    if not raw_subtitle or len(raw_subtitle.strip()) < 10:
        log("ERROR", "❌ Step 2: Raw subtitle is empty or too short")
        return False, "", "Raw subtitle is empty"
    
    try:
        # Configure API
        genai.configure(api_key=api_key)
        log("INFO", "🔧 Step 2: Starting NEW format correction with custom logic...")
        
        # 🔥 IMPROVED PROMPT for better SRT format
        improved_prompt = f"""Convert the following text into proper .srt format. Requirements:

1. Sequential numbering: 1, 2, 3, 4...
2. Timestamp format: HH:MM:SS,mmm --> HH:MM:SS,mmm (exactly this format)
3. Subtitle text on separate lines
4. Blank line between each subtitle block

Example format:
1
00:00:00,000 --> 00:00:03,500
First subtitle text here

2
00:00:03,500 --> 00:00:07,200
Second subtitle text here

Output ONLY the corrected .srt content, no explanations:

{raw_subtitle}
"""
        
        # 🔥 TRY GEMINI-2.0-FLASH-LITE FIRST
        log("INFO", "🔧 Step 2.1: Trying Gemini-2.0-flash-lite for initial correction...")
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            
            response = model.generate_content(
                improved_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,  # Lower temperature for more consistent formatting
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                gemini_output = response.text.strip()
                log("SUCCESS", "✅ Step 2.1: Initial format correction completed")
                
                # 🔥 APPLY NEW CUSTOM FORMAT FIXING LOGIC
                log("INFO", "🔧 Step 2.2: Applying NEW custom format fixing logic...")
                
                try:
                    final_corrected = fix_errors_format(gemini_output)
                    log("SUCCESS", "✅ Step 2.2: NEW custom format fixing completed")
                    
                    # Quick validation
                    if len(final_corrected.strip()) > 20 and '-->' in final_corrected:
                        return True, final_corrected, "Format corrected with Gemini + NEW custom logic"
                    else:
                        log("WARNING", "⚠️ Step 2.2: Custom fixing resulted in invalid content")
                        
                except Exception as fix_error:
                    log("WARNING", f"⚠️ Step 2.2: Custom fixing failed: {str(fix_error)}")
                    # Fallback to Gemini output if custom fixing fails
                    return True, gemini_output, f"Gemini correction only (custom fix failed): {str(fix_error)}"
                    
            else:
                log("WARNING", "⚠️ Step 2.1: Gemini-2.0-flash-lite returned empty/short response")
                
        except Exception as gemini_error:
            log("WARNING", f"⚠️ Step 2.1: Gemini-2.0-flash-lite failed: {str(gemini_error)}")
        
        # 🔥 FALLBACK 1: Try Gemini-2.0-flash (regular)
        log("INFO", "🔧 Step 2.3: Fallback to Gemini-2.0-flash...")
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = model.generate_content(
                improved_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                gemini_output = response.text.strip()
                log("SUCCESS", "✅ Step 2.3: Gemini-2.0-flash correction completed")
                
                # Apply custom fixing
                try:
                    final_corrected = fix_errors_format(gemini_output)
                    log("SUCCESS", "✅ Step 2.3: Custom fixing applied to Gemini-2.0-flash output")
                    return True, final_corrected, "Format corrected with Gemini-2.0-flash + custom logic"
                except Exception as fix_error:
                    log("WARNING", f"⚠️ Step 2.3: Custom fixing failed: {str(fix_error)}")
                    return True, gemini_output, f"Gemini-2.0-flash only: {str(fix_error)}"
                    
        except Exception as e:
            log("WARNING", f"⚠️ Step 2.3: Gemini-2.0-flash failed: {str(e)}")
        
        # 🔥 FALLBACK 2: Direct custom fixing on raw subtitle
        log("INFO", "🔧 Step 2.4: Applying NEW custom format fixing directly to raw subtitle...")
        
        try:
            final_corrected = fix_errors_format(raw_subtitle)
            log("SUCCESS", "✅ Step 2.4: NEW custom format fixing applied to raw subtitle")
            
            # Basic validation
            if len(final_corrected.strip()) > 20:
                return True, final_corrected, "Format corrected with NEW custom logic only"
            else:
                log("WARNING", "⚠️ Step 2.4: Custom fixing resulted in too short content")
                
        except Exception as fix_error:
            log("ERROR", f"❌ Step 2.4: Direct custom fixing failed: {str(fix_error)}")
        
        # 🔥 LAST RESORT: Return raw subtitle
        log("WARNING", "⚠️ Step 2: All correction methods failed, using raw subtitle")
        return True, raw_subtitle, "No format correction applied - using raw output"
            
    except Exception as e:
        log("ERROR", f"❌ Step 2: Critical format correction error: {str(e)}")
        log("INFO", "📝 Step 2: Using raw subtitle as emergency fallback...")
        
        # Emergency fallback
        try:
            emergency_corrected = fix_errors_format(raw_subtitle)
            return True, emergency_corrected, f"Emergency custom fixing: {str(e)}"
        except Exception as emergency_error:
            log("ERROR", f"❌ Step 2: Emergency fixing also failed: {str(emergency_error)}")
            return True, raw_subtitle, f"Raw subtitle returned due to errors: {str(e)}"
        
def errors_info_and_fix_format(text):
    """
    Phân tích và fix các lỗi format SRT theo logic mới:
    1. Xóa markdown code blocks ```srt ... ```
    2. Thêm dòng trống giữa các blocks
    """
    lines = text.split('\n')
    
    # 🔥 BƯỚC 1: Xóa markdown code blocks
    if lines and lines[0].strip() == "```srt":
        lines = lines[1:]
        print("✅ Removed opening ```srt marker")
    
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
        print("✅ Removed closing ``` marker")
    
    # 🔥 BƯỚC 2: Thêm dòng trống giữa các blocks
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        current_line = lines[i].strip()
        
        # Kiểm tra nếu là số block (1, 2, 3, ...)
        if current_line.isdigit():
            block_number = int(current_line)
            
            # Nếu không phải block đầu tiên và dòng trước không trống
            if block_number > 1 and i > 0 and lines[i-1].strip() != "":
                fixed_lines.append("")  # Thêm dòng trống
                print(f"✅ Added blank line before block {block_number}")
        
        fixed_lines.append(lines[i])
        i += 1
    
    return '\n'.join(fixed_lines)


def fix_timestamp_format(timestamp_str):
    """
    Fix timestamp theo ĐÚNG 5 rules của bạn
    """
    timestamp = timestamp_str.strip()
    original = timestamp_str
    
    # 🔥 RULE 3.1: Truncate milliseconds > 3 digits
    if ',' in timestamp:
        time_part, ms_part = timestamp.split(',', 1)
        if len(ms_part) > 3:
            ms_part = ms_part[:3]  # Xóa các chữ số thừa
            timestamp = f"{time_part},{ms_part}"
            print(f"✅ 3.1: Truncated milliseconds: {original} → {timestamp}")
    
    # Tách lại sau khi truncate
    if ',' in timestamp:
        time_part, ms_part = timestamp.split(',', 1)
    else:
        time_part = timestamp
        ms_part = "000"
    
    time_segments = time_part.split(':')
    
    # 🔥 RULE 3.2: aa:bb:ccc hoặc aa:bb,ccc → 00:aa:bb,ccc
    if len(time_segments) == 2:
        # Case: aa:bb,ccc (đã có comma)
        aa, bb = time_segments
        fixed_timestamp = f"00:{aa.zfill(2)}:{bb.zfill(2)},{ms_part}"
        print(f"✅ 3.2: aa:bb,ccc → 00:aa:bb,ccc: {original} → {fixed_timestamp}")
        return fixed_timestamp
        
    elif len(time_segments) == 3:
        aa, bb, cc = time_segments
        
        # 🔥 CHECK: Có phải aa:bb:ccc format không?
        if len(cc) == 3 and cc.isdigit():
            # aa:bb:ccc → 00:aa:bb,ccc
            fixed_timestamp = f"00:{aa.zfill(2)}:{bb.zfill(2)},{cc}"
            print(f"✅ 3.2: aa:bb:ccc → 00:aa:bb,ccc: {original} → {fixed_timestamp}")
            return fixed_timestamp
        else:
            # Normal HH:MM:SS format, tiếp tục xử lý rule 3.5
            pass
    
    # 🔥 RULE 3.3: aa:bb:cc:ddd → aa:bb:cc,ddd
    elif len(time_segments) == 4:
        aa, bb, cc, ddd = time_segments
        fixed_timestamp = f"{aa}:{bb}:{cc},{ddd}"
        print(f"✅ 3.3: aa:bb:cc:ddd → aa:bb:cc,ddd: {original} → {fixed_timestamp}")
        timestamp = fixed_timestamp
        time_segments = [aa, bb, cc]
        ms_part = ddd
    
    # 🔥 RULE 3.4: aa:bb:cc:dd:eee → bb:cc:dd,eee
    elif len(time_segments) == 5:
        aa, bb, cc, dd, eee = time_segments
        fixed_timestamp = f"{bb}:{cc}:{dd},{eee}"
        print(f"✅ 3.4: aa:bb:cc:dd:eee → bb:cc:dd,eee: {original} → {fixed_timestamp}")
        timestamp = fixed_timestamp
        time_segments = [bb, cc, dd]
        ms_part = eee
    
    # 🔥 RULE 3.5: Pad single digits với zeros
    if len(time_segments) >= 3:
        hh, mm, ss = time_segments[0], time_segments[1], time_segments[2]
        
        # Pad mỗi segment thành 2 chữ số
        hh = hh.zfill(2)
        mm = mm.zfill(2)
        ss = ss.zfill(2)
        
        # Pad milliseconds thành 3 chữ số
        ms_part = ms_part.ljust(3, '0')[:3]
        
        final_timestamp = f"{hh}:{mm}:{ss},{ms_part}"
        
        if final_timestamp != original:
            print(f"✅ 3.5: Padded zeros: {original} → {final_timestamp}")
        
        return final_timestamp
    
    # Fallback: return với basic formatting
    return f"00:00:00,{ms_part.ljust(3, '0')[:3]}"

def fix_errors_format(text):
    """
    Main function để fix tất cả lỗi format với iterative approach
    """
    print("🔄 Starting SRT format fixing process...")
    
    # Bước 1 & 2: Fix markdown và spacing
    text = errors_info_and_fix_format(text)
    
    # Bước 3: Iterative timestamp fixing
    test = True
    iter_count = 0
    max_iterations = 100
    
    while test and iter_count < max_iterations:
        iter_count += 1
        print(f"🔄 Iteration {iter_count}: Scanning for timestamp errors...")
        
        lines = text.split('\n')
        number_errors = 0
        line_start = 1
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            current_line = lines[i].strip()
            
            # Kiểm tra nếu là số block
            if current_line.isdigit() and int(current_line) == line_start:
                # Tìm thấy block mới
                fixed_lines.append(lines[i])  # Thêm số block
                
                # Kiểm tra dòng timestamp (dòng tiếp theo)
                if i + 1 < len(lines):
                    timestamp_line = lines[i + 1].strip()
                    
                    # Kiểm tra format "xxxx --> yyyy" 
                    if '-->' in timestamp_line:
                        parts = timestamp_line.split('-->')
                        if len(parts) == 2:
                            start_time = parts[0].strip()
                            end_time = parts[1].strip()
                            
                            # Fix cả hai timestamps
                            fixed_start = fix_timestamp_format(start_time)
                            fixed_end = fix_timestamp_format(end_time)
                            
                            fixed_timestamp_line = f"{fixed_start} --> {fixed_end}"
                            
                            # Kiểm tra nếu có thay đổi
                            if fixed_timestamp_line != timestamp_line:
                                number_errors += 1
                                print(f"🔧 Fixed block {line_start}: {timestamp_line} → {fixed_timestamp_line}")
                            
                            fixed_lines.append(fixed_timestamp_line)
                            i += 2  # Skip timestamp line đã xử lý
                        else:
                            fixed_lines.append(lines[i + 1])
                            i += 2
                    else:
                        fixed_lines.append(lines[i + 1])
                        i += 2
                else:
                    i += 1
                
                line_start += 1
            else:
                fixed_lines.append(lines[i])
                i += 1
        
        # Cập nhật text với fixes
        text = '\n'.join(fixed_lines)
        
        print(f"📊 Iteration {iter_count}: Found and fixed {number_errors} timestamp errors")
        
        # Nếu không có lỗi nào, dừng loop
        if number_errors == 0:
            test = False
            print("✅ No more errors found. Format fixing complete!")
    
    if iter_count >= max_iterations:
        print(f"⚠️ Reached maximum iterations ({max_iterations}). Some errors may remain.")
    
    return text

def process_video_for_subtitles(video_path: str, api_key: str, source_lang: str, 
                                       target_lang: str, words_per_line: int = None, 
                                       ffmpeg_path: str = None, log_callback=None) -> Tuple[bool, str, str]:
    """
    🔥 UPDATED: Two-step subtitle generation với NEW custom format fixing logic
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
            
            # 🔥 ENHANCED STEP 1: Multiple fallback strategies
            log("INFO", "🤖 Starting Enhanced Step 1: Subtitle Generation with Fallbacks")
            
            step1_success, raw_subtitle, step1_message = generate_subtitles_step1(
                temp_audio, api_key, source_lang, target_lang, log_callback
            )
            
            if not step1_success:
                return False, "", f"Enhanced Step 1 failed: {step1_message}"
            
            # Basic validation of Step 1 output
            if not raw_subtitle or len(raw_subtitle.strip()) < 10:
                return False, "", "Step 1 produced empty or too short subtitle content"
            
            log("INFO", f"📝 Enhanced Step 1 complete. Subtitle length: {len(raw_subtitle)} characters")
            log("SUCCESS", f"✅ Step 1 Result: {step1_message}")
            
            # 🔥 NEW STEP 2: Enhanced format correction with NEW custom logic
            log("INFO", "🔧 Starting NEW Step 2: Enhanced Format Correction with Custom Logic")
            
            step2_success, final_subtitle, step2_message = generate_subtitles_step2(
                raw_subtitle, api_key, log_callback
            )
            
            if step2_success:
                log("SUCCESS", f"🎉 NEW enhanced two-step process complete!")
                log("INFO", f"📋 Final result: {step2_message}")
                
                # 🔥 REMOVED: No longer call fix_srt_timestamps() - NEW logic handles everything
                # OLD CODE REMOVED: final_subtitle_fixed = fix_srt_timestamps(final_subtitle, log_callback)
                
                # 🔥 NEW: Direct return of Step 2 output (already fixed by new logic)
                if final_subtitle and len(final_subtitle.strip()) > 10:
                    log("SUCCESS", "✅ NEW format fixing complete - returning Step 2 output")
                    return True, final_subtitle, f"NEW Enhanced success: {step1_message} + {step2_message}"
                else:
                    log("WARNING", "⚠️ Final subtitle is empty, using Step 1 output with NEW fixing")
                    
                    # Apply NEW custom fixing to Step 1 output as fallback
                    try:
                        raw_subtitle_fixed = fix_errors_format(raw_subtitle)
                        log("SUCCESS", "✅ NEW custom fixing applied to Step 1 output")
                        return True, raw_subtitle_fixed, f"NEW Enhanced Step 1 with custom fixing: {step1_message}"
                    except Exception as fix_error:
                        log("WARNING", f"⚠️ NEW custom fixing failed: {str(fix_error)}")
                        return True, raw_subtitle, f"NEW Enhanced Step 1 only: {step1_message}"
            else:
                log("WARNING", "⚠️ NEW Step 2 failed, using Step 1 output with NEW custom fixing")
                
                # Apply NEW custom fixing to Step 1 output
                try:
                    raw_subtitle_fixed = fix_errors_format(raw_subtitle)
                    log("SUCCESS", "✅ NEW custom fixing applied to Step 1 output")
                    return True, raw_subtitle_fixed, f"NEW Enhanced Step 1 with custom fixing: {step1_message}"
                except Exception as fix_error:
                    log("WARNING", f"⚠️ NEW custom fixing failed: {str(fix_error)}")
                    return True, raw_subtitle, f"NEW Enhanced Step 1 only: {step1_message}"
                
        finally:
            # Cleanup temp audio file
            if os.path.exists(temp_audio):
                try:
                    os.unlink(temp_audio)
                    log("INFO", "🧹 Temporary audio file cleaned up")
                except:
                    pass
            
    except Exception as e:
        log("ERROR", f"❌ NEW Enhanced pipeline error: {str(e)}")
        import traceback
        log("ERROR", f"📋 Traceback: {traceback.format_exc()}")
        return False, "", f"NEW Enhanced pipeline error: {str(e)}"

def get_default_words_per_line(target_language: str) -> int:
    """Get default words per line for target language"""
    # Language-specific defaults - EXPANDED VERSION
    defaults = {
        # === LATIN SCRIPT LANGUAGES ===
        "English": 8, "Spanish": 8, "French": 8, "Italian": 8, "Portuguese": 8,
        "Romanian": 8, "Catalan": 8, "Galician": 8, "Indonesian": 8, "Malay": 8,
        "Filipino": 8, "Vietnamese": 8, "Albanian": 7, "Bosnian": 7, "Croatian": 7,
        "Romanian": 8, "Bulgarian": 7, "Croatian": 7, "Serbian": 7,
        "Lithuanian": 6, "Latvian": 7, "Estonian": 7,
        "Swedish": 7, "Danish": 7, "Norwegian": 7,
        "Hungarian": 6, "Finnish": 6, "Turkish": 6,  # Agglutinative languages
        "Greek": 7,
        
        # === COMPOUND WORD LANGUAGES ===
        "German": 6, "Dutch": 6, "Icelandic": 6, "Lithuanian": 6,
        
        # === AGGLUTINATIVE LANGUAGES ===
        "Finnish": 6, "Hungarian": 6, "Turkish": 6,
        
        # === CJK SCRIPTS ===
        "Chinese": 6, "Japanese": 8, "Korean": 7,
        
        # === ARABIC SCRIPT ===
        "Arabic": 6, "Persian": 6, "Urdu": 6, "Hebrew": 6,
        
        # === SOUTH ASIAN SCRIPTS ===
        "Hindi": 7, "Bengali": 7, "Gujarati": 7, "Marathi": 7,
        "Tamil": 6, "Telugu": 6, "Kannada": 6, "Malayalam": 6,
        
        # === SOUTHEAST ASIAN ===
        "Thai": 6,
    }
    
    # Clean language name
    clean_lang = target_language.split(" ")[1] if " " in target_language else target_language
    
    # Remove all emoji flags
    import re
    clean_lang = re.sub(r'🇦-🇿', '', clean_lang).strip()
    
    # Handle country format like "Brazil (Portuguese)" -> "Portuguese"
    if "(" in clean_lang:
        # Extract language from parentheses
        if ")" in clean_lang:
            clean_lang = clean_lang.split("(")[1].split(")")[0].strip()
        else:
            clean_lang = clean_lang.split("(")[0].strip()
    
    return defaults.get(clean_lang, 8)



