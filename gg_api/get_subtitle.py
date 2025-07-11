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
    🔥 ENHANCED: Step 2 với fallback Gemini 2.0 Flash và improved prompt
    """
    
    def log(level, message):
        if log_callback:
            log_callback(level, message)
    
    if not GENAI_AVAILABLE:
        return False, "", "google-generativeai library not available"
    
    try:
        # Configure API
        genai.configure(api_key=api_key)
        log("INFO", "🔧 Step 2: Enhanced format correction starting...")
        
        # 🔥 IMPROVED PROMPT
        improved_prompt = f"""Convert the following passage into standard .srt format, for example:
1
00:00:03,500 --> 00:00:06,008
Subtitle text here

2  
00:00:06,008 --> 00:00:10,000
Next subtitle text

with each block separated by one line.
Output in proper .srt file format.

Content to convert:
{raw_subtitle}
"""
        
        # 🔥 BƯỚC 2.1: Thử Gemini-2.0-flash-lite trước
        log("INFO", "🔧 Step 2.1: Trying Gemini-2.0-flash-lite for format correction...")
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            
            response = model.generate_content(
                improved_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                corrected_srt = response.text.strip()
                log("SUCCESS", "✅ Step 2.1: Format corrected with Gemini-2.0-flash-lite")
                return True, corrected_srt, "Format corrected with Gemini-2.0-flash-lite"
            else:
                log("WARNING", "⚠️ Step 2.1: Gemini-2.0-flash-lite returned empty/short response")
                
        except Exception as e:
            log("WARNING", f"⚠️ Step 2.1: Gemini-2.0-flash-lite failed: {str(e)}")
        
        # 🔥 BƯỚC 2.2: Fallback to Gemini-2.0-flash
        log("INFO", "🔧 Step 2.2: Fallback to Gemini-2.0-flash...")
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = model.generate_content(
                improved_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192
                )
            )
            
            if response.text and len(response.text.strip()) > 50:
                corrected_srt = response.text.strip()
                log("SUCCESS", "✅ Step 2.2: Format corrected with Gemini-2.0-flash")
                return True, corrected_srt, "Format corrected with Gemini-2.0-flash"
            else:
                log("WARNING", "⚠️ Step 2.2: Gemini-2.0-flash returned empty/short response")
                
        except Exception as e:
            log("WARNING", f"⚠️ Step 2.2: Gemini-2.0-flash failed: {str(e)}")
        
        # 🔥 BƯỚC 2.3: Sử dụng raw subtitle từ Step 1
        log("INFO", "🔧 Step 2.3: Using raw subtitle from Step 1 (no format correction)")
        return True, raw_subtitle, "No format correction applied - using raw output"
            
    except Exception as e:
        log("WARNING", f"⚠️ Step 2: Format correction error: {str(e)}")
        log("INFO", "📝 Step 2: Using original subtitle without format correction")
        return True, raw_subtitle, f"Format correction failed, using original: {str(e)}"



def process_video_for_subtitles(video_path: str, api_key: str, source_lang: str, 
                                       target_lang: str, words_per_line: int = None, 
                                       ffmpeg_path: str = None, log_callback=None) -> Tuple[bool, str, str]:
    """
    🔥 ENHANCED: Two-step subtitle generation với multiple fallback strategies
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
            
            # 🔥 ENHANCED STEP 2: Format correction with fallbacks
            log("INFO", "🔧 Starting Enhanced Step 2: Format Correction with Fallbacks")
            
            step2_success, final_subtitle, step2_message = generate_subtitles_step2(
                raw_subtitle, api_key, log_callback
            )
            
            if step2_success:
                log("SUCCESS", f"🎉 Enhanced two-step process complete!")
                log("INFO", f"📋 Final result: {step2_message}")
                
                # 🔥 FINAL: Fix SRT format
                if final_subtitle and len(final_subtitle.strip()) > 10:
                    log("INFO", "🔧 Applying final SRT timestamp format fix...")
                    final_subtitle_fixed = fix_srt_timestamps(final_subtitle, log_callback)
                    
                    return True, final_subtitle_fixed, f"Enhanced success: {step1_message} + {step2_message}"
                else:
                    log("WARNING", "⚠️ Final subtitle is empty, using Step 1 output")
                    raw_subtitle_fixed = fix_srt_timestamps(raw_subtitle, log_callback)
                    return True, raw_subtitle_fixed, f"Enhanced Step 1 only: {step1_message}"
            else:
                log("WARNING", "⚠️ Enhanced Step 2 failed, using Step 1 output with format fix")
                raw_subtitle_fixed = fix_srt_timestamps(raw_subtitle, log_callback)
                return True, raw_subtitle_fixed, f"Enhanced Step 1 only: {step1_message}"
                
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
        return False, "", f"Enhanced pipeline error: {str(e)}"



