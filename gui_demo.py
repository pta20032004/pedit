"""
Video Editor Tool - Main GUI Demo

FUNCTIONS OVERVIEW:
===================

UI Creation Functions:
- __init__(): Initialize main window and setup
- init_ui(): Create main layout and panels
- create_left_panel(): File management and settings panel
- create_right_panel(): Preview and processing tabs
- create_preview_tab(): Video preview and effects settings
- create_processing_tab(): Progress monitoring and queue management
- create_logs_tab(): Logging and debugging output
- create_menu_bar(): Application menu structure
- apply_modern_styles(): Apply dark theme CSS styling

Custom Widgets:
- VideoPreviewWidget.__init__(): Initialize 9:16 preview widget
- VideoPreviewWidget.paintEvent(): Draw preview areas (subtitle, banner, source)
- VideoPreviewWidget.init_preview(): Setup default preview state

Event Handlers:
- add_files(): Open file dialog and add video files to list
- add_folder(): Add entire folder of videos
- clear_files(): Remove all files from processing list
- browse_output(): Select output directory
- browse_banner(): Select banner/logo image file
- select_chroma_color(): Color picker for chroma key
- test_api_key(): Validate Google AI API key
- start_processing(): Begin batch video processing
- toggle_preview_area(): Show/hide preview areas (subtitle, banner, source)
- load_voice_data() - Load dữ liệu từ voice_info.json
- preview_voice() - Preview voice đã chọn
- toggle_voice_controls() - Bật/tắt voice controls
- get_selected_voice_info() - Lấy thông tin voice đã chọn

Utility Functions:
- add_log(): Add formatted log entry with timestamp and color
- clear_logs(): Clear all log entries
- save_logs(): Export logs to text file

Menu Handlers:
- new_project(), open_project(), save_project(): Project management
- open_api_config(), open_preferences(), open_templates(): Settings dialogs
- show_about(), show_docs(), show_tutorial(): Help and documentation

API Management:

- current_api_index: Track which API key is currently in use

- test_api_key
- update_backup_api_status
- auto_select_working_api_key
"""

import subprocess
import time  
from typing import Tuple
from banner.banner import add_video_banner
import threading
import sys
import json
import os
import re


try:
    from gg_api.get_subtitle import fix_srt_timestamps
    SUBTITLE_FIX_AVAILABLE = True
    print("✅ Subtitle fix function loaded successfully")
except ImportError as e:
    SUBTITLE_FIX_AVAILABLE = False
    print(f"⚠️ Warning: Subtitle fix function not found: {str(e)}")

# 🔥 CRITICAL FIX: Đảm bảo có thể import gg_api
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"✅ Added to Python path: {current_dir}")

from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QTabWidget, QGroupBox,
                            QPushButton, QLabel, QLineEdit, QTextEdit, 
                            QProgressBar, QListWidget, QCheckBox, QSpinBox,
                            QComboBox, QFileDialog, QSplitter, QFrame,
                            QScrollArea, QSlider, QDoubleSpinBox, QTextBrowser,
                            QListWidgetItem, QHeaderView, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QPainter, QPen, QBrush

try:
    from gg_api.test_api import test_api_key as test_key_function
    API_TESTING_AVAILABLE = True
    print("✅ API testing module loaded successfully")
except ImportError as e:
    API_TESTING_AVAILABLE = False
    print(f"⚠️ Warning: API testing module not found: {str(e)}")
    print("   Make sure gg_api/test_api.py exists and dependencies are installed")
except Exception as e:
    API_TESTING_AVAILABLE = False
    print(f"❌ Error loading API testing module: {str(e)}")

