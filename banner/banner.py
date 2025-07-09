# File: banner/banner.py

import subprocess
import os

def add_video_banner(
    main_video_path: str,
    banner_video_path: str,
    output_path: str,
    position_x: int,
    position_y: int,
    banner_width: int,
    banner_height: int,
    chroma_color: str = "0x00ff00",
    similarity: float = 0.2,
    blend: float = 0.2,
    start_time: int = 0,
    end_time: int = 9999,
    ffmpeg_executable: str = "ffmpeg"
) -> tuple[bool, str]:
    """
    🔥 FIXED: Overlays a banner video with proper path handling and loop support
    """
    if not os.path.exists(ffmpeg_executable):
        return False, f"FFmpeg not found at {ffmpeg_executable}"

    # Validate inputs
    if not os.path.exists(main_video_path):
        return False, f"Main video not found: {main_video_path}"
    
    if not os.path.exists(banner_video_path):
        return False, f"Banner video not found: {banner_video_path}"

    display_duration = end_time - start_time
    if display_duration <= 0:
        return False, f"Invalid time range: start={start_time}, end={end_time}"

    # 🔥 FIXED: Sử dụng 2-input method thay vì movie filter
    # Tính toán thời gian hiển thị
    display_duration = end_time - start_time
    
    # Build filter complex với proper loop handling
    filter_parts = []
    
    # 1. Scale banner với loop support
    filter_parts.append(f"[1:v]scale={banner_width}:{banner_height}[banner_scaled]")
    
    # 2. Chromakey processing (nếu cần)
    if chroma_color != "none":
        filter_parts.append(f"[banner_scaled]chromakey=color={chroma_color}:similarity={similarity}:blend={blend}[banner_chroma]")
        banner_stream = "[banner_chroma]"
    else:
        banner_stream = "[banner_scaled]"
    
    # 3. Overlay với timing
    filter_parts.append(f"[0:v]{banner_stream}overlay=x={position_x}:y={position_y}:enable='between(t,{start_time},{end_time})'")
    
    # Kết hợp filter
    filter_complex = ";".join(filter_parts)

    # 🔥 FIXED: FFmpeg command với stream_loop để tránh banner đứng hình
    command = [
        ffmpeg_executable,
        "-y",  # Overwrite output
        "-i", main_video_path,
        "-stream_loop", "-1",  # 🔥 Loop banner video vô hạn
        "-i", banner_video_path,
        "-filter_complex", filter_complex,
        "-c:a", "copy",  # Copy audio
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-avoid_negative_ts", "make_zero",  # 🔥 Fix timing issues
        "-shortest",  # 🔥 Limit total output duration
        output_path
    ]
    
    try:
        print("🚀 Executing FFmpeg Command (FIXED):")
        print(" ".join(command))

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300  # 5 minute timeout
        )

        if process.returncode == 0:
            return True, "Banner processing successful with fixed method."
        else:
            error_message = f"FFmpeg Error (code {process.returncode}):\nSTDERR:\n{process.stderr}\nSTDOUT:\n{process.stdout}"
            return False, error_message

    except subprocess.TimeoutExpired:
        return False, "FFmpeg process timed out after 5 minutes"
    except Exception as e:
        return False, f"Exception occurred: {str(e)}"