def fix_srt_timestamps(srt_content: str, log_callback=None) -> str:
    """
    🔥 FIXED: Fix SRT timestamps hoàn toàn - MULTIPLE PASSES + VALIDATION
    """
    if log_callback:
        log_callback("INFO", "🔧 Starting COMPLETE SRT timestamp fix...")
    
    try:
        # Step 1: Multiple passes để fix timestamps
        content = _fix_timestamps_multiple_passes(srt_content, log_callback)
        
        # Step 2: Fix spacing giữa blocks  
        content = _fix_srt_spacing(content, log_callback)
        
        # Step 3: Validation cuối cùng
        errors = _validate_srt_format(content, log_callback)
        
        if errors:
            if log_callback:
                log_callback("WARNING", f"⚠️ Found {len(errors)} validation errors, using best effort result")
                for error in errors[:3]:  # Show first 3 errors
                    log_callback("WARNING", f"   - {error}")
            # Vẫn return result thay vì reject hoàn toàn
            return content
        else:
            if log_callback:
                log_callback("SUCCESS", "✅ SRT format validation PASSED!")
            return content
            
    except Exception as e:
        if log_callback:
            log_callback("ERROR", f"❌ Error in complete SRT fix: {str(e)}")
        return srt_content  # Fallback to original


def _parse_timestamp_intelligent(timestamp_str: str) -> tuple:
    """Parse timestamp thông minh với validation"""
    
    # Clean input
    ts = timestamp_str.strip().replace('.', ',')
    
    # Extract millisecond
    if ',' in ts:
        time_part, ms_part = ts.split(',', 1)  # Only split on first comma
        # Pad millisecond to 3 digits, truncate if longer
        ms_part = ms_part.ljust(3, '0')[:3]
        try:
            ms = int(ms_part)
        except ValueError:
            ms = 0
    else:
        time_part = ts
        ms = 0
    
    # Parse time components
    parts = time_part.split(':')
    
    try:
        if len(parts) == 2:
            # MM:SS format
            minutes, seconds = [int(p) for p in parts]
            hours = 0
        elif len(parts) == 3:
            # HH:MM:SS format
            hours, minutes, seconds = [int(p) for p in parts]
        else:
            raise ValueError(f"Invalid time format: {len(parts)} parts")
        
        # Validation với auto-correction
        if not (0 <= hours <= 23):
            hours = min(23, max(0, hours))
        if not (0 <= minutes <= 59):
            minutes = min(59, max(0, minutes))
        if not (0 <= seconds <= 59):
            seconds = min(59, max(0, seconds))
        if not (0 <= ms <= 999):
            ms = min(999, max(0, ms))
            
        return hours, minutes, seconds, ms
        
    except ValueError as e:
        # Fallback: parse lỗi thì trả về 0:0:0,0
        return 0, 0, 0, 0