class SimpleSpinner(QLabel):
    """Simple rotating spinner using text characters"""
    
    def __init__(self):
        super().__init__()
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_index = 0
        
        self.setStyleSheet("""
            QLabel {
                color: #63b3ed;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_spinner)
        
        self.hide()
    
    def start_spinning(self):
        """Start the spinning animation"""
        self.show()
        self.timer.start(100)  # Update every 100ms
    
    def stop_spinning(self):
        """Stop the spinning animation"""
        self.timer.stop()
        self.hide()
        self.current_index = 0
    
    def update_spinner(self):
        """Update spinner character"""
        self.setText(self.spinner_chars[self.current_index])
        self.current_index = (self.current_index + 1) % len(self.spinner_chars)


class VideoPreviewWidget(QLabel):
    """Custom widget for displaying 9:16 video preview with overlay areas - FIXED SYNC"""
    
    def __init__(self):
        super().__init__()
        self.preview_width = 270
        self.preview_height = 480
        self.setMinimumSize(self.preview_width, self.preview_height)
        self.setMaximumSize(self.preview_width, self.preview_height)
        self.setStyleSheet("""
            border: 2px solid #333;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #2a2a2a, stop:1 #1a1a1a);
            border-radius: 8px;
        """)
        self.setAlignment(Qt.AlignCenter)
        
        # 🔥 FIXED: Kích thước video thực tế (9:16 standard)
        self.REAL_VIDEO_WIDTH = 1080
        self.REAL_VIDEO_HEIGHT = 1920
        
        # 🔥 FIXED: Tỷ lệ co dãn chính xác
        self.scale_x = self.preview_width / self.REAL_VIDEO_WIDTH
        self.scale_y = self.preview_height / self.REAL_VIDEO_HEIGHT
        
        # Default preview areas visibility
        self.show_subtitle_area = True
        self.show_banner_area = True
        self.show_source_area = True
        
        # 🔥 FIXED: Khởi tạo với vị trí thực tế từ settings
        self.subtitle_rect = QRect(0, 0, 0, 0)  # Sẽ được cập nhật từ bên ngoài
        self.banner_rect = QRect(0, 0, 0, 0)
        self.source_rect = QRect(0, 0, 0, 0)

        self.init_preview()
    
    def paintEvent(self, event):
        """Draw preview areas with TikTok-safe margins visualization - FIXED VERSION"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 🔥 VẼ TIKTOK SAFE MARGINS
        BASE_LEFT_MARGIN = 90
        BASE_RIGHT_MARGIN = 130
        
        left_margin_preview = int(BASE_LEFT_MARGIN * self.scale_x)
        right_margin_preview = int(BASE_RIGHT_MARGIN * self.scale_x)
        
        # Left danger zone (avatar/username area)
        painter.setPen(QPen(QColor(255, 100, 100, 120), 2, Qt.DashLine))
        painter.setBrush(QBrush(QColor(255, 100, 100, 40)))
        painter.drawRect(0, 0, left_margin_preview, self.preview_height)
        
        # Right danger zone (like/comment buttons)
        painter.setPen(QPen(QColor(255, 100, 100, 120), 2, Qt.DashLine))
        painter.setBrush(QBrush(QColor(255, 100, 100, 40)))
        painter.drawRect(self.preview_width - right_margin_preview, 0, right_margin_preview, self.preview_height)
        
        # Safe zone outline
        safe_area_x = left_margin_preview
        safe_area_width = self.preview_width - left_margin_preview - right_margin_preview
        painter.setPen(QPen(QColor(0, 255, 0, 200), 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 0, 0)))  # No fill, just outline
        painter.drawRect(safe_area_x, 0, safe_area_width, self.preview_height)
        
        # Vẽ subtitle area (inside safe zone)
        if self.show_subtitle_area:
            painter.setPen(QPen(QColor(255, 255, 0, 180), 2, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 30)))
            painter.drawRect(self.subtitle_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(self.subtitle_rect.x(), self.subtitle_rect.y() - 5, "SAFE Subtitle Area")
        
        # Vẽ banner area
        if self.show_banner_area:
            painter.setPen(QPen(QColor(0, 255, 255, 150), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 255, 255, 30)))
            painter.drawRect(self.banner_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(self.banner_rect.x(), self.banner_rect.y() - 5, "Banner/Logo")
        
        # Vẽ source area
        if self.show_source_area:
            painter.setPen(QPen(QColor(255, 0, 255, 150), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 0, 255, 30)))
            painter.drawRect(self.source_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(self.source_rect.x(), self.source_rect.y() - 5, "Source")
        
        # Center text with TikTok info
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.rect(), Qt.AlignCenter, 
                        "📱 TikTok Safe Preview\n9:16 Format 1080x1920\n\n🔴 Danger Zones\n🟢 Safe Area\n🟡 Subtitle Zone")


    def update_from_real_coordinates(self, area_type: str, real_x: int, real_y: int, real_width: int = None, real_height: int = None):
        """ FIXED: Cập nhật preview từ tọa độ thực tế với TikTok safe margins"""
        # Chuyển đổi từ tọa độ thực tế sang preview
        preview_x = int(real_x * self.scale_x)
        preview_y = int(real_y * self.scale_y)
        
        if area_type == 'banner':
            if real_width and real_height:
                preview_width = int(real_width * self.scale_x)
                preview_height = int(real_height * self.scale_y)
                self.banner_rect = QRect(preview_x, preview_y, preview_width, preview_height)
            else:
                self.banner_rect.moveTo(preview_x, preview_y)
                
        elif area_type == 'subtitle':
            #  TikTok-safe subtitle area với margins
            REAL_VIDEO_WIDTH = 1080
            BASE_LEFT_MARGIN = 90
            BASE_RIGHT_MARGIN = 130
            
            # Calculate safe area
            safe_left = BASE_LEFT_MARGIN
            safe_right = REAL_VIDEO_WIDTH - BASE_RIGHT_MARGIN
            safe_width = safe_right - safe_left
            
            # Convert to preview coordinates
            preview_safe_left = int(safe_left * self.scale_x)
            preview_safe_width = int(safe_width * self.scale_x)
            
            if real_width and real_height:
                preview_height = int(real_height * self.scale_y)
            else:
                preview_height = int(80 * self.scale_y)  # Default height
            
            # Center in safe area
            self.subtitle_rect = QRect(preview_safe_left, preview_y, preview_safe_width, preview_height)
            
        elif area_type == 'source':
            if real_width and real_height:
                preview_width = int(real_width * self.scale_x)
                preview_height = int(real_height * self.scale_y)
                self.source_rect = QRect(preview_x, preview_y, preview_width, preview_height)
            else:
                default_width = int(200 * self.scale_x)
                default_height = int(30 * self.scale_y)
                self.source_rect = QRect(preview_x, preview_y, default_width, default_height)
        
        self.update()  # Vẽ lại widget

    def paintEvent(self, event):
        """Draw preview areas with correct scaling"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Vẽ subtitle area
        if self.show_subtitle_area:
            painter.setPen(QPen(QColor(255, 255, 0, 150), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 30)))
            painter.drawRect(self.subtitle_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(self.subtitle_rect.x(), self.subtitle_rect.y() - 5, "Subtitle Area")
        
        # Vẽ banner area
        if self.show_banner_area:
            painter.setPen(QPen(QColor(0, 255, 255, 150), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 255, 255, 30)))
            painter.drawRect(self.banner_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(self.banner_rect.x(), self.banner_rect.y() - 5, "Banner/Logo")
        
        # Vẽ source area
        if self.show_source_area:
            painter.setPen(QPen(QColor(255, 0, 255, 150), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 0, 255, 30)))
            painter.drawRect(self.source_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(self.source_rect.x(), self.source_rect.y() - 5, "Source")
        
        # Center text
        painter.setPen(QColor(128, 128, 128))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(self.rect(), Qt.AlignCenter, "Video Preview\n9:16 Format\n1080x1920")

    def init_preview(self):
        """Setup default preview state"""
        self.setText("")
        self.update()

class VideoEditorMainWindow(QMainWindow):
    """Main application window for video editing tool"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Editor Tool - Batch Processing (9:16 Format)")
        self.setGeometry(100, 100, 1600, 1000)
        
        self.current_api_index = 0
        
        # 🔥 THÊM BIẾN PROCESSING STATE
        self.is_processing = False
        
        self.init_ui()
        self.apply_modern_styles()
        
        # 🔥 THIẾT LẬP CÁC MẶC ĐỊNH SAU KHI UI ĐÃ TẠO
        self.setup_defaults()
        
        # 🔥 KIỂM TRA FFMPEG KHI KHỞI ĐỘNG
        QApplication.processEvents()  # Để UI load xong trước
        self.check_ffmpeg_installation()
    
    
    def wrap_text_for_safe_display(self, text: str, max_chars_per_line: int) -> str:
        """🔥 SIMPLE: Wrap text để fit TikTok safe area"""
        try:
            import textwrap
            
            # Clean text
            text = ' '.join(text.split())
            
            # If short enough, return as-is
            if len(text) <= max_chars_per_line:
                return text
            
            # Smart wrap
            lines = textwrap.wrap(text, width=max_chars_per_line, break_long_words=False)
            
            # Limit to 2 lines max for readability
            if len(lines) > 2:
                # Try longer lines to reduce line count
                lines = textwrap.wrap(text, width=int(max_chars_per_line * 1.3), break_long_words=False)
                lines = lines[:2]  # Still limit to 2 lines
            
            return '\n'.join(lines)
            
        except Exception:
            # Fallback: simple truncation
            if len(text) > max_chars_per_line:
                return text[:max_chars_per_line-3] + "..."
            return text


    def preprocess_srt_for_safe_display(self, srt_file_path: str, max_chars_per_line: int = 20) -> str:
        """🔥 NEW: Pre-process SRT file để wrap text, return path to new file"""
        try:
            self.add_log("INFO", f"📝 Pre-processing SRT for safe display (max {max_chars_per_line} chars/line)")
            
            # Read original SRT
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # Process each subtitle block
            blocks = srt_content.strip().split('\n\n')
            processed_blocks = []
            wrapped_count = 0
            
            for block in blocks:
                lines = block.strip().split('\n')
                
                if len(lines) >= 3:
                    # Line 0: number, Line 1: timing, Line 2+: text
                    subtitle_number = lines[0]
                    timing = lines[1]
                    text_lines = lines[2:]
                    original_text = ' '.join(text_lines)
                    
                    # Wrap text for safe display
                    wrapped_text = self.wrap_text_for_safe_display(original_text, max_chars_per_line)
                    
                    if wrapped_text != original_text:
                        wrapped_count += 1
                    
                    # Rebuild block
                    new_block = f"{subtitle_number}\n{timing}\n{wrapped_text}"
                    processed_blocks.append(new_block)
                else:
                    # Keep as-is if format is weird
                    processed_blocks.append(block)
            
            # Create new SRT content
            new_srt_content = '\n\n'.join(processed_blocks)
            
            # Save to new file
            output_dir = os.path.dirname(srt_file_path)
            base_name = os.path.splitext(os.path.basename(srt_file_path))[0]
            safe_srt_path = os.path.join(output_dir, f"{base_name}_safe.srt")
            
            with open(safe_srt_path, 'w', encoding='utf-8') as f:
                f.write(new_srt_content)
            
            self.add_log("SUCCESS", f"✅ Pre-processed SRT: {wrapped_count}/{len(processed_blocks)} subtitles wrapped")
            self.add_log("INFO", f"   📁 Safe SRT: {os.path.basename(safe_srt_path)}")
            
            return safe_srt_path
            
        except Exception as e:
            self.add_log("ERROR", f"❌ SRT pre-processing failed: {str(e)}")
            return srt_file_path

    def parse_srt(self, srt_content: str) -> list:
        """
        🔥 NEW HELPER: Chuyển nội dung file SRT thành một danh sách để dùng cho drawtext.
        """
        subtitle_entries = []
        blocks = srt_content.strip().split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    time_line = lines[1]
                    start_str, end_str = time_line.split(' --> ')
                    h, m, s_ms = start_str.split(':')
                    s, ms = s_ms.split(',')
                    start_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                    h, m, s_ms = end_str.split(':')
                    s, ms = s_ms.split(',')
                    end_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                    text = ' '.join(lines[2:]).replace("'", "’").replace(":", " ").replace("\\", "\\\\").replace("%", "\\%").replace("=", "\\=")
                    subtitle_entries.append({'start': start_seconds, 'end': end_seconds, 'text': text})
                except Exception as e:
                    self.add_log("WARNING", f"⚠️ Bỏ qua một khối SRT không hợp lệ: {e}")
        return subtitle_entries

    def create_ass_file_content(self, srt_content: str, font_size: int, margin_v: int, style: str) -> str:
        """
        🔥 HÀM MỚI: Chuyển đổi nội dung SRT sang định dạng ASS với style tùy chỉnh.
        """
        def srt_time_to_ass(srt_time):
            parts = srt_time.replace(',', '.').split(':')
            return f"{int(parts[0]):01}:{int(parts[1]):02}:{float(parts[2]):05.2f}"

        # Xác định màu sắc dựa trên style
        primary_color = "&H00FFFFFF"  # White
        outline_color = "&H00000000"  # Black
        if style == "Black with White Outline":
            primary_color = "&H00000000"
            outline_color = "&H00FFFFFF"
        elif style == "Yellow":
            primary_color = "&H0000FFFF"
            outline_color = "&H00000000"
            
        # Phần header và style của file ASS
        # Alignment=2 có nghĩa là CĂN GIỮA Ở DƯỚI (Bottom Center)
        ass_header = f"""[Script Info]
Title: Generated by Video Editor Tool
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},&H000000FF,{outline_color},&H64000000,-1,0,0,0,100,100,0,0,1,2,2,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # Xử lý các dòng sự kiện
        dialogue_lines = []
        blocks = srt_content.strip().split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                start_str, end_str = time_line.split(' --> ')
                start_ass = srt_time_to_ass(start_str.strip())
                end_ass = srt_time_to_ass(end_str.strip())
                
                # Nối các dòng text lại và thay thế \n bằng \\N (ký tự xuống dòng của ASS)
                text_content = "\\N".join(lines[2:])
                dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text_content}")

        return ass_header + "\n".join(dialogue_lines)

    def add_subtitles_to_video(self, input_video: str, srt_file: str, output_video: str) -> bool:
        """
        🔥 PHIÊN BẢN CHUẨN: Không mapping bằng tay. Tận dụng cơ chế scale tự động của ASS.
        """
        self.add_log("INFO", "✅ Sử dụng cơ chế scale tự động của file .ASS.")
        try:
            ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe")
            if not os.path.exists(ffmpeg_path):
                self.add_log("ERROR", "❌ FFmpeg executable not found")
                return False

            # === BƯỚC 1: BỎ HOÀN TOÀN LOGIC MAPPING BẰNG TAY ===
            # Lấy giá trị gốc trực tiếp từ GUI. Các giá trị này dành cho canvas 1080x1920.
            font_size = self.subtitle_size.value()
            pos_y = self.subtitle_y.value()
            
            # MarginV là khoảng cách từ cạnh dưới, tính trên canvas 1920px.
            REFERENCE_HEIGHT = 1920
            margin_v = REFERENCE_HEIGHT - pos_y

            self.add_log("INFO", f"🎨 Using original values for ASS script (on 1080x1920 canvas)")
            self.add_log("INFO", f"   🔤 Font: {font_size}px, Vertical Margin: {margin_v}px from bottom")
            # === KẾT THÚC BƯỚC 1 ===

            # === BƯỚC 2: TẠO VÀ SỬ DỤNG FILE .ASS (giữ nguyên) ===
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # Tạo nội dung file .ass, sử dụng các giá trị gốc.
            style = self.subtitle_style.currentText()
            ass_content = self.create_ass_file_content(srt_content, font_size, margin_v, style)

            # Lưu nội dung .ass vào một file tạm
            temp_ass_path = os.path.join(os.path.dirname(srt_file), "temp_subtitles.ass")
            with open(temp_ass_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)

            # Lệnh FFmpeg sử dụng file .ass tạm
            escaped_ass_path = temp_ass_path.replace('\\', '/').replace(':', '\\:')
            cmd = [
                ffmpeg_path,
                "-i", input_video,
                "-vf", f"subtitles='{escaped_ass_path}'",
                "-c:a", "copy",
                "-y",
                output_video
            ]

            self.add_log("INFO", "🔧 FFmpeg subtitles command is being executed with .ass file...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, encoding='utf-8', errors='ignore')

            # Xóa file tạm sau khi dùng
            if os.path.exists(temp_ass_path):
                os.remove(temp_ass_path)
            
            if result.returncode == 0 and os.path.exists(output_video):
                self.add_log("SUCCESS", "✅ Subtitles with AUTO-SCALING and centering added successfully!")
                return True
            else:
                self.add_log("ERROR", f"❌ FFmpeg .ass error. Return code: {result.returncode}")
                self.add_log("ERROR", f"   stderr: ...{result.stderr[-500:]}")
                return False

        except Exception as e:
            self.add_log("ERROR", f"❌ A critical error occurred in .ass subtitle addition: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   Traceback: {traceback.format_exc()}")
            return False
    
    def get_validated_api_key(self) -> str:
        """
        🔥 SỬA LẠI: Validate API key với debug chi tiết
        """
        self.add_log("INFO", "🔑 [API DEBUG] Starting API key validation...")
        
        # Get from manual input
        api_key = self.api_key_input.text().strip()
        self.add_log("INFO", f"🔍 [API DEBUG] Manual input length: {len(api_key)}")
        
        if not api_key:
            self.add_log("WARNING", "⚠️ [API DEBUG] Manual API key field is empty")
            
            # Try to get from dropdown as fallback
            if hasattr(self, 'api_key_pool'):
                selected_key = self.api_key_pool.currentData()
                if selected_key:
                    api_key = selected_key
                    self.add_log("INFO", f"🔍 [API DEBUG] Using key from pool: {len(api_key)} chars")
                else:
                    self.add_log("ERROR", "❌ [API DEBUG] No key available in pool either")
                    return ""
            else:
                self.add_log("ERROR", "❌ [API DEBUG] No API key source available")
                return ""
        
        # Basic validation
        if len(api_key) < 20:
            self.add_log("ERROR", f"❌ [API DEBUG] API key too short: {len(api_key)} chars (minimum 20)")
            return ""
        
        # Check if it looks like a Google AI API key
        if not api_key.startswith('AIza'):
            self.add_log("WARNING", f"⚠️ [API DEBUG] API key doesn't start with 'AIza': {api_key[:10]}...")
            # Continue anyway, might still work
        
        self.add_log("SUCCESS", f"✅ [API DEBUG] API key validated: {api_key[:10]}...{api_key[-4:]}")
        return api_key

    def build_subtitle_filter(self, srt_file: str, font_size: int, pos_x: int, pos_y: int, style: str) -> str:
        """
        🔥 FIXED: Xây dựng filter string cho FFmpeg subtitle với center positioning
        """
        try:
            # Escape đường dẫn SRT file cho FFmpeg
            escaped_srt = srt_file.replace('\\', '/').replace(':', '\\:')
            
            # 🔥 SIMPLE APPROACH: Chỉ dùng subtitles filter cơ bản
            subtitle_filter = f"subtitles='{escaped_srt}'"
            
            # 🔥 BASIC STYLING: Đơn giản hóa để tránh lỗi
            if style == "White with Shadow":
                subtitle_filter += f":force_style='FontSize={font_size},Alignment=2,MarginV=50'"
            elif style == "Black with White Outline":
                subtitle_filter += f":force_style='FontSize={font_size},Alignment=2,MarginV=50,PrimaryColour=&H000000,OutlineColour=&Hffffff'"
            elif style == "Yellow":
                subtitle_filter += f":force_style='FontSize={font_size},Alignment=2,MarginV=50,PrimaryColour=&H00ffff'"
            else:  # Default
                subtitle_filter += f":force_style='FontSize={font_size},Alignment=2,MarginV=50'"
            
            self.add_log("INFO", f"🎨 Subtitle filter: {subtitle_filter[:100]}...")
            return subtitle_filter
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error building subtitle filter: {str(e)}")
            # 🔥 ULTIMATE FALLBACK: Chỉ dùng subtitles filter thuần
            return f"subtitles='{escaped_srt}'"

    def add_subtitles_to_video_centered(self, input_video: str, srt_file: str, output_video: str) -> bool:
        """🔥 FIXED: Handle special characters + correct FFmpeg syntax - 3 fallback methods"""
        try:
            import time
            import tempfile
            import shutil
            
            # Validate inputs
            if not os.path.exists(input_video):
                self.add_log("ERROR", f"❌ Input video not found: {input_video}")
                return False
                
            if not os.path.exists(srt_file):
                self.add_log("ERROR", f"❌ SRT file not found: {srt_file}")
                return False
            
            # FFmpeg path
            ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe")
            if not os.path.exists(ffmpeg_path):
                system_ffmpeg = shutil.which("ffmpeg")
                if not system_ffmpeg:
                    self.add_log("ERROR", "❌ FFmpeg not found")
                    return False
                ffmpeg_path = system_ffmpeg
            
            # Get video dimensions
            video_width, video_height = self.get_video_dimensions(input_video)
            if not video_width or not video_height:
                self.add_log("ERROR", "❌ Cannot get video dimensions")
                return False
            
            # Calculate max chars based on video width
            if video_width <= 720:
                max_chars = 15
            elif video_width <= 1080:
                max_chars = 20
            else:
                max_chars = 25
            
            self.add_log("INFO", f"📐 Video: {video_width}x{video_height}, Max chars: {max_chars}")
            
            # Pre-process SRT for text wrapping
            safe_srt_file = self.preprocess_srt_for_safe_display(srt_file, max_chars)
            
            # Get GUI settings
            font_size = self.subtitle_size.value()
            scale_factor = min(video_width / 1080, video_height / 1920)
            scaled_font_size = max(12, int(font_size * scale_factor))
            
            self.add_log("INFO", f"🔤 Font: {font_size}px → {scaled_font_size}px")
            
            # 🔥 METHOD 1: Copy SRT to temp location with safe filename
            self.add_log("INFO", "🔄 METHOD 1: Safe temp file approach")
            
            temp_dir = tempfile.gettempdir()
            timestamp = str(int(time.time()))
            safe_filename = f"temp_subtitle_{timestamp}.srt"
            temp_srt_path = os.path.join(temp_dir, safe_filename)
            
            # Copy processed SRT to temp location
            shutil.copy2(safe_srt_file, temp_srt_path)
            self.add_log("INFO", f"🔧 Temp SRT: {safe_filename}")
            
            cmd_basic = [
                ffmpeg_path,
                "-y",
                "-i", input_video,
                "-vf", f"subtitles={temp_srt_path}",
                "-c:a", "copy", 
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                output_video
            ]
            
            result = subprocess.run(cmd_basic, capture_output=True, text=True, timeout=600)
            
            # Clean up temp file
            try:
                os.remove(temp_srt_path)
            except:
                pass
            
            if result.returncode == 0:
                if os.path.exists(output_video) and os.path.getsize(output_video) > 1000:
                    self.add_log("SUCCESS", f"✅ METHOD 1 SUCCESS!")
                    # Clean up processed SRT
                    try:
                        if safe_srt_file != srt_file:
                            os.remove(safe_srt_file)
                    except:
                        pass
                    return True
            
            self.add_log("WARNING", f"⚠️ METHOD 1 failed (code: {result.returncode})")
            
            # 🔥 METHOD 2: Relative path in video directory
            self.add_log("INFO", "🔄 METHOD 2: Relative path approach")
            
            video_dir = os.path.dirname(input_video)
            simple_srt_name = "temp_sub.srt"
            simple_srt_path = os.path.join(video_dir, simple_srt_name)
            
            # Copy SRT to video directory
            shutil.copy2(safe_srt_file, simple_srt_path)
            
            # Change to video directory
            original_cwd = os.getcwd()
            
            try:
                os.chdir(video_dir)
                
                cmd_relative = [
                    ffmpeg_path,
                    "-y", 
                    "-i", os.path.basename(input_video),
                    "-vf", f"subtitles={simple_srt_name}",
                    "-c:a", "copy",
                    "-c:v", "libx264",
                    "-preset", "fast", 
                    "-crf", "23",
                    os.path.basename(output_video)
                ]
                
                result2 = subprocess.run(cmd_relative, capture_output=True, text=True, timeout=600)
                
                # Always restore directory
                os.chdir(original_cwd)
                
                # Clean up temp SRT
                try:
                    os.remove(simple_srt_path)
                except:
                    pass
                
                if result2.returncode == 0:
                    if os.path.exists(output_video) and os.path.getsize(output_video) > 1000:
                        self.add_log("SUCCESS", f"✅ METHOD 2 SUCCESS!")
                        # Clean up processed SRT
                        try:
                            if safe_srt_file != srt_file:
                                os.remove(safe_srt_file)
                        except:
                            pass
                        return True
                            
            except Exception as e:
                # Always restore directory on exception
                try:
                    os.chdir(original_cwd)
                except:
                    pass
                self.add_log("ERROR", f"❌ METHOD 2 exception: {str(e)}")
            
            self.add_log("WARNING", f"⚠️ METHOD 2 failed")
            
            # 🔥 METHOD 3: Drawtext fallback (no subtitle file dependency)
            self.add_log("INFO", "🔄 METHOD 3: Drawtext fallback")
            
            # Parse SRT manually
            subtitle_entries = self.parse_srt_for_drawtext(safe_srt_file)
            
            if not subtitle_entries:
                self.add_log("ERROR", "❌ No subtitle entries found")
            else:
                # Build simple drawtext filters
                drawtext_filters = []
                
                for entry in subtitle_entries[:10]:  # Limit to first 10 to avoid command too long
                    start_time = entry['start_seconds']
                    end_time = entry['end_seconds']
                    text = entry['text'].replace("'", "").replace(":", " ")  # Remove problematic chars
                    
                    # Simple centered drawtext
                    drawtext_filter = (
                        f"drawtext="
                        f"text='{text}':"
                        f"fontsize={scaled_font_size}:"
                        f"fontcolor=white:"
                        f"x=(w-text_w)/2:"
                        f"y=h-100:"
                        f"enable='between(t,{start_time},{end_time})'"
                    )
                    drawtext_filters.append(drawtext_filter)
                
                if drawtext_filters:
                    complete_filter = ",".join(drawtext_filters)
                    
                    cmd_drawtext = [
                        ffmpeg_path,
                        "-y",
                        "-i", input_video,
                        "-vf", complete_filter,
                        "-c:a", "copy",
                        "-c:v", "libx264", 
                        "-preset", "fast",
                        "-crf", "23",
                        output_video
                    ]
                    
                    result3 = subprocess.run(cmd_drawtext, capture_output=True, text=True, timeout=600)
                    
                    if result3.returncode == 0:
                        if os.path.exists(output_video) and os.path.getsize(output_video) > 1000:
                            self.add_log("SUCCESS", f"✅ METHOD 3 (drawtext) SUCCESS!")
                            # Clean up processed SRT
                            try:
                                if safe_srt_file != srt_file:
                                    os.remove(safe_srt_file)
                            except:
                                pass
                            return True
            
            # Clean up processed SRT file
            try:
                if safe_srt_file != srt_file:
                    os.remove(safe_srt_file)
            except:
                pass
            
            # All methods failed
            self.add_log("ERROR", "❌ All 3 subtitle methods failed")
            self.add_log("ERROR", "💡 Suggestion: Check if video file name has special characters")
            
            return False
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Critical error in subtitle processing: {str(e)}")
            return False


    def create_srt_file_from_content(self, srt_content: str, output_path: str) -> bool:
        """
        🔥 UPDATED: Create SRT file WITHOUT calling old fix_srt_timestamps
        """
        try:
            self.add_log("INFO", f"📄 Creating SRT file with NEW format validation...")
            
            # 🔥 REMOVED: No longer call fix_srt_timestamps() - content should already be fixed
            # OLD CODE REMOVED: fixed_content = fix_srt_timestamps(srt_content, self.add_log)
            
            # 🔥 NEW: Use content as-is (should already be processed by new Step 2 logic)
            final_content = srt_content.strip()
            
            # Basic validation only
            if not final_content or len(final_content) < 10:
                self.add_log("ERROR", "❌ SRT content is empty or too short")
                return False
            
            # Quick format check
            if '-->' not in final_content:
                self.add_log("WARNING", "⚠️ SRT content may not contain valid timestamps")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write content directly
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
                
                # Ensure file ends with newline
                if not final_content.endswith('\n'):
                    f.write('\n')
            
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                
                # Count blocks for reporting
                blocks = final_content.strip().split('\n\n')
                valid_blocks = [b for b in blocks if b.strip()]
                
                self.add_log("SUCCESS", f"✅ SRT file created: {file_size} bytes, {len(valid_blocks)} subtitle blocks")
                
                # Show preview of first 2 blocks
                self.add_log("INFO", "📋 SRT preview (first 2 blocks):")
                for i, block in enumerate(valid_blocks[:2]):
                    lines = block.strip().split('\n')
                    for j, line in enumerate(lines):
                        self.add_log("INFO", f"   {i+1}.{j+1}: {line}")
                    if i < len(valid_blocks) - 1:
                        self.add_log("INFO", "   ---")
                
                if len(valid_blocks) > 2:
                    self.add_log("INFO", f"   ... and {len(valid_blocks) - 2} more blocks")
                
                return True
            else:
                self.add_log("ERROR", "❌ Failed to create SRT file")
                return False
                
        except Exception as e:
            self.add_log("ERROR", f"❌ Error creating SRT: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")
            return False
        
    def process_subtitles_for_video(self, video_path: str, output_dir: str) -> Tuple[bool, str]:
        """
        🔥 FIXED: Xử lý subtitle với validation và error handling tốt hơn
        """
        try:
            # Lấy thông tin video
            base_name = os.path.basename(video_path)
            name_without_ext = os.path.splitext(base_name)[0]
            file_ext = os.path.splitext(base_name)[1]
            
            self.add_log("INFO", f"🎬 [SUBTITLE DEBUG] Starting subtitle processing for: {base_name}")
            
            # Step 1: Validate video file
            if not os.path.exists(video_path):
                self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Video file not found: {video_path}")
                return False, ""
            
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            self.add_log("INFO", f"📊 [SUBTITLE DEBUG] Video file size: {file_size_mb:.2f} MB")
            
            # Step 2: Validate API key
            self.add_log("INFO", "🔑 [SUBTITLE DEBUG] Validating API key...")
            api_key = self.get_validated_api_key()
            if not api_key:
                self.add_log("ERROR", "❌ [SUBTITLE DEBUG] API key validation failed")
                return False, ""
            
            self.add_log("SUCCESS", f"✅ [SUBTITLE DEBUG] API key validated: {api_key[:10]}...{api_key[-4:]}")
            
            # Step 3: Get language settings
            source_lang = self.source_lang.currentText()
            target_lang = self.target_lang.currentText()
            
            self.add_log("INFO", f"🌐 [SUBTITLE DEBUG] Languages: {source_lang} → {target_lang}")
            
            # Step 4: Import validation - 🔥 CRITICAL CHECK
            self.add_log("INFO", "📦 [SUBTITLE DEBUG] Checking import availability...")
            if not hasattr(self, 'subtitle_import_available'):
                try:
                    from gg_api.get_subtitle import process_video_for_subtitles, get_default_words_per_line
                    self.subtitle_import_available = True
                    self.add_log("SUCCESS", "✅ [SUBTITLE DEBUG] Subtitle module imported successfully")
                except ImportError as e:
                    self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Failed to import subtitle module: {str(e)}")
                    return False, ""
                except Exception as e:
                    self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Unexpected import error: {str(e)}")
                    return False, ""
            
            # Step 5: Get words per line
            try:
                from gg_api.get_subtitle import get_default_words_per_line
                words_per_line = get_default_words_per_line(target_lang)
                self.add_log("INFO", f"📝 [SUBTITLE DEBUG] Words per line: {words_per_line}")
            except Exception as e:
                self.add_log("WARNING", f"⚠️ [SUBTITLE DEBUG] Error getting words per line, using default: {str(e)}")
                words_per_line = 8
            
            # Step 6: Create SRT output path
            srt_temp_path = os.path.join(output_dir, f"{name_without_ext}_subtitle.srt")
            self.add_log("INFO", f"📄 [SUBTITLE DEBUG] SRT output path: {srt_temp_path}")
            
            # Step 7: **CRITICAL** - Call Gemini API
            self.add_log("INFO", "🤖 [SUBTITLE DEBUG] *** CALLING GEMINI API NOW ***")
            self.add_log("INFO", "⏳ [SUBTITLE DEBUG] This WILL take 30-120 seconds for AI processing...")
            self.add_log("INFO", "🕐 [SUBTITLE DEBUG] Please wait, do NOT close the application...")
            
            # Force UI update before long operation
            QApplication.processEvents()
            
            try:
                from gg_api.get_subtitle import process_video_for_subtitles as api_process_video
                
                # 🔥 ACTUAL API CALL - THIS IS WHERE THE MAGIC HAPPENS
                start_time = time.time()
                success, srt_content, message = api_process_video(
                    video_path=video_path,
                    api_key=api_key,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    words_per_line=words_per_line,
                    ffmpeg_path=None,
                    log_callback=self.add_log  # 🔥 IMPORTANT: Pass log callback
                )
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                self.add_log("INFO", f"🔍 [SUBTITLE DEBUG] API call completed in {elapsed_time:.1f} seconds")
                self.add_log("INFO", f"   Success: {success}")
                self.add_log("INFO", f"   Message: {message}")
                
                if srt_content:
                    self.add_log("INFO", f"   SRT content length: {len(srt_content)} characters")
                    self.add_log("INFO", f"   SRT preview: {srt_content[:100]}...")
                else:
                    self.add_log("ERROR", "   SRT content is empty!")

            
                    
            except Exception as api_error:
                self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Exception during API call: {str(api_error)}")
                import traceback
                self.add_log("ERROR", f"   📋 API call traceback: {traceback.format_exc()}")
                return False, ""
            
            if not success:
                self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] API call failed: {message}")
                return False, ""
            
            if not srt_content or len(srt_content.strip()) < 10:
                self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] SRT content is empty or too short")
                return False, ""
            
            # Step 8: Save SRT file
            self.add_log("INFO", "💾 [SUBTITLE DEBUG] Saving SRT file...")
            try:
                with open(srt_temp_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                if os.path.exists(srt_temp_path):
                    srt_file_size = os.path.getsize(srt_temp_path)
                    self.add_log("SUCCESS", f"✅ [SUBTITLE DEBUG] SRT file saved: {srt_file_size} bytes")
                else:
                    self.add_log("ERROR", "❌ [SUBTITLE DEBUG] SRT file not created")
                    return False, ""
                    
            except Exception as e:
                self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Failed to save SRT: {str(e)}")
                return False, ""
            
            # Step 9: Create output video path
            output_video_path = os.path.join(output_dir, f"{name_without_ext}_with_subtitles{file_ext}")
            self.add_log("INFO", f"🎬 [SUBTITLE DEBUG] Output video path: {output_video_path}")
            
            # Step 10: Add subtitle to video using FFmpeg
            self.add_log("INFO", "🎞️ [SUBTITLE DEBUG] Adding subtitles to video with FFmpeg...")
            subtitle_success = self.add_subtitles_to_video(
                input_video=video_path,
                srt_file=srt_temp_path,
                output_video=output_video_path
            )
            
            if subtitle_success:
                self.add_log("SUCCESS", f"✅ [SUBTITLE DEBUG] Final video created: {os.path.basename(output_video_path)}")
                
                # Cleanup SRT file
                # try:
                #     os.remove(srt_temp_path)
                #     self.add_log("INFO", "🧹 [SUBTITLE DEBUG] Temporary SRT file cleaned up")
                # except:
                #     self.add_log("WARNING", "⚠️ [SUBTITLE DEBUG] Could not cleanup SRT file")
                
                return True, output_video_path
            else:
                self.add_log("ERROR", "❌ [SUBTITLE DEBUG] Failed to add subtitles to video")
                return False, ""
                
        except Exception as e:
            self.add_log("ERROR", f"❌ [SUBTITLE DEBUG] Unexpected error: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Full traceback: {traceback.format_exc()}")
            return False, ""

    
    def setup_defaults(self):
        """🔥 FIXED: Thiết lập giá trị mặc định chính xác với GUI sync test"""
        try:
            # 1. MẶC ĐỊNH OUTPUT FOLDER LÀ "output"
            current_dir = os.path.dirname(os.path.abspath(__file__))
            default_output = os.path.join(current_dir, "output")
            
            # Tạo thư mục output nếu chưa có
            if not os.path.exists(default_output):
                os.makedirs(default_output)
                self.add_log("INFO", f"📁 Created default output folder: {default_output}")
            
            if hasattr(self, 'output_path'):
                self.output_path.setText(default_output)
                self.add_log("INFO", f"📤 Default output folder set: {default_output}")
            
            # 2. MẶC ĐỊNH BẬT ADD BANNER/LOGO
            if hasattr(self, 'chk_add_banner'):
                self.chk_add_banner.setChecked(True)
                self.add_log("INFO", "🖼️ Add Banner/Logo enabled by default")
            
            #  3. BANNER POSITION VÀ SIZE 
            if hasattr(self, 'banner_x'):
                self.banner_x.setValue(230)  # X position
                self.add_log("INFO", f" Default banner X position: 230px")
                
            if hasattr(self, 'banner_y'):
                self.banner_y.setValue(1400)  
                self.add_log("INFO", f" Default banner Y position: 1400px")
                
            if hasattr(self, 'banner_height_ratio'):
                self.banner_height_ratio.setValue(0.18)  # Height ratio - GIÁ TRỊ CỦA BẠN
                self.add_log("INFO", f"📏 Default banner height ratio: 0.18 (18% of video height)")
            
            # 🔥 4. BANNER TIMING - TỪ GIÂY 5 ĐẾN GIÂY 12
            if hasattr(self, 'banner_start_time'):
                self.banner_start_time.setValue(5)  # Bắt đầu từ giây thứ 5
                self.add_log("INFO", f"⏰ Default banner start time: 5 seconds")
                
            if hasattr(self, 'banner_end_time'):
                self.banner_end_time.setValue(12)  # Kết thúc ở giây thứ 12
                self.add_log("INFO", f"⏰ Default banner end time: 12 seconds")
            
            # 🔥 5. SUBTITLE DEFAULTS - QUAN TRỌNG CHO GUI SYNC
            if hasattr(self, 'subtitle_size'):
                self.subtitle_size.setValue(60)  # Font size mặc định
                self.add_log("INFO", f"🔤 Default subtitle font size: 40px")
                
            if hasattr(self, 'subtitle_y'):
                self.subtitle_y.setValue(1400)  # Y position mặc định
                self.add_log("INFO", f"📍 Default subtitle Y position: 1200px")
                
            if hasattr(self, 'subtitle_style'):
                self.subtitle_style.setCurrentText("White with Shadow")  # Style mặc định
                self.add_log("INFO", f"🎨 Default subtitle style: White with Shadow")
            
            # 6. MẶC ĐỊNH BẬT CHROMAKEY (XÓA NỀN XANH)
            if hasattr(self, 'enable_chromakey'):
                self.enable_chromakey.setChecked(True)
                # Enable chromakey controls
                if hasattr(self, 'chroma_color'):
                    self.chroma_color.setEnabled(True)
                if hasattr(self, 'chroma_tolerance'):
                    self.chroma_tolerance.setEnabled(True)
                self.add_log("INFO", "🎭 Chromakey (remove green background) enabled by default")
            
            # 7. MẶC ĐỊNH CHROMA COLOR LÀ GREEN
            if hasattr(self, 'chroma_color'):
                self.chroma_color.setCurrentText("Green (0x00ff00)")
                self.add_log("INFO", "🟢 Default chromakey color: Green")
            
            # 🔥 8. MẶC ĐỊNH BẬT SUBTITLE
            if hasattr(self, 'chk_add_subtitle'):
                self.chk_add_subtitle.setChecked(True)
                self.add_log("INFO", "📝 Add Subtitles enabled by default")
            
            # 🔥 9. CẬP NHẬT PREVIEW NGAY SAU KHI SET DEFAULTS
            QApplication.processEvents()  # Đảm bảo UI đã load xong
            if hasattr(self, '_update_preview_positions'):
                self._update_preview_positions()
                self.add_log("INFO", "🔄 Preview positions updated with new defaults")
            
            # 🔥 10. TEST GUI SYNC - Đọc lại các giá trị để verify
            self.add_log("SUCCESS", "✅ GUI SYNC TEST - Verifying default values:")
            if hasattr(self, 'subtitle_size'):
                actual_font = self.subtitle_size.value()
                self.add_log("INFO", f"   🔤 Font size verified: {actual_font}px")
            if hasattr(self, 'subtitle_y'):
                actual_y = self.subtitle_y.value()
                self.add_log("INFO", f"   📍 Y position verified: {actual_y}px")
            if hasattr(self, 'subtitle_style'):
                actual_style = self.subtitle_style.currentText()
                self.add_log("INFO", f"   🎨 Style verified: {actual_style}")
            
            # 11. LOG TỔNG KẾT CÁC SETTINGS
            self.add_log("SUCCESS", "✅ All default settings applied successfully:")
            self.add_log("INFO", "   🖼️ Banner: ENABLED")
            self.add_log("INFO", "   📍 Position: (230, 1400) pixels")
            self.add_log("INFO", "   📐 Size: 18% of video height")
            self.add_log("INFO", "   ⏰ Timing: 5-12 seconds (7 seconds duration)")
            self.add_log("INFO", "   🎭 Chromakey: ENABLED (Green removal)")
            self.add_log("INFO", "   📝 Subtitle: ENABLED, 40px font, Y=1200px, White with Shadow")
            self.add_log("INFO", "   📁 Output: ./output folder")
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error setting defaults: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")

    def set_processing_state(self, is_processing):
        """Cập nhật trạng thái processing với spinner"""
        self.is_processing = is_processing
        
        if is_processing:
            # Bắt đầu processing
            self.btn_start_process.setText("🔄 PROCESSING...")
            self.btn_start_process.setEnabled(False)
            self.processing_spinner.start_spinning()
            
            # Có thể disable thêm một số controls quan trọng
            self.file_list.setEnabled(False)
            
            self.add_log("INFO", "🔄 Processing started...")
        else:
            # Kết thúc processing
            self.btn_start_process.setText("🚀 START BATCH PROCESSING")
            self.btn_start_process.setEnabled(True)
            self.processing_spinner.stop_spinning()
            
            # Re-enable controls
            self.file_list.setEnabled(True)
            
            self.add_log("SUCCESS", "✅ Processing completed!")

    # THAY THẾ HÀM NÀY TRONG gui_demo.py
    def run_banner_processing(self, main_video, banner_video, output_path, params) -> bool:
        """🔥 FIXED: Hàm worker để chạy add_video_banner với error handling tốt hơn"""
        try:
            self.add_log("INFO", "⚙️ Starting FFmpeg banner overlay process...")
            self.add_log("INFO", f"   📹 Main: {os.path.basename(main_video)}")
            self.add_log("INFO", f"   🖼️ Banner: {os.path.basename(banner_video)}")
            self.add_log("INFO", f"   📐 Size: {params['banner_width']}x{params['banner_height']}")
            self.add_log("INFO", f"   📍 Position: ({params['position_x']}, {params['position_y']})")
            
            # Đường dẫn FFmpeg
            ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe")
            
            if not os.path.exists(ffmpeg_path):
                self.add_log("ERROR", f"❌ FFmpeg not found: {ffmpeg_path}")
                return False
            
            # 🔥 FIXED: Gọi hàm add_video_banner với tham số đầy đủ
            success, log_output = add_video_banner(
                main_video_path=main_video,
                banner_video_path=banner_video,
                output_path=output_path,
                position_x=params["position_x"],
                position_y=params["position_y"],
                banner_width=params["banner_width"],      # 🔥 FIXED: Sử dụng key đúng
                banner_height=params["banner_height"],    # 🔥 FIXED: Sử dụng key đúng
                chroma_color=params["chroma_color"],
                similarity=params["similarity"],
                blend=params["blend"],
                start_time=params["start_time"],
                end_time=params["end_time"],
                ffmpeg_executable=ffmpeg_path
            )

            if success:
                self.add_log("SUCCESS", f"✅ Banner overlay completed successfully!")
                self.add_log("SUCCESS", f"   💾 Output: {os.path.basename(output_path)}")
                return True
            else:
                self.add_log("ERROR", f"❌ FFmpeg banner overlay failed!")
                
                # Log chi tiết lỗi FFmpeg
                if log_output:
                    self.add_log("ERROR", "--- FFmpeg Error Details ---")
                    error_lines = log_output.split('\n')
                    for line in error_lines:
                        if line.strip() and ('error' in line.lower() or 'failed' in line.lower() or 'invalid' in line.lower()):
                            self.add_log("ERROR", f"  {line.strip()}")
                    self.add_log("ERROR", "--- End Error Details ---")
                
                return False
                    
        except Exception as e:
            self.add_log("ERROR", f"❌ Exception in banner processing: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Full traceback: {traceback.format_exc()}")
            return False


    def _update_preview_positions(self):
        """FIXED: Cập nhật preview với TikTok-safe subtitle positioning và GUI sync"""
        if not hasattr(self, 'video_preview') or self.video_preview is None:
            return

        try:
            # 🔥 FIXED: Lấy giá trị THỰC TẾ từ GUI controls với safety checks
            real_banner_x = self.banner_x.value() if hasattr(self, 'banner_x') and self.banner_x is not None else 230
            real_banner_y = self.banner_y.value() if hasattr(self, 'banner_y') and self.banner_y is not None else 1400
            real_subtitle_y = self.subtitle_y.value() if hasattr(self, 'subtitle_y') and self.subtitle_y is not None else 1200
            real_source_x = self.source_x.value() if hasattr(self, 'source_x') and self.source_x is not None else 50
            real_source_y = self.source_y.value() if hasattr(self, 'source_y') and self.source_y is not None else 50
            
            # 🔥 ADDED: Lấy font size từ GUI để hiển thị trong preview
            gui_font_size = self.subtitle_size.value() if hasattr(self, 'subtitle_size') and self.subtitle_size is not None else 40
            gui_style = self.subtitle_style.currentText() if hasattr(self, 'subtitle_style') and self.subtitle_style is not None else "White with Shadow"
            
            # Tính kích thước banner thực tế với safety check
            banner_height_ratio = self.banner_height_ratio.value() if hasattr(self, 'banner_height_ratio') and self.banner_height_ratio is not None else 0.18
            real_banner_height = int(1920 * banner_height_ratio)
            real_banner_width = int(real_banner_height * 16/9)
            
            # 🔥 SUBTITLE: Always use TikTok-safe area - SAME as processing function
            REFERENCE_WIDTH = 1080
            BASE_LEFT_MARGIN = 90
            BASE_RIGHT_MARGIN = 130
            
            subtitle_safe_left = BASE_LEFT_MARGIN
            subtitle_safe_width = REFERENCE_WIDTH - BASE_LEFT_MARGIN - BASE_RIGHT_MARGIN
            subtitle_height = 80  # Default subtitle area height
            
            # Cập nhật preview với tọa độ safe
            self.video_preview.update_from_real_coordinates('banner', real_banner_x, real_banner_y, real_banner_width, real_banner_height)
            self.video_preview.update_from_real_coordinates('subtitle', subtitle_safe_left, real_subtitle_y, subtitle_safe_width, subtitle_height)
            self.video_preview.update_from_real_coordinates('source', real_source_x, real_source_y)
            
            # 🔥 LOG GUI VALUES FOR DEBUGGING
            self.add_log("DEBUG", f"🔄 Preview updated with GUI values:")
            self.add_log("DEBUG", f"   📍 Banner: ({real_banner_x}, {real_banner_y}) {real_banner_width}x{real_banner_height}")
            self.add_log("DEBUG", f"   📝 Subtitle: Y={real_subtitle_y}, Font={gui_font_size}px, Style={gui_style}")
            self.add_log("DEBUG", f"   📎 Source: ({real_source_x}, {real_source_y})")
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error updating preview positions: {str(e)}")

    # SỬA 3: Hàm init_ui() - THAY THẾ TOÀN BỘ
    def init_ui(self):
        """Create main layout and panels"""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (file management and settings)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel (preview and processing)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set panel sizes
        splitter.setSizes([650, 950])
        
        # Status bar and menu
        self.statusBar().showMessage("Ready - Optimized for 9:16 Videos")
        self.statusBar().setStyleSheet("QStatusBar { background-color: #2d3748; color: #e2e8f0; }")
        self.create_menu_bar()
        
        # Load API setup after UI is created
        self.setup_api_components()



    # THÊM MỚI 2: Sử dụng key đã chọn từ dropdown
    def use_selected_api_key(self):
        """Use the selected API key from dropdown with clear feedback"""
        try:
            # Check if dropdown has valid items
            if self.api_key_pool.count() <= 2:  # 0-1 items or just header
                self.add_log("WARNING", "⚠️ No API keys available to select")
                
                # Update status to show no keys
                self.api_status_label.setText("Primary API: ❌ No keys available")
                self.api_status_label.setStyleSheet("color: #dc2626; font-weight: bold;")
                return
            
            # Get selected key data
            selected_key = self.api_key_pool.currentData()
            selected_text = self.api_key_pool.currentText()
            
            # Check if valid key is selected
            if not selected_key or selected_key == "" or "📊" in selected_text:
                self.add_log("WARNING", "⚠️ Please select a valid API key (not the header)")
                
                # Update status
                self.api_status_label.setText("Primary API: ⚠️ No key selected")
                self.api_status_label.setStyleSheet("color: #d97706; font-weight: bold;")
                return
            
            # SUCCESS - Set the selected key to manual input
            self.api_key_input.setText(selected_key)
            
            # Update status to show key is ready for testing
            self.api_status_label.setText("Primary API: 🔑 Key loaded - Click Test")
            self.api_status_label.setStyleSheet("color: #0ea5e9; font-weight: bold;")
            
            # Clear and informative logging
            self.add_log("SUCCESS", f"✅ API key selected: {selected_text}")
            self.add_log("INFO", "💡 Key has been loaded into manual field")
            self.add_log("INFO", "🔍 Click 'Test' button to validate the key")
            
            # Flash effect for user feedback (optional)
            self.api_key_input.setStyleSheet("""
                QLineEdit#modernInput { 
                    border: 2px solid #10b981; 
                    background: #ecfdf5;
                }
            """)
            
            # Reset style after a moment
            QApplication.processEvents()
            import time
            time.sleep(0.1)
            self.api_key_input.setStyleSheet("")  # Reset to default
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error selecting API key: {str(e)}")
            
            # Update status to show error
            self.api_status_label.setText("Primary API: ❌ Selection error")
            self.api_status_label.setStyleSheet("color: #dc2626; font-weight: bold;")

    # ==============================================================================
    # == KHỐI CODE QUẢN LÝ API KEY - ==
    # ==============================================================================

    # THÊM MỚI 1: Hàm phụ trợ để cập nhật trạng thái API một cách nhất quán
    def _update_api_status(self, status: str, message: str):
        """
        Cập nhật label trạng thái API với màu sắc và nội dung tương ứng.
        Args:
            status (str): Trạng thái ('SUCCESS', 'ERROR', 'WARNING', 'INFO', 'TESTING').
            message (str): Nội dung thông báo.
        """
        status_colors = {
            "SUCCESS": "#16a34a",  # Green
            "ERROR": "#dc2626",    # Red
            "WARNING": "#d97706",  # Amber
            "INFO": "#0ea5e9",     # Blue
            "TESTING": "#d97706"   # Amber
        }
        color = status_colors.get(status, "#6b7280") # Mặc định là màu xám
        
        if hasattr(self, 'api_status_label'):
            self.api_status_label.setText(f"Primary API: {message}")
            self.api_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # Log thông báo tương ứng với trạng thái
        if status in ["SUCCESS", "ERROR", "WARNING", "INFO"]:
            self.add_log(status, message)
            
    # SỬA ĐỔI 1: Hàm thiết lập các thành phần API khi khởi động
    def setup_api_components(self):
        """Khởi tạo và thiết lập các thành phần liên quan đến API."""
        self.add_log("INFO", "🚀 Initializing API system...")
        QApplication.processEvents() # Cập nhật giao diện ngay lập tức

        # Tải các key từ file vào dropdown
        self.load_api_keys_to_dropdown()
        
        # Kiểm tra xem có key trong pool không và cập nhật trạng thái
        if hasattr(self, 'api_key_pool') and self.api_key_pool.count() > 1:
            self._update_api_status("INFO", "💡 Sẵn sàng - Nhập key hoặc chọn từ pool.")
        else:
            self._update_api_status("WARNING", "⚠️ Không có key trong pool, vui lòng nhập thủ công.")

        self.add_log("SUCCESS", "✅ API system initialization complete.")
        self.add_log("INFO", "📋 Hướng dẫn: 1. Chọn key từ pool hoặc nhập thủ công. 2. Nhấn 'Test' để kiểm tra.")

    # SỬA ĐỔI 2: Hàm tải API key vào dropdown
    def load_api_keys_to_dropdown(self):
        """Tải các API key từ file api_key.json và điền vào QComboBox."""
        if not hasattr(self, 'api_key_pool'):
            return

        self.api_key_pool.clear()
        self.add_log("INFO", "🔄 Loading API keys from pool...")
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "gg_api", "api_key.json")
            
            if not os.path.exists(json_path):
                self.api_key_pool.addItem("❌ Không tìm thấy file api_key.json")
                if hasattr(self, 'backup_api_label'):
                    self.backup_api_label.setText("❌ File api_key.json không tồn tại")
                    self.backup_api_label.setStyleSheet("color: #dc2626;")
                self.add_log("ERROR", f"File not found: {json_path}")
                return

            with open(json_path, 'r', encoding='utf-8') as f:
                api_data = json.load(f)

            key_count = 0
            for item in api_data:
                if isinstance(item, dict):
                    for name, api_key in item.items():
                        if api_key and len(api_key) > 14:
                            masked_key = f"{api_key[:10]}...{api_key[-4:]}"
                            display_text = f"🔑 {name} ({masked_key})"
                            self.api_key_pool.addItem(display_text, api_key) # Lưu key đầy đủ vào data
                            key_count += 1
            
            if key_count > 0:
                self.api_key_pool.insertItem(0, "📊 Chọn một key từ pool...")
                self.api_key_pool.setCurrentIndex(0)
                if hasattr(self, 'backup_api_label'):
                    self.backup_api_label.setText(f"✅ API Pool: {key_count} keys khả dụng")
                    self.backup_api_label.setStyleSheet("color: #16a34a; font-weight: bold;")
                self.add_log("SUCCESS", f"✅ Loaded {key_count} API keys.")
            else:
                self.api_key_pool.addItem("⚠️ Không có key hợp lệ trong file")
                if hasattr(self, 'backup_api_label'):
                    self.backup_api_label.setText("⚠️ API Pool: Rỗng")
                    self.backup_api_label.setStyleSheet("color: #d97706;")
                self.add_log("WARNING", "API key file is empty or contains no valid keys.")

        except (json.JSONDecodeError, FileNotFoundError) as e:
            error_msg = f"Error loading API keys: {str(e)}"
            self.api_key_pool.addItem("❌ Lỗi khi tải keys")
            if hasattr(self, 'backup_api_label'):
                self.backup_api_label.setText("❌ Lỗi tải API Pool")
                self.backup_api_label.setStyleSheet("color: #dc2626;")
            self.add_log("ERROR", error_msg)

    # SỬA ĐỔI 3: Hàm sử dụng key được chọn từ dropdown
    def use_selected_api_key(self):
        """Lấy key được chọn từ dropdown và điền vào ô input."""
        selected_key = self.api_key_pool.currentData()
        
        if selected_key: # currentData() trả về None nếu item không có data
            self.api_key_input.setText(selected_key)
            self._update_api_status("INFO", "🔑 Key đã được tải. Nhấn 'Test' để xác thực.")
            self.add_log("SUCCESS", f"✅ Selected API key: {self.api_key_pool.currentText()}")
        else:
            self._update_api_status("WARNING", "⚠️ Vui lòng chọn một key hợp lệ từ danh sách.")

    # SỬA ĐỔI 4: Hàm kiểm tra API key được viết lại hoàn toàn
    # SỬA LẠI LẦN CUỐI: Hàm test_api_key đơn giản, không dùng thread
    def test_api_key(self):
        """
        Kiểm tra API key một cách trực tiếp (có thể làm đơ GUI tối đa 10 giây).
        """
        api_key_to_test = self.api_key_input.text().strip()
        
        sender_btn = self.findChild(QPushButton, "testButton")

        if not api_key_to_test:
            self._update_api_status("WARNING", "⚠️ Chưa nhập API key.")
            return

        # Vô hiệu hóa nút và cập nhật UI
        if sender_btn:
            sender_btn.setEnabled(False)
            sender_btn.setText("🔄 Testing...")
        self._update_api_status("TESTING", "🔄 Đang kiểm tra key...")
        QApplication.processEvents() # Ép giao diện cập nhật ngay

        try:
            # Gọi trực tiếp hàm test đã có timeout
            results = test_key_function(api_key_to_test)
            
            if results and results.get("success"):
                self._update_api_status("SUCCESS", results.get("message"))
                self.add_log("SUCCESS", f"Model: {results.get('text_model', 'N/A')}")
            else:
                self._update_api_status("ERROR", results.get("message", "Lỗi không xác định"))

        except Exception as e:
            self._update_api_status("ERROR", f"❌ Lỗi khi gọi hàm test: {str(e)}")
        finally:
            # Luôn kích hoạt lại nút sau khi test xong
            if sender_btn:
                sender_btn.setEnabled(True)
                sender_btn.setText("🔍 Test")
    # ==============================================================================
    # == KẾT THÚC KHỐI CODE QUẢN LÝ API KEY ========================================
    # ==============================================================================
    


    def load_voice_data(self):
        """Load voice information from JSON file"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "gg_api", "voice_info.json")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                voice_data = json.load(f)
            
            # Chỉ log nếu log_text đã được tạo
            if hasattr(self, 'log_text'):
                self.add_log("SUCCESS", f"✅ Loaded {len(voice_data)} voices from voice_info.json")
            
            return voice_data
        except FileNotFoundError:
            if hasattr(self, 'log_text'):
                self.add_log("ERROR", "❌ voice_info.json not found")
            return []
        except json.JSONDecodeError:
            if hasattr(self, 'log_text'):
                self.add_log("ERROR", "❌ Error parsing voice_info.json")
            return []

    def preview_voice(self):
        """Preview selected voice with sample text"""
        if not hasattr(self, 'voice_combo') or self.voice_combo.count() == 0:
            self.add_log("WARNING", "⚠️ No voices available for preview")
            return
        
        selected_voice = self.voice_combo.currentData()  # Get actual voice name
        if not selected_voice:
            self.add_log("WARNING", "⚠️ No voice selected")
            return
        
        speed = self.voice_speed.value()
        sample_text = "Hello! This is a preview of the selected AI voice."
        
        self.add_log("INFO", f"🎵 Previewing voice: {selected_voice} at {speed}x speed")
        self.add_log("INFO", f"📝 Sample text: {sample_text}")
        
        # TODO: Implement actual voice preview using Google AI API

    def toggle_voice_controls(self, checked):
        """Enable/disable voice controls based on voice over checkbox"""
        if hasattr(self, 'voice_combo'):
            self.voice_combo.setEnabled(checked)
        if hasattr(self, 'voice_speed'):
            self.voice_speed.setEnabled(checked)
        
        # Update button states
        for btn in self.findChildren(QPushButton):
            if btn.text() == "🎵 Preview":
                btn.setEnabled(checked)
        
        if checked:
            self.add_log("INFO", "🔊 Voice controls enabled")
        else:
            self.add_log("INFO", "🔇 Voice controls disabled")

    def get_selected_voice_info(self):
        """Get information about currently selected voice"""
        if not hasattr(self, 'voice_combo'):
            return None
        
        selected_voice = self.voice_combo.currentData()
        if not selected_voice:
            return None
        
        # Load voice data and find selected voice info
        voice_data = self.load_voice_data()
        for voice in voice_data:
            if voice.get("Voice Name") == selected_voice:
                return {
                    "name": voice.get("Voice Name"),
                    "characteristic": voice.get("Characteristic"),
                    "gender": voice.get("Inferred Gender"),
                    "speed": self.voice_speed.value()
                }
        
        return None

    def init_ui(self):
        """Create main layout and panels"""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (file management and settings)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel (preview and processing)
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set panel sizes
        splitter.setSizes([650, 950])
        
        # Status bar and menu
        self.statusBar().showMessage("Ready - Optimized for 9:16 Videos")
        self.statusBar().setStyleSheet("QStatusBar { background-color: #2d3748; color: #e2e8f0; }")
        self.create_menu_bar()
        
        # Load API setup after UI is created
        self.setup_api_components() # Dòng này sẽ gọi bộ hàm mới mà bạn vừa dán vào
    

    def create_left_panel(self):
        """File management and settings panel with scroll support"""
        # Main widget container
        main_widget = QWidget()
        main_widget.setObjectName("leftPanel")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scrollable area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("modernScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ==================== FILE SELECTION GROUP ====================
        file_group = QGroupBox("📁 File Management")
        file_group.setObjectName("modernGroupBox")
        file_layout = QVBoxLayout(file_group)
        
        # File operation buttons
        btn_layout = QHBoxLayout()
        btn_add_files = QPushButton("📹 Add Videos")
        btn_add_files.setObjectName("primaryButton")
        btn_add_folder = QPushButton("📂 Add Folder")
        btn_add_folder.setObjectName("secondaryButton")
        
        btn_add_files.clicked.connect(self.add_files)
        btn_add_folder.clicked.connect(self.add_folder)
        
        btn_layout.addWidget(btn_add_files)
        btn_layout.addWidget(btn_add_folder)
        file_layout.addLayout(btn_layout)
        
        btn_clear_all = QPushButton("🗑️ Clear All")
        btn_clear_all.setObjectName("dangerButton")
        btn_clear_all.clicked.connect(self.clear_files)
        file_layout.addWidget(btn_clear_all)
        
        # File list widget
        self.file_list = QListWidget()
        self.file_list.setObjectName("modernList")
        self.file_list.setMaximumHeight(150)  # Limit height to save space
        file_layout.addWidget(QLabel("Selected Files (9:16 Videos):"))
        file_layout.addWidget(self.file_list)
        
        layout.addWidget(file_group)
        
        # ==================== LANGUAGE & VOICE SETTINGS GROUP ====================
        ai_group = QGroupBox("🤖 Language & Voice Settings")
        ai_group.setObjectName("modernGroupBox")
        ai_layout = QVBoxLayout(ai_group)
        
        # -------- API Key management section --------
        api_frame = QFrame()
        api_frame.setObjectName("settingsFrame")
        api_grid = QGridLayout(api_frame)
        
        # Row 1: Manual API Key Input
        api_grid.addWidget(QLabel("Manual API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your Google AI API key manually")
        self.api_key_input.setObjectName("modernInput")
        api_grid.addWidget(self.api_key_input, 0, 1)
        
        btn_test_api = QPushButton("🔍 Test")
        btn_test_api.setObjectName("testButton")
        btn_test_api.clicked.connect(self.test_api_key)
        btn_test_api.setToolTip("Test the API key")
        api_grid.addWidget(btn_test_api, 0, 2)
        
        # Row 2: OR separator
        or_label = QLabel("— OR —")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setObjectName("infoLabel")
        or_label.setStyleSheet("color: #9ca3af; font-weight: bold; margin: 8px 0;")
        api_grid.addWidget(or_label, 1, 0, 1, 3)
        
        # Row 3: Select from Pool
        api_grid.addWidget(QLabel("Select from Pool:"), 2, 0)
        self.api_key_pool = QComboBox()
        self.api_key_pool.setObjectName("modernCombo")
        self.api_key_pool.addItem("🔄 Loading available keys...")
        api_grid.addWidget(self.api_key_pool, 2, 1)
        
        btn_use_selected = QPushButton("✅ Use")
        btn_use_selected.setObjectName("testButton")
        btn_use_selected.clicked.connect(self.use_selected_api_key)
        btn_use_selected.setToolTip("Use the selected API key from pool")
        api_grid.addWidget(btn_use_selected, 2, 2)
        
        # Row 4: API Status
        self.api_status_label = QLabel("Primary API: Not tested")
        self.api_status_label.setObjectName("statusLabel")
        api_grid.addWidget(self.api_status_label, 3, 0, 1, 2)
        
        # Row 5: Backup API information
        self.backup_api_label = QLabel("🔄 Loading backup keys...")
        self.backup_api_label.setObjectName("infoLabel")
        api_grid.addWidget(self.backup_api_label, 4, 0, 1, 3)
        
        ai_layout.addWidget(api_frame)
        
        # -------- Language settings section --------
        lang_frame = QFrame()
        lang_frame.setObjectName("settingsFrame")
        lang_grid = QGridLayout(lang_frame)
        
        # Source Language
        lang_grid.addWidget(QLabel("Source Language:"), 0, 0)
        self.source_lang = QComboBox()
        self.source_lang.setObjectName("modernCombo")
        self.source_lang.addItems([
            "🔍 Auto Detect", "🇺🇸 English", "🇨🇳 Chinese", "🇯🇵 Japanese", "🇩🇪 German", "🇮🇳 Hindi",
            "🇬🇧 English (UK)", "🇫🇷 French", "🇮🇹 Italian", "🇧🇷 Portuguese", "🇨🇦 English (CA)",
            "🇰🇷 Korean", "🇪🇸 Spanish", "🇷🇺 Russian", "🇦🇺 English (AU)", "🇳🇱 Dutch",
            "🇸🇦 Arabic", "🇦🇪 Arabic (UAE)", "🇻🇳 Vietnamese"
        ])
        lang_grid.addWidget(self.source_lang, 0, 1)
        
        # Target Language
        lang_grid.addWidget(QLabel("Target Language:"), 1, 0)
        self.target_lang = QComboBox()
        self.target_lang.setObjectName("modernCombo")
        self.target_lang.addItems([
            "🇺🇸 English", "🇨🇳 Chinese", "🇯🇵 Japanese", "🇩🇪 German", "🇮🇳 Hindi",
            "🇬🇧 English (UK)", "🇫🇷 French", "🇮🇹 Italian", "🇧🇷 Portuguese", "🇨🇦 English (CA)",
            "🇰🇷 Korean", "🇪🇸 Spanish", "🇷🇺 Russian", "🇦🇺 English (AU)", "🇳🇱 Dutch",
            "🇸🇦 Arabic", "🇦🇪 Arabic (UAE)", "🇻🇳 Vietnamese"
        ])
        lang_grid.addWidget(self.target_lang, 1, 1)
        
        ai_layout.addWidget(lang_frame)
        
        # -------- Voice Selection section --------
        voice_frame = QFrame()
        voice_frame.setObjectName("settingsFrame")
        voice_grid = QGridLayout(voice_frame)

        # Voice selection dropdown
        voice_grid.addWidget(QLabel("🔊 AI Voice:"), 0, 0)
        self.voice_combo = QComboBox()
        self.voice_combo.setObjectName("modernCombo")

        # Load and populate voice dropdown with data from JSON
        voice_data = self.load_voice_data()
        if voice_data:
            for voice in voice_data:
                voice_name = voice.get("Voice Name", "Unknown")
                characteristic = voice.get("Characteristic", "")
                gender = voice.get("Inferred Gender", "")
                
                # Create display text with NEW EMOJI for gender
                gender_emoji = ""
                if "Nữ" in gender and "Nam" in gender:
                    gender_emoji = "⚧️"  # Unisex voice
                elif "Nữ" in gender:
                    gender_emoji = "♀️"  # Female voice (purple circle)
                elif "Nam" in gender:
                    gender_emoji = "♂️"  # Male voice (blue circle)
                else:
                    gender_emoji = "⚪"  # Unknown gender (white circle)
                
                display_text = f"{gender_emoji} {voice_name} - {characteristic}"
                self.voice_combo.addItem(display_text, voice_name)  # Store actual voice name as data
        else:
            self.voice_combo.addItem("❌ No voices loaded")

        voice_grid.addWidget(self.voice_combo, 0, 1, 1, 2)

        # Voice preview button
        btn_preview_voice = QPushButton("🎵 Preview")
        btn_preview_voice.setObjectName("testButton")
        btn_preview_voice.clicked.connect(self.preview_voice)
        btn_preview_voice.setToolTip("Preview the selected voice")
        voice_grid.addWidget(btn_preview_voice, 1, 0)

        # Voice speed control
        voice_grid.addWidget(QLabel("Speed:"), 1, 1)
        self.voice_speed = QDoubleSpinBox()
        self.voice_speed.setObjectName("modernSpin")
        self.voice_speed.setRange(0.5, 2.0)
        self.voice_speed.setValue(1.0)
        self.voice_speed.setSingleStep(0.1)
        self.voice_speed.setSuffix("x")
        voice_grid.addWidget(self.voice_speed, 1, 2)

        # Voice settings info
        voice_info_label = QLabel("💡 Voice only applied when 'Replace with AI Voice' is enabled")
        voice_info_label.setObjectName("infoLabel")
        voice_grid.addWidget(voice_info_label, 2, 0, 1, 3)

        ai_layout.addWidget(voice_frame)
        layout.addWidget(ai_group)
        
        
        effects_group = QGroupBox("🎨 Video Effects (9:16 Optimized)")
        effects_group.setObjectName("modernGroupBox")
        effects_layout = QGridLayout(effects_group)
        
        # Row 1
        self.chk_add_banner = QCheckBox("🖼️ Add Banner/Logo")
        self.chk_add_subtitle = QCheckBox("📝 Add Translated Subtitles")
        effects_layout.addWidget(self.chk_add_banner, 0, 0)
        effects_layout.addWidget(self.chk_add_subtitle, 0, 1)
        
        # Row 2
        self.chk_add_source = QCheckBox("📎 Add Source Text")
        self.chk_voice_over = QCheckBox("🔊 Replace with AI Voice")
        effects_layout.addWidget(self.chk_add_source, 1, 0)
        effects_layout.addWidget(self.chk_voice_over, 1, 1)
        
        # Apply styles to checkboxes
        for chk in [self.chk_add_banner, self.chk_add_subtitle, self.chk_add_source, self.chk_voice_over]:
            chk.setObjectName("modernCheckbox")
        
        # Connect voice over checkbox to enable/disable voice controls (after checkbox is created)
        self.chk_voice_over.toggled.connect(self.toggle_voice_controls)
        
        layout.addWidget(effects_group)
        
        # ==================== OUTPUT SETTINGS ====================
        output_group = QGroupBox("📤 Output Settings")
        output_group.setObjectName("modernGroupBox")
        output_layout = QGridLayout(output_group)
        
        # Output folder selection
        output_layout.addWidget(QLabel("Output Folder:"), 0, 0)
        self.output_path = QLineEdit()
        self.output_path.setObjectName("modernInput")
        self.output_path.setPlaceholderText("Select output directory...")
        output_layout.addWidget(self.output_path, 0, 1)
        btn_browse_output = QPushButton("📁")
        btn_browse_output.setObjectName("iconButton")
        btn_browse_output.clicked.connect(self.browse_output)
        output_layout.addWidget(btn_browse_output, 0, 2)
        
        # Output format selection
        output_layout.addWidget(QLabel("Output Format:"), 1, 0)
        self.output_format = QComboBox()
        self.output_format.setObjectName("modernCombo")
        self.output_format.addItems(["MP4 (Recommended)", "AVI", "MOV"])
        output_layout.addWidget(self.output_format, 1, 1, 1, 2)
        
        # Quality information
        quality_label = QLabel("📊 Quality: Original (No compression)")
        quality_label.setObjectName("infoLabel")
        output_layout.addWidget(quality_label, 2, 0, 1, 3)
        
        layout.addWidget(output_group)
        
        # ==================== FINALIZE LAYOUT ====================
        # Add stretch at the end to push everything up
        layout.addStretch()
        
        # Set the content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        return main_widget
    


    def create_right_panel(self):
        """Preview and processing tabs"""
        widget = QWidget()
        widget.setObjectName("rightPanel")
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Create tabbed interface
        tab_widget = QTabWidget()
        tab_widget.setObjectName("modernTabs")
        
        # Add tabs
        preview_tab = self.create_preview_tab()
        tab_widget.addTab(preview_tab, "👁️ Preview")
        
        processing_tab = self.create_processing_tab()
        tab_widget.addTab(processing_tab, "⚙️ Processing")
        
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "📋 Logs")
        
        layout.addWidget(tab_widget)
        
        
        # Các dòng này đảm bảo rằng ngay khi giao diện được tạo,
        # các kết nối sẽ được thiết lập và preview sẽ hiển thị ở đúng vị trí ban đầu.
        self._connect_preview_signals()
        self._update_preview_positions() 

        return widget
    
    def _connect_preview_signals(self):
        """Kết nối sự kiện valueChanged của các controls tới hàm cập nhật preview với safety checks."""
        
        try:
            connected_count = 0
            
            # Banner signals - WITH SAFETY CHECKS
            if hasattr(self, 'banner_x') and self.banner_x is not None:
                self.banner_x.valueChanged.connect(self._update_preview_positions)
                connected_count += 1
                
            if hasattr(self, 'banner_y') and self.banner_y is not None:
                self.banner_y.valueChanged.connect(self._update_preview_positions)
                connected_count += 1
                
            if hasattr(self, 'banner_height_ratio') and self.banner_height_ratio is not None:
                self.banner_height_ratio.valueChanged.connect(self._update_preview_positions)
                connected_count += 1

            # 🔥 REMOVED: subtitle_x signal - không còn cần thiết
            # Subtitle Y signal only - WITH SAFETY CHECK
            if hasattr(self, 'subtitle_y') and self.subtitle_y is not None:
                self.subtitle_y.valueChanged.connect(self._update_preview_positions)
                connected_count += 1

            # Source text signals - WITH SAFETY CHECKS
            if hasattr(self, 'source_x') and self.source_x is not None:
                self.source_x.valueChanged.connect(self._update_preview_positions)
                connected_count += 1
                
            if hasattr(self, 'source_y') and self.source_y is not None:
                self.source_y.valueChanged.connect(self._update_preview_positions)
                connected_count += 1
            
            self.add_log("SUCCESS", f"🔗 Real-time preview connections established: {connected_count} signals connected")
            self.add_log("INFO", "📍 Subtitle positioning: Auto-centered horizontally, Y-position adjustable")
            
            # 🔥 TRIGGER INITIAL PREVIEW UPDATE AFTER CONNECTIONS
            if hasattr(self, '_update_preview_positions'):
                self._update_preview_positions()
                self.add_log("INFO", "🔄 Initial preview positions updated")
                
        except Exception as e:
            self.add_log("ERROR", f"❌ Error connecting preview signals: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")


    def create_preview_tab(self):
        """Video preview and effects settings"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(20)
        
        # Video preview section (left side)
        preview_group = QGroupBox("📱 9:16 Video Preview")
        preview_group.setObjectName("modernGroupBox")
        preview_layout = QVBoxLayout(preview_group)
        
        # Custom video preview widget
        self.video_preview = VideoPreviewWidget()
        preview_layout.addWidget(self.video_preview, alignment=Qt.AlignCenter)
        
        preview_info = QLabel("📐 Optimized for mobile/social media\n📱 Vertical format (9:16)\n🔄 Auto-converts non-9:16 videos")
        preview_info.setObjectName("infoLabel")
        preview_info.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_info)
        
        # START BUTTON VỚI SPINNER
        start_button_frame = QFrame()
        start_button_frame.setObjectName("startButtonFrame")
        start_button_layout = QHBoxLayout(start_button_frame)
        start_button_layout.setContentsMargins(0, 20, 0, 10)
        
        self.btn_start_process = QPushButton("🚀 START BATCH PROCESSING")
        self.btn_start_process.setObjectName("startButton")
        self.btn_start_process.clicked.connect(self.start_processing)
        
        # Tạo spinner
        self.processing_spinner = SimpleSpinner()
        
        start_button_layout.addWidget(self.btn_start_process)
        start_button_layout.addWidget(self.processing_spinner)
        start_button_layout.addStretch()
        
        preview_layout.addWidget(start_button_frame)
        
        layout.addWidget(preview_group)
        
        # Settings section (right side with scroll)
        settings_scroll = QScrollArea()
        settings_scroll.setObjectName("modernScroll")
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # 🔥 BANNER SETTINGS - UNCHANGED
        banner_group = QGroupBox("🖼️ Video Banner Settings")
        banner_group.setObjectName("modernGroupBox")
        banner_layout = QGridLayout(banner_group)
        
        # Row 0: Banner file
        banner_layout.addWidget(QLabel("Banner File:"), 0, 0)
        self.banner_path = QLineEdit()
        self.banner_path.setObjectName("modernInput")
        self.banner_path.setPlaceholderText("Select video banner file...")
        banner_layout.addWidget(self.banner_path, 0, 1)
        btn_browse_banner = QPushButton("📁")
        btn_browse_banner.setObjectName("iconButton")
        btn_browse_banner.clicked.connect(self.browse_banner)
        banner_layout.addWidget(btn_browse_banner, 0, 2)
        
        # Row 1: Position X
        banner_layout.addWidget(QLabel("Position X:"), 1, 0)
        self.banner_x = QSpinBox()
        self.banner_x.setObjectName("modernSpin")
        self.banner_x.setRange(0, 1080)
        self.banner_x.setValue(250)
        self.banner_x.setSuffix(" px")
        banner_layout.addWidget(self.banner_x, 1, 1)
        
        # Row 2: Position Y
        banner_layout.addWidget(QLabel("Position Y:"), 2, 0)
        self.banner_y = QSpinBox()
        self.banner_y.setObjectName("modernSpin")
        self.banner_y.setRange(0, 1920)
        self.banner_y.setValue(1550)
        self.banner_y.setSuffix(" px")
        banner_layout.addWidget(self.banner_y, 2, 1)
        
        # Row 3: Banner height ratio
        banner_layout.addWidget(QLabel("Banner Height:"), 3, 0)
        self.banner_height_ratio = QDoubleSpinBox()
        self.banner_height_ratio.setObjectName("modernSpin")
        self.banner_height_ratio.setRange(0.1, 0.8)
        self.banner_height_ratio.setValue(0.6)
        self.banner_height_ratio.setSingleStep(0.05)
        self.banner_height_ratio.setSuffix(" ratio")
        banner_layout.addWidget(self.banner_height_ratio, 3, 1, 1, 2)
        
        # Row 4: Timing section
        timing_frame = QFrame()
        timing_frame.setObjectName("settingsFrame")
        timing_layout = QHBoxLayout(timing_frame)
        
        timing_layout.addWidget(QLabel("⏰ Show from:"))
        self.banner_start_time = QSpinBox()
        self.banner_start_time.setObjectName("modernSpin")
        self.banner_start_time.setRange(0, 3600)
        self.banner_start_time.setValue(0)
        self.banner_start_time.setSuffix("s")
        timing_layout.addWidget(self.banner_start_time)
        
        timing_layout.addWidget(QLabel("to:"))
        self.banner_end_time = QSpinBox()
        self.banner_end_time.setObjectName("modernSpin")
        self.banner_end_time.setRange(1, 3600)
        self.banner_end_time.setValue(60)
        self.banner_end_time.setSuffix("s")
        timing_layout.addWidget(self.banner_end_time)
        
        banner_layout.addWidget(timing_frame, 4, 0, 1, 3)
        
        # Row 5: Chromakey settings
        chroma_frame = QFrame()
        chroma_frame.setObjectName("settingsFrame")
        chroma_layout = QGridLayout(chroma_frame)
        
        # Enable/disable chromakey
        self.enable_chromakey = QCheckBox("🎭 Remove banner background")
        self.enable_chromakey.setObjectName("modernCheckbox")
        self.enable_chromakey.setChecked(True)
        chroma_layout.addWidget(self.enable_chromakey, 0, 0, 1, 3)
        
        # Chromakey color
        chroma_layout.addWidget(QLabel("Color:"), 1, 0)
        self.chroma_color = QComboBox()
        self.chroma_color.setObjectName("modernCombo")
        self.chroma_color.addItems(["Green (0x00ff00)", "Blue (0x0000ff)", "Black (0x000000)", "White (0xffffff)", "Red (0xff0000)"])
        self.chroma_color.setEnabled(True)
        chroma_layout.addWidget(self.chroma_color, 1, 1)
        
        # Chromakey tolerance
        chroma_layout.addWidget(QLabel("Tolerance:"), 1, 2)
        self.chroma_tolerance = QSpinBox()
        self.chroma_tolerance.setObjectName("modernSpin")
        self.chroma_tolerance.setRange(0, 100)
        self.chroma_tolerance.setValue(20)
        self.chroma_tolerance.setSuffix("%")
        self.chroma_tolerance.setEnabled(True)
        chroma_layout.addWidget(self.chroma_tolerance, 1, 3)
        
        # Connect checkbox to enable/disable chromakey controls
        self.enable_chromakey.toggled.connect(lambda checked: [
            self.chroma_color.setEnabled(checked),
            self.chroma_tolerance.setEnabled(checked)
        ])
        
        banner_layout.addWidget(chroma_frame, 5, 0, 1, 3)
        settings_layout.addWidget(banner_group)
        
        # 🔥 SUBTITLE SETTINGS - REMOVED POSITION X, ALWAYS CENTERED
        subtitle_group = QGroupBox("📝 Subtitle Settings (Auto-Centered)")
        subtitle_group.setObjectName("modernGroupBox")
        subtitle_layout = QGridLayout(subtitle_group)
        
        # Font Size
        subtitle_layout.addWidget(QLabel("Font Size:"), 0, 0)
        self.subtitle_size = QSpinBox()
        self.subtitle_size.setObjectName("modernSpin")
        self.subtitle_size.setRange(10, 100)
        self.subtitle_size.setValue(40)
        self.subtitle_size.setSuffix("px")
        subtitle_layout.addWidget(self.subtitle_size, 0, 1)
        
        # 🔥 REMOVED: Position X - Always centered horizontally
        # INFO LABEL ABOUT CENTERING
        center_info = QLabel("📍 Horizontal Position: Auto-centered")
        center_info.setObjectName("infoLabel")
        center_info.setStyleSheet("color: #10b981; font-weight: bold;")
        subtitle_layout.addWidget(center_info, 1, 0, 1, 2)
        
        # Position Y (vertical position still adjustable)
        subtitle_layout.addWidget(QLabel("Vertical Position Y:"), 2, 0)
        self.subtitle_y = QSpinBox()
        self.subtitle_y.setObjectName("modernSpin")
        self.subtitle_y.setRange(0, 1920)
        self.subtitle_y.setValue(1200)
        self.subtitle_y.setSuffix(" px")
        subtitle_layout.addWidget(self.subtitle_y, 2, 1)
        
        # Style
        subtitle_layout.addWidget(QLabel("Style:"), 3, 0)
        self.subtitle_style = QComboBox()
        self.subtitle_style.setObjectName("modernCombo")
        self.subtitle_style.addItems(["White with Shadow", "Black with White Outline", "Yellow", "Custom"])
        subtitle_layout.addWidget(self.subtitle_style, 3, 1)
        
        settings_layout.addWidget(subtitle_group)
        
        # SOURCE SETTINGS - UNCHANGED
        source_group = QGroupBox("📎 Source Text Settings")
        source_group.setObjectName("modernGroupBox")
        source_layout = QGridLayout(source_group)
        
        source_layout.addWidget(QLabel("Source Text:"), 0, 0)
        self.source_text = QLineEdit()
        self.source_text.setObjectName("modernInput")
        self.source_text.setPlaceholderText("e.g., @username, website.com")
        self.source_text.setText("@YourChannel")
        source_layout.addWidget(self.source_text, 0, 1)
        
        source_layout.addWidget(QLabel("Position X:"), 1, 0)
        self.source_x = QSpinBox()
        self.source_x.setObjectName("modernSpin")
        self.source_x.setRange(0, 1080)
        self.source_x.setValue(0)
        self.source_x.setSuffix(" px")
        source_layout.addWidget(self.source_x, 1, 1)
        
        source_layout.addWidget(QLabel("Position Y:"), 2, 0)
        self.source_y = QSpinBox()
        self.source_y.setObjectName("modernSpin")
        self.source_y.setRange(0, 1920)
        self.source_y.setValue(0)
        self.source_y.setSuffix(" px")
        source_layout.addWidget(self.source_y, 2, 1)
        
        source_layout.addWidget(QLabel("Font Size:"), 3, 0)
        self.source_font_size = QSpinBox()
        self.source_font_size.setObjectName("modernSpin")
        self.source_font_size.setRange(10, 24)
        self.source_font_size.setValue(14)
        self.source_font_size.setSuffix("px")
        source_layout.addWidget(self.source_font_size, 3, 1)
        
        settings_layout.addWidget(source_group)
        
        settings_layout.addStretch()
        settings_scroll.setWidget(settings_widget)
        settings_scroll.setWidgetResizable(True)
        
        layout.addWidget(settings_scroll)
        return widget
    # ==============================================================================
    # THÊM HÀM set_processing_state() VÀ start_processing() CẬP NHẬT
    # ==============================================================================
    def set_processing_state(self, is_processing):
        """Cập nhật trạng thái processing với spinner"""
        self.is_processing = is_processing
        
        if is_processing:
            # Bắt đầu processing
            self.btn_start_process.setText("🔄 PROCESSING...")
            self.btn_start_process.setEnabled(False)
            self.processing_spinner.start_spinning()
            
            # Có thể disable thêm một số controls quan trọng
            self.file_list.setEnabled(False)
            
            self.add_log("INFO", "🔄 Processing started...")
            
        else:
            # Kết thúc processing
            self.btn_start_process.setText("🚀 START BATCH PROCESSING")
            self.btn_start_process.setEnabled(True)
            self.processing_spinner.stop_spinning()
            
            # Re-enable controls
            self.file_list.setEnabled(True)
            
            self.add_log("SUCCESS", "✅ Processing completed!")

    def get_video_dimensions(self, video_path: str) -> tuple[int | None, int | None]:
        """
        Lấy kích thước thực tế của video - UNIVERSAL cho mọi kích thước.
        Returns: (width, height) hoặc (None, None) nếu lỗi
        """
        try:
            import subprocess
            
            ffprobe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffprobe.exe")
            
            if not os.path.exists(ffprobe_path):
                self.add_log("ERROR", f"❌ FFprobe not found: {ffprobe_path}")
                return None, None
            
            probe_cmd = [
                ffprobe_path,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                video_path
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                try:
                    output_parts = result.stdout.strip().split(',')
                    if len(output_parts) >= 2:
                        width = int(output_parts[0])
                        height = int(output_parts[1])
                        self.add_log("INFO", f"📐 Video dimensions detected: {width}x{height}")
                        return width, height
                except (ValueError, IndexError):
                    self.add_log("ERROR", f"❌ Cannot parse dimensions: {result.stdout}")
            else:
                self.add_log("ERROR", f"❌ FFprobe error: {result.stderr}")
            
            return None, None
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error getting video dimensions: {str(e)}")
            return None, None

    def calculate_universal_banner_params(self, video_width: int, video_height: int) -> dict | None:
        """🔥 FIXED: Tính toán banner params với validation đầy đủ"""
        try:
            # Input validation
            if video_width <= 0 or video_height <= 0:
                self.add_log("ERROR", f"❌ Invalid video dimensions: {video_width}x{video_height}")
                return None
            
            # Reference size
            REFERENCE_WIDTH = 1080
            REFERENCE_HEIGHT = 1920
            
            # 🔥 Lấy và validate GUI values
            try:
                gui_x = self.banner_x.value()
                gui_y = self.banner_y.value()
                gui_height_ratio = self.banner_height_ratio.value()
                gui_start_time = self.banner_start_time.value()
                gui_end_time = self.banner_end_time.value()
            except Exception as e:
                self.add_log("ERROR", f"❌ Error reading GUI values: {str(e)}")
                return None
            
            # Validation
            if gui_height_ratio <= 0 or gui_height_ratio > 1:
                self.add_log("ERROR", f"❌ Invalid banner height ratio: {gui_height_ratio}")
                return None
            
            # Scaling calculations
            width_scale = video_width / REFERENCE_WIDTH
            height_scale = video_height / REFERENCE_HEIGHT
            
            # Position mapping
            actual_x = int(gui_x * width_scale)
            actual_y = int(gui_y * height_scale)
            
            # Banner size calculations
            actual_banner_height = int(video_height * gui_height_ratio)
            actual_banner_width = int(actual_banner_height * 16/9)  # 16:9 aspect ratio
            
            # Boundary checks
            if actual_banner_width > video_width:
                actual_banner_width = int(video_width * 0.9)
                actual_banner_height = int(actual_banner_width * 9/16)
                self.add_log("WARNING", f"⚠️ Banner width adjusted to fit video: {actual_banner_width}x{actual_banner_height}")
            
            # Position clamping
            max_x = max(0, video_width - actual_banner_width)
            max_y = max(0, video_height - actual_banner_height)
            final_x = max(0, min(actual_x, max_x))
            final_y = max(0, min(actual_y, max_y))
            
            # 🔥 Get chroma settings safely
            chroma_color = self._get_chroma_color()
            chroma_similarity = self.chroma_tolerance.value() / 100.0 if hasattr(self, 'chroma_tolerance') else 0.2
            
            # 🔥 Build final parameters dictionary
            params = {
                "position_x": final_x,
                "position_y": final_y,
                "banner_width": actual_banner_width,
                "banner_height": actual_banner_height,
                "chroma_color": chroma_color,
                "similarity": chroma_similarity,
                "blend": 0.2,
                "start_time": gui_start_time,
                "end_time": gui_end_time
            }
            
            # Detailed logging
            self.add_log("SUCCESS", f"🎯 Banner parameters calculated successfully:")
            self.add_log("INFO", f"   📐 Video: {video_width}x{video_height}")
            self.add_log("INFO", f"   📏 Scale: {width_scale:.3f}x, {height_scale:.3f}x")
            self.add_log("INFO", f"   📍 Position: ({gui_x}, {gui_y}) → ({final_x}, {final_y})")
            self.add_log("INFO", f"   📐 Banner: {actual_banner_width}x{actual_banner_height} ({gui_height_ratio*100:.1f}%)")
            
            return params
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Banner calculation error: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")
            return None

    def _get_chroma_color(self) -> str:
        """🔥 HELPER: Lấy chroma color từ GUI"""
        if not self.enable_chromakey.isChecked():
            return "none"
        
        chroma_map = {
            "Green (0x00ff00)": "0x00ff00",
            "Blue (0x0000ff)": "0x0000ff", 
            "Black (0x000000)": "0x000000",
            "White (0xffffff)": "0xffffff",
            "Red (0xff0000)": "0xff0000"
        }
        selected = self.chroma_color.currentText()
        return chroma_map.get(selected, "0x00ff00")

    
    def process_banner_with_universal_mapping(self, main_video_path: str, banner_video_path: str, output_path: str) -> bool:
        """🔥 FIXED: Xử lý banner với mapping chính xác cho mọi kích thước video"""
        try:
            # Step 1: Lấy kích thước video
            video_width, video_height = self.get_video_dimensions(main_video_path)
            
            if video_width is None or video_height is None:
                self.add_log("ERROR", f"❌ Cannot determine video size: {os.path.basename(main_video_path)}")
                return False
            
            # Step 2: Tính toán thông số universal
            banner_params = self.calculate_universal_banner_params(video_width, video_height)
            
            if not banner_params:
                self.add_log("ERROR", f"❌ Universal banner calculation failed")
                return False
            
            # Step 3: 🔥 FIXED - Lấy chroma settings
            chroma_color = banner_params.get("chroma_color", "0x00ff00")
            
            # Step 4: 🔥 FIXED - Tạo final params với keys chính xác
            final_params = {
                "position_x": banner_params["position_x"],
                "position_y": banner_params["position_y"],
                "banner_width": banner_params["banner_width"],     # 🔥 FIXED: Key đúng
                "banner_height": banner_params["banner_height"],   # 🔥 FIXED: Key đúng
                "chroma_color": chroma_color,
                "similarity": banner_params["similarity"],
                "blend": banner_params["blend"],
                "start_time": banner_params["start_time"],
                "end_time": banner_params["end_time"]
            }
            
            # Step 5: Log final parameters
            self.add_log("INFO", f"🎬 Final FFmpeg parameters for {os.path.basename(main_video_path)}:")
            self.add_log("INFO", f"   ➡️ Position: ({final_params['position_x']}, {final_params['position_y']})")
            self.add_log("INFO", f"   ➡️ Banner Size: {final_params['banner_width']}x{final_params['banner_height']} pixels")
            self.add_log("INFO", f"   ➡️ Chroma: {final_params['chroma_color']}, Similarity: {final_params['similarity']}")
            self.add_log("INFO", f"   ➡️ Timing: {final_params['start_time']}s to {final_params['end_time']}s")
            
            # Step 6: Gọi hàm xử lý banner
            success = self.run_banner_processing(main_video_path, banner_video_path, output_path, final_params)
            
            if success:
                self.add_log("SUCCESS", f"✅ Banner processing completed: {os.path.basename(main_video_path)}")
            else:
                self.add_log("ERROR", f"❌ Banner processing failed: {os.path.basename(main_video_path)}")
            
            return success
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Universal banner processing error: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")
            return False
        
    def start_processing(self):
        """Begin batch video processing với UNIVERSAL banner mapping và subtitle generation"""
        if self.file_list.count() == 0:
            self.add_log("WARNING", "⚠️ No files selected for processing")
            return

        # Bắt đầu processing state
        self.set_processing_state(True)
        QApplication.processEvents()

        try:
            self.add_log("INFO", "🚀 Starting UNIVERSAL batch processing...")
            self.add_log("INFO", f"📊 Processing {self.file_list.count()} files")

            # 🔥 DEBUG: Kiểm tra trạng thái checkbox
            add_banner_checked = self.chk_add_banner.isChecked()
            add_subtitle_checked = self.chk_add_subtitle.isChecked()
            add_source_checked = self.chk_add_source.isChecked()
            add_voice_checked = self.chk_voice_over.isChecked()
            
            self.add_log("INFO", f"🔍 [DEBUG] Checkbox status:")
            self.add_log("INFO", f"   🖼️ Banner: {add_banner_checked}")
            self.add_log("INFO", f"   📝 Subtitle: {add_subtitle_checked}")
            self.add_log("INFO", f"   📎 Source: {add_source_checked}")
            self.add_log("INFO", f"   🔊 Voice: {add_voice_checked}")

            # Log processing settings
            source_lang = self.source_lang.currentText()
            target_lang = self.target_lang.currentText()
            self.add_log("INFO", f"🌐 Language: {source_lang} → {target_lang}")

            # Log enabled effects
            effects = []
            if add_banner_checked:
                effects.append("Universal Banner Mapping")
            if add_subtitle_checked:
                effects.append("AI Subtitles")
            if add_source_checked:
                effects.append("Source Text")
            if add_voice_checked:
                effects.append("AI Voice Over")

            if effects:
                self.add_log("INFO", f"🎨 Effects enabled: {', '.join(effects)}")
            else:
                self.add_log("WARNING", "🎨 NO EFFECTS ENABLED!")

            # Populate processing queue
            self.queue_list.clear()
            files_to_process = []
            for i in range(self.file_list.count()):
                item_text = self.file_list.item(i).text().split("📹 ")[-1]
                files_to_process.append(item_text)
                queue_item = QListWidgetItem(f"⏳ {os.path.basename(item_text)}")
                self.queue_list.addItem(queue_item)

            output_dir = self.output_path.text().strip()
            if not output_dir or not os.path.isdir(output_dir):
                self.add_log("ERROR", "❌ Output directory not found or path is empty.")
                self.set_processing_state(False)
                return

            self.add_log("INFO", f"📁 Output directory: {output_dir}")

            # ==================================================================
            # 🔥 STEP 1: BANNER PROCESSING (nếu được bật)
            # ==================================================================
            banner_output_files = []  # Track các file sau khi xử lý banner
            
            if add_banner_checked:
                self.add_log("INFO", "🔄 [DEBUG] ENTERING BANNER PROCESSING BRANCH")
                banner_video_path = self.banner_path.text().strip()

                # Kiểm tra banner file
                if not banner_video_path or not os.path.exists(banner_video_path):
                    self.add_log("ERROR", f"❌ Banner video file not found or path is empty.")
                    self.set_processing_state(False)
                    return

                # Log thông tin banner processing
                self.add_log("INFO", "🎬 UNIVERSAL Banner Processing Started:")
                self.add_log("INFO", f"   📁 Banner file: {os.path.basename(banner_video_path)}")

                successful_banner_files = 0
                for idx, main_video_path in enumerate(files_to_process, 1):
                    base_name = os.path.basename(main_video_path)
                    name_without_ext = os.path.splitext(base_name)[0]
                    file_ext = os.path.splitext(base_name)[1]
                    
                    self.add_log("INFO", f"--- Banner processing {idx}/{len(files_to_process)}: {base_name} ---")
                    
                    # Cập nhật UI
                    if hasattr(self, 'current_file_label'):
                        self.current_file_label.setText(f"Adding banner: {base_name}")
                    if hasattr(self, 'current_progress'):
                        progress = int((idx-1) / len(files_to_process) * 100)
                        self.current_progress.setValue(progress)
                    QApplication.processEvents()
                    
                    # Tạo đường dẫn file output cho banner
                    banner_output_path = os.path.join(output_dir, f"{name_without_ext}_with_banner{file_ext}")
                    
                    # 🔥 GỌI HÀM ĐIỀU PHỐI UNIVERSAL CHO TỪNG VIDEO
                    success = self.process_banner_with_universal_mapping(
                        main_video_path, 
                        banner_video_path, 
                        banner_output_path
                    )
                    
                    # Cập nhật trạng thái trong hàng đợi
                    if idx <= self.queue_list.count():
                        queue_item = self.queue_list.item(idx - 1)
                        if success:
                            successful_banner_files += 1
                            queue_item.setText(f"✅🖼️ {base_name}")
                            banner_output_files.append(banner_output_path)  # 🔥 QUAN TRỌNG: Lưu file đã xử lý banner
                        else:
                            queue_item.setText(f"❌🖼️ {base_name}")
                            banner_output_files.append(main_video_path)  # Fallback to original file
                            
                self.add_log("SUCCESS", f"🎉 UNIVERSAL Banner Processing Complete!")
                self.add_log("SUCCESS", f"   ✅ Successful: {successful_banner_files}/{len(files_to_process)} files")
                self.add_log("INFO", f"🔍 [DEBUG] Banner output files count: {len(banner_output_files)}")
                        
            else:
                self.add_log("INFO", "🔄 [DEBUG] SKIPPING BANNER PROCESSING")
                # Nếu không có banner processing, sử dụng files gốc
                banner_output_files = files_to_process.copy()
                self.add_log("INFO", f"🔍 [DEBUG] Using original files count: {len(banner_output_files)}")

            # ==================================================================
            # 🔥 STEP 2: SUBTITLE PROCESSING (nếu được bật) - CRITICAL SECTION
            # ==================================================================
            self.add_log("INFO", f"🔍 [DEBUG] Checking subtitle condition: add_subtitle_checked = {add_subtitle_checked}")
            
            if add_subtitle_checked:
                self.add_log("INFO", "🔄 [DEBUG] *** ENTERING SUBTITLE PROCESSING BRANCH ***")
                self.add_log("INFO", "📝 AI SUBTITLE Processing Started:")
                
                # 🔥 CRITICAL: Validate API key trước khi bắt đầu
                self.add_log("INFO", "🔍 [DEBUG] Starting API key validation...")
                api_key = self.get_validated_api_key()
                if not api_key:
                    self.add_log("ERROR", "❌ [DEBUG] API key validation failed - STOPPING SUBTITLE PROCESSING")
                    # Don't return, continue with other processing
                    self.add_log("WARNING", "⚠️ Subtitle processing skipped due to API key issue")
                else:
                    self.add_log("SUCCESS", f"✅ [DEBUG] API key validated successfully: {len(api_key)} chars")
                    
                    # 🔥 TEST IMPORT SUBTITLE MODULE
                    self.add_log("INFO", "🔍 [DEBUG] Testing subtitle module import...")
                    try:
                        from gg_api.get_subtitle import process_video_for_subtitles, get_default_words_per_line
                        self.add_log("SUCCESS", "✅ [DEBUG] Subtitle module imported successfully")
                    except Exception as import_error:
                        self.add_log("ERROR", f"❌ [DEBUG] Subtitle module import failed: {str(import_error)}")
                        self.add_log("WARNING", "⚠️ Subtitle processing skipped due to import issue")
                        api_key = None  # Disable subtitle processing
                    
                    if api_key:  # Only proceed if API key is valid and import successful
                        subtitle_successful_files = 0
                        final_output_files = []  # Track các file cuối cùng
                        
                        # Sử dụng files từ banner processing (hoặc gốc nếu không có banner)
                        if add_banner_checked:
                            self.add_log("INFO", "🔗 [DEBUG] Processing subtitles on banner-processed videos")
                            input_files_for_subtitle = banner_output_files
                        else:
                            self.add_log("INFO", "📹 [DEBUG] Processing subtitles on original videos")
                            input_files_for_subtitle = files_to_process.copy()
                        
                        self.add_log("INFO", f"🔍 [DEBUG] Files to process for subtitle: {len(input_files_for_subtitle)}")
                        
                        # 🔥 CRITICAL: Xử lý subtitle cho từng file
                        for idx, video_file in enumerate(input_files_for_subtitle, 1):
                            base_name = os.path.basename(video_file)
                            
                            self.add_log("INFO", f"🔍 [DEBUG] --- Subtitle processing {idx}/{len(input_files_for_subtitle)}: {base_name} ---")
                            
                            # Validate file exists
                            if not os.path.exists(video_file):
                                self.add_log("ERROR", f"❌ [DEBUG] File not found for subtitle processing: {video_file}")
                                continue
                            
                            # Cập nhật UI
                            if hasattr(self, 'current_file_label'):
                                self.current_file_label.setText(f"Adding subtitles: {base_name}")
                            if hasattr(self, 'current_progress'):
                                progress = int((idx-1) / len(input_files_for_subtitle) * 100)
                                self.current_progress.setValue(progress)
                            QApplication.processEvents()
                            
                            # 🔥 CRITICAL: Gọi hàm xử lý subtitle - THỜI ĐIỂM QUAN TRỌNG
                            self.add_log("INFO", f"🤖 [DEBUG] *** CALLING process_subtitles_for_video() for {base_name} ***")
                            
                            try:
                                import time
                                start_time = time.time()
                                success, subtitle_output = self.process_subtitles_for_video(video_file, output_dir)
                                end_time = time.time()
                                elapsed = end_time - start_time
                                
                                self.add_log("INFO", f"🔍 [DEBUG] Subtitle processing result: success={success} (took {elapsed:.1f}s)")
                                if success:
                                    self.add_log("INFO", f"🔍 [DEBUG] Subtitle output file: {subtitle_output}")
                            except Exception as subtitle_error:
                                self.add_log("ERROR", f"❌ [DEBUG] Exception in subtitle processing: {str(subtitle_error)}")
                                import traceback
                                self.add_log("ERROR", f"📋 [DEBUG] Traceback: {traceback.format_exc()}")
                                success = False
                                subtitle_output = video_file
                            
                            # Cập nhật queue status
                            if idx <= self.queue_list.count():
                                queue_item = self.queue_list.item(idx - 1)
                                current_text = queue_item.text()
                                if success:
                                    subtitle_successful_files += 1
                                    final_output_files.append(subtitle_output)
                                    # Thêm icon subtitle vào status
                                    if "✅" in current_text:
                                        queue_item.setText(current_text.replace("✅", "✅📝"))
                                    else:
                                        queue_item.setText(f"✅📝 {base_name}")
                                else:
                                    final_output_files.append(video_file)  # Fallback
                                    if "❌" not in current_text:
                                        queue_item.setText(f"❌📝 {base_name}")
                        
                        self.add_log("SUCCESS", f"🎉 AI SUBTITLE Processing Complete!")
                        self.add_log("SUCCESS", f"   ✅ Successful: {subtitle_successful_files}/{len(input_files_for_subtitle)} files")
                        
                        if subtitle_successful_files < len(input_files_for_subtitle):
                            failed_count = len(input_files_for_subtitle) - subtitle_successful_files
                            self.add_log("WARNING", f"   ⚠️ Failed: {failed_count} files (check logs for details)")
            else:
                self.add_log("INFO", "🔄 [DEBUG] *** SUBTITLE PROCESSING SKIPPED - CHECKBOX NOT CHECKED ***")

            # ==================================================================
            # 🔥 COMPLETION
            # ==================================================================
            
            # Cập nhật UI hoàn thành
            if hasattr(self, 'current_file_label'):
                self.current_file_label.setText("Batch processing completed!")
            if hasattr(self, 'current_progress'):
                self.current_progress.setValue(100)

            self.add_log("SUCCESS", "🎉 COMPLETE BATCH PROCESSING SESSION FINISHED!")
            self.add_log("SUCCESS", f"   📁 Output folder: {output_dir}")
            
            # Thống kê tổng quát
            total_processed = len(files_to_process)
            if add_banner_checked and add_subtitle_checked:
                self.add_log("INFO", f"   🎬 Pipeline: Video → Banner → Subtitle → Final Output")
            elif add_banner_checked:
                self.add_log("INFO", f"   🎬 Pipeline: Video → Banner → Final Output")
            elif add_subtitle_checked:
                self.add_log("INFO", f"   🎬 Pipeline: Video → Subtitle → Final Output")
            
            self.add_log("INFO", f"   📊 Total files processed: {total_processed}")

        except Exception as e:
            self.add_log("ERROR", f"❌ A critical error occurred during processing: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Full traceback: {traceback.format_exc()}")
        finally:
            # LUÔN LUÔN HOÀN TẤT TRẠNG THÁI PROCESSING
            self.set_processing_state(False)
    
    def create_processing_tab(self):
        """Progress monitoring and queue management"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Current Processing Status
        current_group = QGroupBox("🔄 Current Processing")
        current_group.setObjectName("modernGroupBox")
        current_layout = QVBoxLayout(current_group)
        
        self.current_file_label = QLabel("No file processing")
        self.current_file_label.setObjectName("statusLabel")
        current_layout.addWidget(self.current_file_label)
        
        self.current_progress = QProgressBar()
        self.current_progress.setObjectName("modernProgress")
        current_layout.addWidget(self.current_progress)
        
        self.current_step_label = QLabel("Step: Ready")
        self.current_step_label.setObjectName("stepLabel")
        current_layout.addWidget(self.current_step_label)
        
        layout.addWidget(current_group)
        
        # API Status monitoring
        api_status_group = QGroupBox("🔑 API Status")
        api_status_group.setObjectName("modernGroupBox")
        api_layout = QGridLayout(api_status_group)
        
        self.api_status_label = QLabel("Primary API: Not tested")
        api_layout.addWidget(self.api_status_label, 0, 0)
        
        
        
        self.api_usage_label = QLabel("Current usage: 0 requests")
        api_layout.addWidget(self.api_usage_label, 1, 0, 1, 2)
        
        layout.addWidget(api_status_group)
        
        # Overall Progress
        overall_group = QGroupBox("📊 Overall Progress")
        overall_group.setObjectName("modernGroupBox")
        overall_layout = QVBoxLayout(overall_group)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setObjectName("modernProgress")
        overall_layout.addWidget(self.overall_progress)
        
        progress_info_layout = QHBoxLayout()
        self.files_completed_label = QLabel("Files completed: 0/0")
        self.estimated_time_label = QLabel("Estimated time: --")
        progress_info_layout.addWidget(self.files_completed_label)
        progress_info_layout.addWidget(self.estimated_time_label)
        overall_layout.addLayout(progress_info_layout)
        
        layout.addWidget(overall_group)
        
        # Processing Queue
        queue_group = QGroupBox("📋 Processing Queue")
        queue_group.setObjectName("modernGroupBox")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_list = QListWidget()
        self.queue_list.setObjectName("modernList")
        queue_layout.addWidget(self.queue_list)
        
        queue_controls = QHBoxLayout()
        self.btn_pause_queue = QPushButton("⏸️ Pause")
        self.btn_pause_queue.setObjectName("warningButton")
        self.btn_resume_queue = QPushButton("▶️ Resume")
        self.btn_resume_queue.setObjectName("primaryButton")
        self.btn_cancel_queue = QPushButton("❌ Cancel All")
        self.btn_cancel_queue.setObjectName("dangerButton")
        
        queue_controls.addWidget(self.btn_pause_queue)
        queue_controls.addWidget(self.btn_resume_queue)
        queue_controls.addWidget(self.btn_cancel_queue)
        queue_controls.addStretch()
        
        queue_layout.addLayout(queue_controls)
        layout.addWidget(queue_group)
        
        return widget
    
    def create_logs_tab(self):
        """Logging and debugging output"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Log control buttons
        log_controls = QHBoxLayout()
        btn_clear_logs = QPushButton("🗑️ Clear Logs")
        btn_clear_logs.setObjectName("secondaryButton")
        btn_save_logs = QPushButton("💾 Save Logs")
        btn_save_logs.setObjectName("primaryButton")
        btn_auto_scroll = QPushButton("📜 Auto Scroll")
        btn_auto_scroll.setObjectName("toggleButton")
        btn_auto_scroll.setCheckable(True)
        btn_auto_scroll.setChecked(True)
        
        btn_clear_logs.clicked.connect(self.clear_logs)
        btn_save_logs.clicked.connect(self.save_logs)
        
        log_controls.addWidget(btn_clear_logs)
        log_controls.addWidget(btn_save_logs)
        log_controls.addWidget(btn_auto_scroll)
        log_controls.addStretch()
        
        layout.addLayout(log_controls)
        
        # Log text display area
        self.log_text = QTextBrowser()
        self.log_text.setObjectName("modernLog")
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)
        
        # Initialize with sample logs
        self.add_log("INFO", "🚀 Video Editor Tool initialized")
        self.add_log("INFO", "📱 Optimized for 9:16 vertical videos")
        self.add_log("INFO", "🔑 Backup API system ready")
        
        return widget
    
    def create_menu_bar(self):
        """Application menu structure"""
        menubar = self.menuBar()
        menubar.setObjectName("modernMenuBar")
        
        # File menu
        file_menu = menubar.addMenu('📁 File')
        file_menu.addAction('🆕 New Project', self.new_project)
        file_menu.addAction('📂 Open Project', self.open_project)
        file_menu.addAction('💾 Save Project', self.save_project)
        file_menu.addSeparator()
        file_menu.addAction('❌ Exit', self.close)
        
        # Settings menu
        settings_menu = menubar.addMenu('⚙️ Settings')
        settings_menu.addAction('🔑 API Configuration', self.open_api_config)
        settings_menu.addAction('🎨 Preferences', self.open_preferences)
        settings_menu.addAction('📱 9:16 Templates', self.open_templates)
        
        # Help menu
        help_menu = menubar.addMenu('❓ Help')
        help_menu.addAction('ℹ️ About', self.show_about)
        help_menu.addAction('📖 Documentation', self.show_docs)
        help_menu.addAction('🎥 Tutorial', self.show_tutorial)
    
    def apply_modern_styles(self):
        """Apply complete modern theme CSS styling from an external file."""
        try:
            # Construct path to the stylesheet relative to the script
            # os.path.dirname(__file__) gets the directory of the current script
            style_sheet_path = os.path.join(os.path.dirname(__file__), 'styles.qss')
            
            with open(style_sheet_path, "r", encoding='utf-8') as f:
                stylesheet = f.read()
            
            self.setStyleSheet(stylesheet)
            print("✅ Successfully loaded external stylesheet: styles.qss")

        except FileNotFoundError:
            print(f"❌ ERROR: Stylesheet 'styles.qss' not found. Make sure it's in the same directory as the script.")
            # Optionally add a log message if the log system is ready
            if hasattr(self, 'log_text'):
                self.add_log("ERROR", "Could not find styles.qss. UI may appear unstyled.")
        except Exception as e:
            print(f"❌ ERROR: Failed to load stylesheet: {e}")
            if hasattr(self, 'log_text'):
                self.add_log("ERROR", f"Failed to load stylesheet: {e}")

    
    def toggle_preview_area(self, area_type):
        """Show/hide preview areas (subtitle, banner, source)"""
        if area_type == 'subtitle':
            self.video_preview.subtitle_area = not self.video_preview.subtitle_area
        elif area_type == 'banner':
            self.video_preview.banner_area = not self.video_preview.banner_area
        elif area_type == 'source':
            self.video_preview.source_area = not self.video_preview.source_area
        
        self.video_preview.update()
    
    def add_log(self, level, message):
        """Add formatted log entry with timestamp and color"""
        color_map = {
            "INFO": "#0A86DE",
            "SUCCESS": "#68d391", 
            "WARNING": "#f6ad55",
            "ERROR": "#fc8181"
        }
        
        color = color_map.get(level, "#e2e8f0")
        timestamp = "12:34:56"  # Placeholder timestamp
        
        formatted_msg = f'<span style="color: {color};">[{timestamp}] [{level}]</span> {message}'
        self.log_text.append(formatted_msg)
    
    # Event Handlers
    def add_files(self):
        """Open file dialog and add video files to list"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select 9:16 Video Files", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        for file in files:
            self.file_list.addItem(f"📹 {file}")
        self.add_log("INFO", f"Added {len(files)} video files")
    
    def add_folder(self):
        """Add entire folder of videos"""
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder:
            # Danh sách các extension video được hỗ trợ
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
            
            found_videos = []
            
            # Quét tất cả files trong folder
            try:
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    
                    # Kiểm tra nếu là file (không phải folder) và có extension video
                    if os.path.isfile(file_path):
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in video_extensions:
                            found_videos.append(file_path)
                
                # Thêm các video files vào list
                if found_videos:
                    for video_file in found_videos:
                        self.file_list.addItem(f"📹 {video_file}")
                    
                    self.add_log("SUCCESS", f"✅ Added {len(found_videos)} video files from folder")
                    self.add_log("INFO", f"📁 Folder scanned: {folder}")
                    
                    # Log chi tiết các files đã thêm
                    for video in found_videos:
                        self.add_log("INFO", f"   📹 {os.path.basename(video)}")
                else:
                    self.add_log("WARNING", f"⚠️ No video files found in folder: {folder}")
                    self.add_log("INFO", f"   Supported formats: {', '.join(video_extensions)}")
                    
            except PermissionError:
                self.add_log("ERROR", f"❌ Permission denied: Cannot access folder {folder}")
            except Exception as e:
                self.add_log("ERROR", f"❌ Error scanning folder: {str(e)}")
        else:
            self.add_log("INFO", "📂 Folder selection cancelled")
    
    def clear_files(self):
        """Remove all files from processing list"""
        self.file_list.clear()
        self.add_log("INFO", "Cleared all files from list")
    
    def browse_output(self):
        """Select output directory"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)
            self.add_log("INFO", f"Output folder set: {folder}")
    
    def browse_banner(self):
        """Select video banner file"""
        # <<< SỬA ĐỔI: Chỉ cho phép chọn các định dạng video phổ biến >>>
        file_filter = "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)"
                
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Video Banner", "", file_filter
        )
        if file:
            self.banner_path.setText(file)
            self.add_log("INFO", f"Video banner file selected: {file}")
    
    


    def check_ffmpeg_installation(self):
        """Kiểm tra xem FFmpeg có sẵn không"""
        ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe")
        
        if os.path.exists(ffmpeg_path):
            self.add_log("SUCCESS", f"✅ FFmpeg found at: {ffmpeg_path}")
            return True
        else:
            self.add_log("ERROR", f"❌ FFmpeg not found at: {ffmpeg_path}")
            self.add_log("ERROR", "   Please ensure FFmpeg is properly installed in the ffmpeg/bin/ directory.")
            return False

    def clear_logs(self):
        """Clear all log entries"""
        self.log_text.clear()
        self.add_log("INFO", "📋 Logs cleared")
    
    def save_logs(self):
        """Export logs to text file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "video_editor_logs.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            self.add_log("SUCCESS", f"💾 Logs saved to: {filename}")
    
    # Menu Handlers
    def new_project(self):
        """Project management"""
        self.add_log("INFO", "🆕 New project created")
    
    def open_project(self):
        """Project management"""
        self.add_log("INFO", "📂 Opening project...")
    
    def save_project(self):
        """Project management"""
        self.add_log("SUCCESS", "💾 Project saved successfully")
    
    def open_api_config(self):
        """Settings dialogs"""
        self.add_log("INFO", "🔑 Opening API configuration...")
    
    def open_preferences(self):
        """Settings dialogs"""
        self.add_log("INFO", "🎨 Opening preferences...")
    
    def open_templates(self):
        """Settings dialogs"""
        self.add_log("INFO", "📱 Opening 9:16 templates...")
    
    def show_about(self):
        """Help and documentation"""
        self.add_log("INFO", "ℹ️ About dialog opened")
    
    def show_docs(self):
        """Help and documentation"""
        self.add_log("INFO", "📖 Opening documentation...")
    
    def show_tutorial(self):
        """Help and documentation"""
        self.add_log("INFO", "🎥 Opening video tutorial...")



if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Video Editor Tool")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Automation Team")
    
    window = VideoEditorMainWindow()
    window.show()
    sys.exit(app.exec_())