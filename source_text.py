"""
Source Text Processing Module - FIXED VERSION
Handles adding source text overlay to videos with custom font support
FIXES:
1. Extract source from original filename (not processed filename)
2. Add 25% opacity to source text
"""

import os
import subprocess
import re
from typing import Tuple, Optional, List


def extract_source_from_filename(filename: str) -> Optional[str]:
    """
    Extract source text from filename pattern: xxx_source_SourceName.mp4
    
    Args:
        filename (str): Video filename (should be ORIGINAL filename, not processed)
        
    Returns:
        Optional[str]: Extracted source text or None if pattern not found
    """
    try:
        # Remove file extension
        base_name = os.path.splitext(filename)[0]
        
        # 🔥 FIXED: Remove any processing suffixes first
        # Remove _with_banner, _with_subtitles, etc.
        base_name = re.sub(r'_with_(banner|subtitles|source)', '', base_name)
        
        # Pattern: anything_source_SourceText
        pattern = r'.*_source_(.+)$'
        match = re.search(pattern, base_name, re.IGNORECASE)
        
        if match:
            source_text = match.group(1)
            # Clean up the source text (replace underscores with spaces)
            source_text = source_text.replace('_', ' ').strip()
            return source_text
            
        return None
        
    except Exception as e:
        print(f"Error extracting source from filename: {e}")
        return None


def validate_font_file(font_path: str) -> bool:
    """
    Validate if font file exists and is accessible
    
    Args:
        font_path (str): Path to font file
        
    Returns:
        bool: True if font is valid, False otherwise
    """
    try:
        return os.path.exists(font_path) and os.path.isfile(font_path)
    except Exception:
        return False


def get_plus_jakarta_font_path() -> str:
    """
    Get the path to Plus Jakarta Sans font file
    
    Returns:
        str: Absolute path to font file
    """
    # Get current script directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct font path
    font_path = os.path.join(
        current_dir, 
        "font", 
        "Plus_Jakarta_Sans", 
        "PlusJakartaSans-VariableFont_wght.ttf"
    )
    
    return font_path