def _format_timestamp(hours: int, minutes: int, seconds: int, ms: int) -> str:
    """Format timestamp thành chuẩn SRT"""
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def _fix_timestamps_multiple_passes(srt_content: str, log_callback=None, max_passes: int = 3) -> str:
    """Fix timestamps với multiple passes"""
    
    content = srt_content
    total_fixes = 0
    
    # Pattern để match tất cả timestamp formats
    timestamp_pattern = r'(\d{1,2}(?::\d{1,2})?:\d{1,2}(?:[.,]\d{1,3})?)\s*-->\s*(\d{1,2}(?::\d{1,2})?:\d{1,2}(?:[.,]\d{1,3})?)'
    
    for pass_num in range(max_passes):
        if log_callback:
            log_callback("INFO", f"🔄 Timestamp fix pass {pass_num + 1}/{max_passes}")
        
        # Find all timestamp lines trong pass này
        matches = list(re.finditer(timestamp_pattern, content))
        
        if not matches:
            if log_callback:
                log_callback("INFO", f"   ✅ No timestamps found to fix in pass {pass_num + 1}")
            break
        
        fixes_in_pass = 0
        
        # Process từ cuối lên đầu để avoid index shifting
        for match in reversed(matches):
            start_ts, end_ts = match.groups()
            
            try:
                # Parse both timestamps
                start_h, start_m, start_s, start_ms = _parse_timestamp_intelligent(start_ts)
                end_h, end_m, end_s, end_ms = _parse_timestamp_intelligent(end_ts)
                
                # Format properly
                fixed_start = _format_timestamp(start_h, start_m, start_s, start_ms)
                fixed_end = _format_timestamp(end_h, end_m, end_s, end_ms)
                
                # Create fixed line
                original_line = match.group(0)
                fixed_line = f"{fixed_start} --> {fixed_end}"
                
                if original_line != fixed_line:
                    # Replace trong content
                    content = content[:match.start()] + fixed_line + content[match.end():]
                    fixes_in_pass += 1
                    
                    if log_callback and fixes_in_pass <= 5:  # Log first 5 fixes
                        log_callback("INFO", f"   ✅ {original_line} → {fixed_line}")
                        
            except Exception as e:
                if log_callback:
                    log_callback("WARNING", f"   ⚠️ Cannot fix '{start_ts} --> {end_ts}': {str(e)}")
        
        total_fixes += fixes_in_pass
        
        if log_callback:
            log_callback("INFO", f"   📊 Pass {pass_num + 1}: {fixes_in_pass} fixes made")
        
        if fixes_in_pass == 0:
            if log_callback:
                log_callback("INFO", "   ✅ No more fixes needed")
            break
    
    if log_callback:
        log_callback("SUCCESS", f"✅ Total timestamp fixes: {total_fixes}")
    
    return content


def _fix_srt_spacing(srt_content: str, log_callback=None) -> str:
    """Fix spacing giữa subtitle blocks"""
    
    if log_callback:
        log_callback("INFO", "📐 Fixing subtitle block spacing...")
    
    # Split thành blocks, loại bỏ empty blocks
    blocks = []
    for block in re.split(r'\n\s*\n', srt_content.strip()):
        block = block.strip()
        if block:  # Skip empty blocks
            blocks.append(block)
    
    if log_callback:
        log_callback("INFO", f"   📋 Found {len(blocks)} subtitle blocks")
    
    # Join với exactly 2 newlines giữa mỗi block
    fixed_content = '\n\n'.join(blocks)
    
    # Ensure content ends with single newline
    if fixed_content and not fixed_content.endswith('\n'):
        fixed_content += '\n'
    
    if log_callback:
        log_callback("SUCCESS", "✅ Block spacing fixed")
    
    return fixed_content


def _validate_srt_format(srt_content: str, log_callback=None) -> list:
    """Validate SRT format và return list errors"""
    
    if log_callback:
        log_callback("INFO", "🔍 Validating final SRT format...")
    
    blocks = srt_content.strip().split('\n\n')
    errors = []
    
    # Standard timestamp pattern để validate
    timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$'
    
    for i, block in enumerate(blocks, 1):
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        
        # Check minimum lines
        if len(lines) < 3:
            errors.append(f"Block {i}: Too few lines ({len(lines)}, need ≥3)")
            continue
        
        # Check block number
        try:
            block_num = int(lines[0].strip())
            if block_num != i:
                errors.append(f"Block {i}: Wrong sequence number ({block_num})")
        except ValueError:
            errors.append(f"Block {i}: Invalid number '{lines[0].strip()}'")
        
        # Check timestamp format
        timestamp_line = lines[1].strip()
        if not re.match(timestamp_pattern, timestamp_line):
            errors.append(f"Block {i}: Invalid timestamp '{timestamp_line}'")
        
        # Check có text content không
        text_lines = [line.strip() for line in lines[2:] if line.strip()]
        if not text_lines:
            errors.append(f"Block {i}: No subtitle text content")
    
    if log_callback:
        if errors:
            log_callback("WARNING", f"⚠️ Validation found {len(errors)} issues")
        else:
            log_callback("SUCCESS", f"✅ Validation passed for {len(blocks)} blocks")
    
    return errors

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