def build_source_text_filter(
    source_text: str,
    position_x: int,
    position_y: int,
    font_size: int = 14,
    font_color: str = "white",
    video_width: int = 1080,
    video_height: int = 1920
) -> str:
    """
    Build FFmpeg drawtext filter for source text overlay WITH MAPPING SUPPORT
    """
    try:
        # Get font path
        font_path = get_plus_jakarta_font_path()
        
        # Validate font
        if not validate_font_file(font_path):
            print(f"Warning: Font file not found: {font_path}")
            font_path = None
        
        # Format text with "Source: " prefix
        formatted_text = f"Source: {source_text}"
        
        # Escape special characters
        escaped_text = formatted_text.replace("'", "\\'").replace(":", "\\:")
        
        # 🔥 BOUNDARY VALIDATION FOR MAPPED COORDINATES
        # Estimate text width (rough calculation)
        text_width_estimate = len(formatted_text) * font_size * 0.6
        text_height_estimate = font_size + 10  # Font size + padding
        
        # Calculate safe boundaries
        max_x = max(0, video_width - int(text_width_estimate))
        max_y = max(font_size, video_height - text_height_estimate)
        
        # Apply boundary constraints
        safe_x = max(0, min(position_x, max_x))
        safe_y = max(font_size, min(position_y, max_y))
        safe_font_size = max(8, min(font_size, min(video_width//10, video_height//20)))  # Adaptive max size
        
        print(f"📎 Source text mapping validation:")
        print(f"   📐 Video: {video_width}x{video_height}")
        print(f"   📍 Position: ({position_x}, {position_y}) → ({safe_x}, {safe_y})")
        print(f"   🔤 Font: {font_size}px → {safe_font_size}px")
        print(f"   📏 Text estimate: {int(text_width_estimate)}x{int(text_height_estimate)} pixels")
        
        # Set opacity to 50%
        opacity = 0.35
        
        # Build drawtext filter with safe coordinates
        if font_path:
            font_path_escaped = font_path.replace("\\", "/").replace(":", "\\:")
            drawtext_filter = (
                f"drawtext="
                f"fontfile='{font_path_escaped}':"
                f"text='{escaped_text}':"
                f"fontsize={safe_font_size}:"     
                f"fontcolor={font_color}:"
                f"x={safe_x}:"                    
                f"y={safe_y}:"                    
                f"alpha={opacity}"
            )
        else:
            drawtext_filter = (
                f"drawtext="
                f"text='{escaped_text}':"
                f"fontsize={safe_font_size}:"     
                f"fontcolor={font_color}:"
                f"x={safe_x}:"                    
                f"y={safe_y}:"                    
                f"alpha={opacity}"
            )
        
        return drawtext_filter
        
    except Exception as e:
        print(f"Error building source text filter: {e}")
        return ""

def add_source_text_to_video(
    input_video_path: str,
    output_video_path: str,
    source_text: str,
    position_x: int = 50,
    position_y: int = 50,
    font_size: int = 14,
    font_color: str = "white",
    ffmpeg_executable: str = None
) -> Tuple[bool, str]:
    """
    Add source text overlay to video using FFmpeg
    
    Args:
        input_video_path (str): Path to input video
        output_video_path (str): Path to output video
        source_text (str): Text to overlay
        position_x (int): X position
        position_y (int): Y position
        font_size (int): Font size
        font_color (str): Font color
        ffmpeg_executable (str): Path to FFmpeg executable
        
    Returns:
        Tuple[bool, str]: (Success status, Log output)
    """
    try:
        # Validate inputs
        if not os.path.exists(input_video_path):
            return False, f"Input video not found: {input_video_path}"
        
        if not source_text or not source_text.strip():
            return False, "Source text is empty"
        
        # Set FFmpeg path
        if not ffmpeg_executable:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ffmpeg_executable = os.path.join(current_dir, "ffmpeg", "bin", "ffmpeg.exe")
        
        if not os.path.exists(ffmpeg_executable):
            return False, f"FFmpeg not found: {ffmpeg_executable}"
        
        # Build drawtext filter
        drawtext_filter = build_source_text_filter(
            source_text=source_text.strip(),
            position_x=position_x,
            position_y=position_y,
            font_size=font_size,
            font_color=font_color
        )
        
        if not drawtext_filter:
            return False, "Failed to build drawtext filter"
        
        # Build FFmpeg command
        cmd = [
            ffmpeg_executable,
            "-i", input_video_path,
            "-vf", drawtext_filter,
            "-c:a", "copy",  # Copy audio without re-encoding
            "-c:v", "libx264",  # Video codec
            "-preset", "fast",  # Encoding speed
            "-crf", "23",  # Quality
            "-y",  # Overwrite output file
            output_video_path
        ]
        
        print(f"Running FFmpeg command for source text overlay...")
        print(f"Source text: {source_text} (25% opacity)")
        print(f"Position: ({position_x}, {position_y})")
        print(f"Font size: {font_size}px")
        
        # Execute FFmpeg
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600,  # 10 minutes timeout
            encoding='utf-8', 
            errors='ignore'
        )
        
        # Check result
        if result.returncode == 0:
            if os.path.exists(output_video_path):
                file_size = os.path.getsize(output_video_path)
                if file_size > 1000:  # At least 1KB
                    return True, f"Source text added successfully. Output size: {file_size} bytes"
                else:
                    return False, "Output file is too small, likely corrupted"
            else:
                return False, "Output file was not created"
        else:
            error_msg = f"FFmpeg failed with return code {result.returncode}"
            if result.stderr:
                error_msg += f"\nStderr: {result.stderr[-500:]}"  # Last 500 chars
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, "FFmpeg process timed out after 10 minutes"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def process_source_text_batch(
    video_files: list,
    output_dir: str,
    source_mode: str = "custom",  # "custom" or "filename"
    custom_source_text: str = "",
    position_x: int = 50,
    position_y: int = 50,
    font_size: int = 14,
    font_color: str = "white",
    ffmpeg_executable: str = None,
    log_callback=None,
    original_filenames: List[str] = None  # 🔥 NEW: Original filenames for extraction
) -> list:
    """
    Process multiple videos with source text overlay
    
    Args:
        video_files (list): List of processed video file paths
        output_dir (str): Output directory
        source_mode (str): "custom" or "filename"
        custom_source_text (str): Custom source text (used if mode is "custom")
        position_x (int): X position
        position_y (int): Y position
        font_size (int): Font size
        font_color (str): Font color
        ffmpeg_executable (str): Path to FFmpeg
        log_callback (function): Callback function for logging
        original_filenames (List[str]): 🔥 NEW: Original filenames for source extraction
        
    Returns:
        list: List of successful output files
    """
    def log(level, message):
        if log_callback:
            log_callback(level, message)
        else:
            print(f"[{level}] {message}")
    
    successful_files = []
    
    try:
        log("INFO", f"🔄 Starting source text batch processing for {len(video_files)} files")
        log("INFO", f"📋 Mode: {source_mode}")
        log("INFO", f"📍 Position: ({position_x}, {position_y})")
        log("INFO", f"🔤 Font: {font_size}px, opacity: 25%")
        
        # Validate output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            log("INFO", f"📁 Created output directory: {output_dir}")
        
        # 🔥 FIXED: Validate original_filenames for filename mode
        if source_mode == "filename" and not original_filenames:
            log("ERROR", "❌ Original filenames required for filename extraction mode")
            return successful_files
        
        for idx, video_file in enumerate(video_files, 1):
            try:
                base_name = os.path.basename(video_file)
                name_without_ext = os.path.splitext(base_name)[0]
                file_ext = os.path.splitext(base_name)[1]
                
                log("INFO", f"📎 Processing {idx}/{len(video_files)}: {base_name}")
                
                # 🔥 FIXED: Determine source text based on mode
                if source_mode == "filename":
                    # Use original filename for extraction
                    if original_filenames and idx <= len(original_filenames):
                        original_filename = os.path.basename(original_filenames[idx - 1])
                        source_text = extract_source_from_filename(original_filename)
                        log("INFO", f"🔍 Extracting from original: {original_filename}")
                    else:
                        log("ERROR", f"❌ No original filename available for index {idx}")
                        continue
                        
                    if not source_text:
                        log("WARNING", f"⚠️ No source text found in original filename: {original_filename}")
                        continue
                    log("SUCCESS", f"✅ Extracted source text: '{source_text}'")
                else:  # custom mode
                    source_text = custom_source_text
                    if not source_text or not source_text.strip():
                        log("WARNING", f"⚠️ Custom source text is empty, skipping: {base_name}")
                        continue
                    log("INFO", f"📝 Using custom text: '{source_text}'")
                
                # Generate output path
                output_path = os.path.join(output_dir, f"{name_without_ext}_with_source{file_ext}")
                
                # Process video
                success, message = add_source_text_to_video(
                    input_video_path=video_file,
                    output_video_path=output_path,
                    source_text=source_text,
                    position_x=position_x,
                    position_y=position_y,
                    font_size=font_size,
                    font_color=font_color,
                    ffmpeg_executable=ffmpeg_executable
                )
                
                if success:
                    successful_files.append(output_path)
                    log("SUCCESS", f"✅ Source text added successfully: {base_name}")
                else:
                    log("ERROR", f"❌ Failed to add source text to {base_name}: {message}")
                    
            except Exception as e:
                log("ERROR", f"❌ Error processing {base_name}: {str(e)}")
                continue
        
        log("SUCCESS", f"🎉 Source text batch processing complete. Successful: {len(successful_files)}/{len(video_files)}")
        return successful_files
        
    except Exception as e:
        log("ERROR", f"❌ Batch processing error: {str(e)}")
        return successful_files