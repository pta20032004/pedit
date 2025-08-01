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
# Thêm vào phần import ở đầu file gui_demo.py
import time
from typing import Tuple
from PyQt5.QtCore import QThread, pyqtSignal

# THÊM VÀO ĐẦU FILE gui_demo.py - SAU PHẦN IMPORT HIỆN TẠI
try:
    from source_text import (
        process_source_text_batch,
        extract_source_from_filename,
        validate_font_file,
        get_plus_jakarta_font_path,
        add_source_text_to_video
    )
    SOURCE_TEXT_AVAILABLE = True
    print("✅ Source text module loaded successfully")
except ImportError as e:
    SOURCE_TEXT_AVAILABLE = False
    print("f⚠️ Warning: Source text module not found: {str(e)}")
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
                            QListWidgetItem, QHeaderView, QTableWidget, QTableWidgetItem,
                            QRadioButton)
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

class SingleAPIWorker(QThread):
    """
    🔥 NEW: Isolated worker for single API processing
    Mỗi worker hoạt động hoàn toàn độc lập với API key riêng
    """
    
    # Signals for communication
    worker_log = pyqtSignal(str, str, str)  # (worker_id, level, message)
    worker_progress = pyqtSignal(str, int)  # (worker_id, progress_percent)
    worker_finished = pyqtSignal(str, bool, str)  # (worker_id, success, result_path)
    worker_started = pyqtSignal(str, str)  # (worker_id, video_filename)
    
    def __init__(self, worker_id: str, api_key: str, main_window):
        super().__init__()
        self.worker_id = worker_id
        self.api_key = api_key
        self.main_window = main_window
        self.current_video = None
        self.current_settings = None
        self.should_stop = False
        self.is_busy = False
        
        # Private log method for this worker
        self._log_prefix = f"[API-{worker_id}]"
    
    def is_available(self) -> bool:
        """Check if worker is available for new task"""
        return not self.is_busy and not self.isRunning()
    
    def assign_video(self, video_path: str, output_dir: str, settings: dict):
        """Assign a video for processing"""
        if not self.is_available():
            return False
            
        self.current_video = video_path
        self.output_dir = output_dir
        self.current_settings = settings.copy()  # Deep copy to avoid conflicts
        return True
    
    def stop_processing(self):
        """Stop current processing"""
        self.should_stop = True
    
    def _log(self, level: str, message: str):
        """Private logging method for this worker"""
        full_message = f"{self._log_prefix} {message}"
        self.worker_log.emit(self.worker_id, level, full_message)
    
    def run(self):
        """
        Main processing loop - COMPLETELY ISOLATED
        """
        if not self.current_video or not self.api_key:
            self._log("ERROR", "❌ No video assigned or API key missing")
            self.worker_finished.emit(self.worker_id, False, "")
            return
        
        self.is_busy = True
        self.should_stop = False
        
        try:
            video_name = os.path.basename(self.current_video)
            self.worker_started.emit(self.worker_id, video_name)
            self._log("INFO", f"🎬 Starting processing: {video_name}")
            
            # STEP 0: Progress 10%
            self.worker_progress.emit(self.worker_id, 10)
            
            # STEP 1: Process with isolated API key
            success, result_path = self._process_video_isolated(
                self.current_video, 
                self.output_dir, 
                self.current_settings
            )
            
            # STEP 2: Progress 100%
            self.worker_progress.emit(self.worker_id, 100)
            
            if success:
                self._log("SUCCESS", f"✅ Completed: {video_name}")
            else:
                self._log("ERROR", f"❌ Failed: {video_name}")
            
            self.worker_finished.emit(self.worker_id, success, result_path)
            
        except Exception as e:
            self._log("ERROR", f"❌ Worker exception: {str(e)}")
            self.worker_finished.emit(self.worker_id, False, "")
        finally:
            self.is_busy = False
    
    def _process_video_isolated(self, video_path: str, output_dir: str, settings: dict) -> Tuple[bool, str]:
        """
        🔥 ISOLATED VIDEO PROCESSING with dedicated API key
        No shared resources with other workers
        """
        try:
            base_name = os.path.basename(video_path)
            name_without_ext = os.path.splitext(base_name)[0]
            file_ext = os.path.splitext(base_name)[1]
            
            # Final output path
            final_output = os.path.join(output_dir, f"{name_without_ext}_processed{file_ext}")
            current_video = video_path
            temp_files_to_delete = []
            
            # PROGRESS: 20%
            self.worker_progress.emit(self.worker_id, 20)
            
            # STEP 1: Subtitles (ISOLATED API CALL)
            if settings.get('add_subtitle', False):
                self._log("INFO", f"📝 Adding subtitles with API key {self.api_key[:10]}...")
                
                success, subtitle_video = self._process_subtitles_isolated(
                    current_video, output_dir, settings
                )
                
                if success and subtitle_video:
                    current_video = subtitle_video
                    temp_files_to_delete.append(subtitle_video)
                    self._log("SUCCESS", "✅ Subtitles added")
                else:
                    self._log("ERROR", "❌ Subtitle processing failed")
                    return False, ""
            
            # PROGRESS: 60%
            self.worker_progress.emit(self.worker_id, 60)
            
            # STEP 2: Banner (if enabled)
            if settings.get('add_banner', False):
                self._log("INFO", f"🖼️ Adding banner...")
                
                banner_output = os.path.join(output_dir, f"{name_without_ext}_with_banner{file_ext}")
                success = self._process_banner_isolated(current_video, settings, banner_output)
                
                if success:
                    current_video = banner_output
                    temp_files_to_delete.append(banner_output)
                    self._log("SUCCESS", "✅ Banner added")
                else:
                    self._log("ERROR", "❌ Banner processing failed")
                    return False, ""
            
            # PROGRESS: 80%
            self.worker_progress.emit(self.worker_id, 80)
            
            # STEP 3: Source text (if enabled)
            if settings.get('add_source', False):
                self._log("INFO", f"📎 Adding source text...")
                
                success = self._process_source_text_isolated(
                    current_video, final_output, base_name, settings
                )
                
                if success:
                    self._log("SUCCESS", f"✅ Source text added")
                else:
                    self._log("ERROR", f"❌ Source text failed")
                    return False, ""
            else:
                # No source text - copy current video to final
                import shutil
                shutil.copy2(current_video, final_output)
            
            # PROGRESS: 95%
            self.worker_progress.emit(self.worker_id, 95)
            
            # CLEANUP
            for temp_file in temp_files_to_delete:
                try:
                    if os.path.exists(temp_file) and temp_file != final_output:
                        os.remove(temp_file)
                except:
                    pass
            
            return True, final_output
            
        except Exception as e:
            self._log("ERROR", f"❌ Isolated processing error: {str(e)}")
            return False, ""
    
    def _process_subtitles_isolated(self, video_path: str, output_dir: str, settings: dict) -> Tuple[bool, str]:
        """ISOLATED subtitle processing with ENHANCED error handling"""
        try:
            base_name = os.path.basename(video_path)
            name_without_ext = os.path.splitext(base_name)[0]
            file_ext = os.path.splitext(base_name)[1]
            
            source_lang = settings.get('source_lang', '🔍 Auto Detect')
            target_lang = settings.get('target_lang', '🇺🇸 English (US)')
            
            self._log("INFO", f"🌐 Languages: {source_lang} → {target_lang}")
            
            # 🔥 ENHANCED: Retry logic with different approaches
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    from gg_api.get_subtitle import process_video_for_subtitles
                    
                    success, srt_content, message = process_video_for_subtitles(
                        video_path=video_path,
                        api_key=self.api_key,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        words_per_line=8,
                        ffmpeg_path=None,
                        log_callback=lambda level, msg: self._log(level, msg)
                    )
                    
                    if success and srt_content:
                        break  # Success, exit retry loop
                        
                    if "403" in str(message) or "permission" in str(message).lower():
                        self._log("WARNING", f"🔄 Attempt {attempt+1}: Permission error, trying different approach...")
                        # Try with simpler settings
                        if attempt == 1:
                            source_lang = "🇺🇸 English (US)"  # Force English
                        elif attempt == 2:
                            target_lang = "🇺🇸 English (US)"  # Force target English
                    else:
                        self._log("ERROR", f"🔄 Attempt {attempt+1}: {message}")
                        
                except Exception as e:
                    self._log("ERROR", f"🔄 Attempt {attempt+1} exception: {str(e)}")
                    
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # Wait before retry
            
            if not success:
                self._log("ERROR", f"❌ All {max_retries} attempts failed")
                return False, ""
            
            # Continue with SRT processing...
            srt_temp_path = os.path.join(output_dir, f"{name_without_ext}_subtitle.srt")
            with open(srt_temp_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            output_video_path = os.path.join(output_dir, f"{name_without_ext}_with_subtitles{file_ext}")
            
            subtitle_success = self.main_window.add_subtitles_to_video(
                input_video=video_path,
                srt_file=srt_temp_path,
                output_video=output_video_path
            )
            
            if subtitle_success:
                return True, output_video_path
            else:
                return False, ""
                
        except Exception as e:
            self._log("ERROR", f"❌ Isolated subtitle error: {str(e)}")
            return False, ""
    
    def _process_banner_isolated(self, video_path: str, settings: dict, output_path: str) -> bool:
        """ISOLATED banner processing"""
        try:
            # Use main window's banner processing (shared but thread-safe)
            return self.main_window.process_banner_with_universal_mapping(
                video_path, 
                settings.get('banner_path', ''),
                output_path
            )
        except Exception as e:
            self._log("ERROR", f"❌ Isolated banner error: {str(e)}")
            return False
    
    def _process_source_text_isolated(self, input_video: str, output_video: str, 
                                    base_name: str, settings: dict) -> bool:
        """ISOLATED source text processing"""
        try:
            if not SOURCE_TEXT_AVAILABLE:
                return False
            
            # Get video dimensions
            video_width, video_height = self.main_window.get_video_dimensions(input_video)
            if not video_width or not video_height:
                return False
            
            # Calculate parameters
            source_params = self.main_window.calculate_universal_source_params(video_width, video_height)
            if not source_params:
                return False
            
            # Determine source text
            if settings.get('source_mode_filename', False):
                from source_text import extract_source_from_filename
                source_text = extract_source_from_filename(base_name)
            else:
                source_text = settings.get('source_text', '@YourChannel')
            
            # Add source text
            from source_text import add_source_text_to_video
            success, message = add_source_text_to_video(
                input_video_path=input_video,
                output_video_path=output_video,
                source_text=source_text,
                position_x=source_params['position_x'],
                position_y=source_params['position_y'],
                font_size=source_params['font_size'],
                font_color=source_params['font_color']
            )
            
            return success
            
        except Exception as e:
            self._log("ERROR", f"❌ Isolated source text error: {str(e)}")
            return False

    def wait(self):
        """Wait for worker to finish"""
        if self.isRunning():
            super().wait()

    def reset_for_next_video(self):
        """Reset worker state for next video"""
        self.current_video = None
        self.current_settings = None
        self.is_busy = False


class ProcessingWorker(QThread):
    """🔥 FINAL VERSION: True parallel processing with proper synchronization"""
    
    progress_updated = pyqtSignal(int)
    current_file_updated = pyqtSignal(str)
    current_step_updated = pyqtSignal(str)
    log_message = pyqtSignal(str, str)
    queue_updated = pyqtSignal(int, str)
    processing_finished = pyqtSignal(bool)
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.files_to_process = []
        self.output_dir = ""
        self.settings = {}
        self.should_stop = False
        
        # 🔥 FIXED: Proper thread management
        self.api_worker_1 = None
        self.api_worker_2 = None
        self.worker1_thread = None
        self.worker2_thread = None
        self.completed_videos = 0
        self.total_videos = 0
        self.progress_lock = threading.Lock()  # Thread safety
        
    def setup_processing(self, files_to_process, output_dir, settings):
        """Setup processing parameters"""
        self.files_to_process = files_to_process
        self.output_dir = output_dir
        self.settings = settings
        self.should_stop = False
        self.completed_videos = 0
        self.total_videos = len(files_to_process)
        
    def stop_processing(self):
        """Stop all workers gracefully"""
        self.should_stop = True
        
        if self.api_worker_1 and self.api_worker_1.isRunning():
            self.api_worker_1.stop_processing()
            self.api_worker_1.wait(3000)
        
        if self.api_worker_2 and self.api_worker_2.isRunning():
            self.api_worker_2.stop_processing()
            self.api_worker_2.wait(3000)
    
    def setup_isolated_workers(self, api_key_1: str, api_key_2: str):
        """Setup 2 completely isolated API workers"""
        try:
            self.api_worker_1 = SingleAPIWorker("Worker-1", api_key_1, self.parent)
            self.api_worker_2 = SingleAPIWorker("Worker-2", api_key_2, self.parent)
            
            # Connect signals but handle progress differently
            self.api_worker_1.worker_log.connect(self.on_worker_log)
            self.api_worker_1.worker_finished.connect(self.on_worker_finished)
            
            self.api_worker_2.worker_log.connect(self.on_worker_log)
            self.api_worker_2.worker_finished.connect(self.on_worker_finished)
            
            self.log_message.emit("SUCCESS", f"✅ ISOLATED workers created:")
            self.log_message.emit("INFO", f"   🔑 Worker-1: {api_key_1[:10]}...{api_key_1[-4:]}")
            self.log_message.emit("INFO", f"   🔑 Worker-2: {api_key_2[:10]}...{api_key_2[-4:]}")
            
            return True
            
        except Exception as e:
            self.log_message.emit("ERROR", f"❌ Failed to create isolated workers: {str(e)}")
            return False
    
    def on_worker_log(self, worker_id: str, level: str, message: str):
        """Handle log messages from workers"""
        self.log_message.emit(level, message)
    
    def on_worker_finished(self, worker_id: str, success: bool, result_path: str):
        """Handle worker completion with thread safety"""
        with self.progress_lock:
            self.completed_videos += 1
            
            status = "✅" if success else "❌"
            self.log_message.emit("INFO", f"{status} {worker_id} completed. Total: {self.completed_videos}/{self.total_videos}")
            
            # Update overall progress
            overall_progress = int((self.completed_videos / self.total_videos) * 100)
            self.progress_updated.emit(overall_progress)
    
    def run(self):
        """🔥 FINAL: True parallel processing"""
        try:
            # Setup workers
            api_key_1, api_key_2 = self.parent.get_dual_api_keys()
            if not self.setup_isolated_workers(api_key_1, api_key_2):
                return
            
            # 🔥 STRATEGY: Split videos evenly
            if len(self.files_to_process) == 1:
                # Single video - use worker 1 only
                worker1_videos = self.files_to_process
                worker2_videos = []
            else:
                # Multiple videos - distribute evenly
                mid_point = len(self.files_to_process) // 2
                worker1_videos = self.files_to_process[:mid_point]
                worker2_videos = self.files_to_process[mid_point:]
            
            self.log_message.emit("INFO", f"🔄 TRUE PARALLEL SPLIT:")
            self.log_message.emit("INFO", f"   Worker-1: {len(worker1_videos)} videos")
            self.log_message.emit("INFO", f"   Worker-2: {len(worker2_videos)} videos")
            
            # 🔥 Start both workers in TRUE parallel threads
            self.worker1_thread = threading.Thread(
                target=self._process_video_list,
                args=(self.api_worker_1, worker1_videos, "Worker-1"),
                daemon=True
            )
            
            if worker2_videos:  # Only start worker 2 if it has videos
                self.worker2_thread = threading.Thread(
                    target=self._process_video_list,
                    args=(self.api_worker_2, worker2_videos, "Worker-2"),
                    daemon=True
                )
            
            # 🔥 START BOTH SIMULTANEOUSLY
            self.worker1_thread.start()
            if self.worker2_thread:
                self.worker2_thread.start()
            
            self.log_message.emit("SUCCESS", "🚀 Both workers started in TRUE PARALLEL mode!")
            
            # 🔥 WAIT FOR BOTH TO COMPLETE
            self.worker1_thread.join()
            if self.worker2_thread:
                self.worker2_thread.join()
            
            # Final status
            self.log_message.emit("SUCCESS", f"🎉 TRUE PARALLEL processing completed!")
            self.processing_finished.emit(True)
            
        except Exception as e:
            self.log_message.emit("ERROR", f"❌ Parallel coordinator error: {str(e)}")
            self.processing_finished.emit(False)
    
    def _process_video_list(self, worker, video_list, worker_name):
        """🔥 ENHANCED: Process list with detailed timing"""
        try:
            import time
            
            for i, video_path in enumerate(video_list):
                if self.should_stop:
                    break
                
                start_time = time.time()
                video_name = os.path.basename(video_path)
                
                self.log_message.emit("INFO", f"📹 {worker_name} starting: {video_name} ({i+1}/{len(video_list)})")
                
                # Process video
                if worker.assign_video(video_path, self.output_dir, self.settings):
                    worker.start()
                    worker.wait()
                    
                    # Calculate timing
                    elapsed = time.time() - start_time
                    self.log_message.emit("SUCCESS", f"✅ {worker_name} completed {video_name} in {elapsed:.1f}s")
                    
                    # Reset for next video
                    worker.reset_for_next_video()
                    
                else:
                    self.log_message.emit("ERROR", f"❌ {worker_name} failed to assign: {video_name}")
                    
        except Exception as e:
            self.log_message.emit("ERROR", f"❌ {worker_name} processing error: {str(e)}")

    def reset_for_next_video(self):
        """Reset worker state for next video"""
        self.current_video = None
        self.current_settings = None
        self.is_busy = False
        self.should_stop = False




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
        
        # 🔥 TẠO WORKER THREAD
        self.processing_worker = ProcessingWorker(self)
        self.setup_worker_connections()
        
        self.init_ui()
        self.apply_modern_styles()
        
        # 🔥 THIẾT LẬP CÁC MẶC ĐỊNH SAU KHI UI ĐÃ TẠO
        self.setup_defaults()
        
        # 🔥 KIỂM TRA FFMPEG KHI KHỞI ĐỘNG
        QApplication.processEvents()  # Để UI load xong trước
        self.check_ffmpeg_installation()
    
    def setup_worker_connections(self):
        """Kết nối signals từ worker thread tới main thread"""
        self.processing_worker.progress_updated.connect(self.update_overall_progress)
        self.processing_worker.current_file_updated.connect(self.update_current_file)
        self.processing_worker.current_step_updated.connect(self.update_current_step)
        self.processing_worker.log_message.connect(self.add_log)
        self.processing_worker.queue_updated.connect(self.update_queue_item)
        self.processing_worker.processing_finished.connect(self.on_processing_finished)

    def update_overall_progress(self, progress):
        """Update overall progress bar"""
        if hasattr(self, 'overall_progress'):
            self.overall_progress.setValue(progress)
        if hasattr(self, 'current_progress'):
            self.current_progress.setValue(progress)

    def update_current_file(self, message):
        """Update current file label"""
        if hasattr(self, 'current_file_label'):
            self.current_file_label.setText(message)

    def update_current_step(self, message):
        """Update current step label"""
        if hasattr(self, 'current_step_label'):
            self.current_step_label.setText(message)

    def update_queue_item(self, index, status):
        """Update queue item status"""
        if hasattr(self, 'queue_list') and index < self.queue_list.count():
            item = self.queue_list.item(index)
            if item:
                file_name = item.text().split(" ", 1)[-1] if " " in item.text() else item.text()
                item.setText(f"{status} {file_name}")

    def on_processing_finished(self, success):
        """Called when processing is completely finished"""
        self.set_processing_state(False)
        
        if success:
            self.add_log("SUCCESS", "🎉 All processing completed successfully!")
        else:
            self.add_log("WARNING", "⚠️ Processing finished with some errors")
    
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
        """Setup default values with font validation"""
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
            
            # 3. BANNER POSITION VÀ SIZE 
            if hasattr(self, 'banner_x'):
                self.banner_x.setValue(230)  # X position
                self.add_log("INFO", f"📍 Default banner X position: 230px")
                
            if hasattr(self, 'banner_y'):
                self.banner_y.setValue(1400)  
                self.add_log("INFO", f"📍 Default banner Y position: 1400px")
                
            if hasattr(self, 'banner_height_ratio'):
                self.banner_height_ratio.setValue(0.18)  # Height ratio
                self.add_log("INFO", f"📏 Default banner height ratio: 0.18 (18% of video height)")
            
            # 4. BANNER TIMING - TỪ GIÂY 5 ĐẾN GIÂY 12
            if hasattr(self, 'banner_start_time'):
                self.banner_start_time.setValue(5)  # Bắt đầu từ giây thứ 5
                self.add_log("INFO", f"⏰ Default banner start time: 5 seconds")
                
            if hasattr(self, 'banner_end_time'):
                self.banner_end_time.setValue(12)  # Kết thúc ở giây thứ 12
                self.add_log("INFO", f"⏰ Default banner end time: 12 seconds")
            
            # 5. SUBTITLE DEFAULTS
            if hasattr(self, 'subtitle_size'):
                self.subtitle_size.setValue(60)  # Font size mặc định
                self.add_log("INFO", f"🔤 Default subtitle font size: 60px")
                
            if hasattr(self, 'subtitle_y'):
                self.subtitle_y.setValue(1400)  # Y position mặc định
                self.add_log("INFO", f"📍 Default subtitle Y position: 1400px")
                
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
            
            # 8. MẶC ĐỊNH BẬT SUBTITLE
            if hasattr(self, 'chk_add_subtitle'):
                self.chk_add_subtitle.setChecked(True)
                self.add_log("INFO", "📝 Add Subtitles enabled by default")
            
            if hasattr(self, 'chk_add_source'):
                self.chk_add_source.setChecked(True)
                self.add_log("INFO", " Add Source Text enabled by default")

            # 9. SOURCE TEXT DEFAULTS
            if hasattr(self, 'source_x'):
                self.source_x.setValue(920)
                self.add_log("INFO", f"📎 Default source X position: 50px")
                
            if hasattr(self, 'source_y'):
                self.source_y.setValue(230)
                self.add_log("INFO", f"📎 Default source Y position: 50px")
                
            if hasattr(self, 'source_font_size'):
                self.source_font_size.setValue(35)
                self.add_log("INFO", f"📎 Default source font size: 14px")
                
            if hasattr(self, 'source_font_color'):
                self.source_font_color.setCurrentText("white")
                self.add_log("INFO", f"📎 Default source font color: white")
                
            if hasattr(self, 'source_text'):
                self.source_text.setText("Social Media")
                self.add_log("INFO", f"📎 Default source text: Social Media")
                
            if hasattr(self, 'source_mode_custom'):
                self.source_mode_custom.setChecked(True)
                self.add_log("INFO", f"📎 Default source mode: Custom text")
            
            # 10. CHECK SOURCE TEXT SETUP
            self.check_source_text_setup()
            
            # 11. CẬP NHẬT PREVIEW NGAY SAU KHI SET DEFAULTS
            QApplication.processEvents()  # Đảm bảo UI đã load xong
            if hasattr(self, '_update_preview_positions'):
                self._update_preview_positions()
                self.add_log("INFO", "🔄 Preview positions updated with new defaults")
            
            # 12. TEST GUI SYNC - Đọc lại các giá trị để verify
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
            
            # 13. LOG TỔNG KẾT CÁC SETTINGS
            self.add_log("SUCCESS", "✅ All default settings applied successfully:")
            self.add_log("INFO", "   🖼️ Banner: ENABLED")
            self.add_log("INFO", "   📍 Position: (230, 1400) pixels")
            self.add_log("INFO", "   📐 Size: 18% of video height")
            self.add_log("INFO", "   ⏰ Timing: 5-12 seconds (7 seconds duration)")
            self.add_log("INFO", "   🎭 Chromakey: ENABLED (Green removal)")
            self.add_log("INFO", "   📝 Subtitle: ENABLED, 60px font, Y=1400px, White with Shadow")
            self.add_log("INFO", "   📎 Source: Custom mode, @YourChannel, (50,50), 14px, white")
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
        """UPDATED: Cập nhật preview với source text universal mapping info"""
        if not hasattr(self, 'video_preview') or self.video_preview is None:
            return

        try:
            # 🔥 Existing banner and subtitle code...
            real_banner_x = self.banner_x.value() if hasattr(self, 'banner_x') and self.banner_x is not None else 230
            real_banner_y = self.banner_y.value() if hasattr(self, 'banner_y') and self.banner_y is not None else 1400
            real_subtitle_y = self.subtitle_y.value() if hasattr(self, 'subtitle_y') and self.subtitle_y is not None else 1200
            
            # 🔥 UPDATED: Get source text values with enhanced info
            real_source_x = self.source_x.value() if hasattr(self, 'source_x') and self.source_x is not None else 50
            real_source_y = self.source_y.value() if hasattr(self, 'source_y') and self.source_y is not None else 50
            
            # Get additional info for logging
            gui_font_size = self.subtitle_size.value() if hasattr(self, 'subtitle_size') and self.subtitle_size is not None else 40
            gui_style = self.subtitle_style.currentText() if hasattr(self, 'subtitle_style') and self.subtitle_style is not None else "White with Shadow"
            source_font_size = self.source_font_size.value() if hasattr(self, 'source_font_size') and self.source_font_size is not None else 14
            source_color = self.source_font_color.currentText() if hasattr(self, 'source_font_color') and self.source_font_color is not None else "white"
            
            # Calculate banner dimensions
            banner_height_ratio = self.banner_height_ratio.value() if hasattr(self, 'banner_height_ratio') and self.banner_height_ratio is not None else 0.18
            real_banner_height = int(1920 * banner_height_ratio)
            real_banner_width = int(real_banner_height * 16/9)
            
            # Subtitle safe area
            REFERENCE_WIDTH = 1080
            BASE_LEFT_MARGIN = 90
            BASE_RIGHT_MARGIN = 130
            
            subtitle_safe_left = BASE_LEFT_MARGIN
            subtitle_safe_width = REFERENCE_WIDTH - BASE_LEFT_MARGIN - BASE_RIGHT_MARGIN
            subtitle_height = 80
            
            # Update preview
            self.video_preview.update_from_real_coordinates('banner', real_banner_x, real_banner_y, real_banner_width, real_banner_height)
            self.video_preview.update_from_real_coordinates('subtitle', subtitle_safe_left, real_subtitle_y, subtitle_safe_width, subtitle_height)
            self.video_preview.update_from_real_coordinates('source', real_source_x, real_source_y)
            
            # 🔥 ENHANCED LOGGING with mapping info
            self.add_log("DEBUG", f"🔄 Preview updated with GUI values (with universal mapping info):")
            self.add_log("DEBUG", f"   📍 Banner: ({real_banner_x}, {real_banner_y}) {real_banner_width}x{real_banner_height}")
            self.add_log("DEBUG", f"   📝 Subtitle: Y={real_subtitle_y}, Font={gui_font_size}px, Style={gui_style}")
            self.add_log("DEBUG", f"   📎 Source: ({real_source_x}, {real_source_y}), Font={source_font_size}px, Color={source_color}")
            self.add_log("DEBUG", f"   💡 Note: Source text will auto-scale for different video sizes")
            
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
    def _update_api_status(self, api_number: int, status: str, message: str):
        """Update API status label"""
        status_colors = {
            "SUCCESS": "#16a34a",
            "ERROR": "#dc2626", 
            "WARNING": "#d97706",
            "INFO": "#0ea5e9",
            "TESTING": "#d97706"
        }
        color = status_colors.get(status, "#6b7280")
        
        if api_number == 1 and hasattr(self, 'api_status_label'):
            self.api_status_label.setText(f"Primary API: {message}")
            self.api_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        elif api_number == 2 and hasattr(self, 'api_status_label_2'):
            self.api_status_label_2.setText(f"Secondary API: {message}")
            self.api_status_label_2.setStyleSheet(f"color: {color}; font-weight: bold;")


    def load_api_keys_to_both_dropdowns(self):
        """Load API keys vào cả 2 dropdown"""
        if not hasattr(self, 'api_key_pool_1') or not hasattr(self, 'api_key_pool_2'):
            return

        # Clear both dropdowns
        self.api_key_pool_1.clear()
        self.api_key_pool_2.clear()
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "gg_api", "api_key.json")
            
            if not os.path.exists(json_path):
                self.api_key_pool_1.addItem("❌ api_key.json not found")
                self.api_key_pool_2.addItem("❌ api_key.json not found")
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
                            
                            # Add to both dropdowns
                            self.api_key_pool_1.addItem(display_text, api_key)
                            self.api_key_pool_2.addItem(display_text, api_key)
                            key_count += 1
            
            if key_count > 0:
                # Add headers
                self.api_key_pool_1.insertItem(0, "📊 Select Primary API Key...")
                self.api_key_pool_2.insertItem(0, "📊 Select Secondary API Key...")
                self.api_key_pool_1.setCurrentIndex(0)
                self.api_key_pool_2.setCurrentIndex(0)
                
                self.add_log("SUCCESS", f"✅ Loaded {key_count} API keys to both pools")
            else:
                self.api_key_pool_1.addItem("⚠️ No valid keys found")
                self.api_key_pool_2.addItem("⚠️ No valid keys found")
                
        except Exception as e:
            self.api_key_pool_1.addItem("❌ Error loading keys")
            self.api_key_pool_2.addItem("❌ Error loading keys")
            self.add_log("ERROR", f"Error loading API keys: {str(e)}")

    # SỬA ĐỔI 1: Hàm thiết lập các thành phần API khi khởi động
    def setup_api_components(self):
        """Initialize dual API system"""
        self.add_log("INFO", "🚀 Initializing DUAL API system...")
        QApplication.processEvents()

        # Load keys vào cả 2 dropdowns
        self.load_api_keys_to_both_dropdowns()
        
        # Set initial status
        self._update_api_status(1, "INFO", "💡 Ready - Enter key or select from pool")
        self._update_api_status(2, "INFO", "💡 Ready - Enter key or select from pool")

        self.add_log("SUCCESS", "✅ DUAL API system initialized")
        self.add_log("INFO", "📋 Tip: Use 2 different API keys for 2x faster processing!")


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
    
    def process_subtitles_for_video_with_api(self, video_path: str, output_dir: str, 
                                       api_key: str, settings: dict) -> Tuple[bool, str]:
        """
        Process subtitles using specific API key (modified version of existing function)
        """
        try:
            base_name = os.path.basename(video_path)
            name_without_ext = os.path.splitext(base_name)[0]
            file_ext = os.path.splitext(base_name)[1]
            
            source_lang = settings.get('source_lang', '🔍 Auto Detect')
            target_lang = settings.get('target_lang', '🇺🇸 English (US)')
            
            # Import and call API function with specific key
            from gg_api.get_subtitle import process_video_for_subtitles
            
            success, srt_content, message = process_video_for_subtitles(
                video_path=video_path,
                api_key=api_key,  # 🔥 Use specific API key
                source_lang=source_lang,
                target_lang=target_lang,
                words_per_line=8,
                ffmpeg_path=None,
                log_callback=self.add_log
            )
            
            if not success:
                return False, ""
            
            # Save SRT and add to video
            srt_temp_path = os.path.join(output_dir, f"{name_without_ext}_subtitle.srt")
            with open(srt_temp_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            output_video_path = os.path.join(output_dir, f"{name_without_ext}_with_subtitles{file_ext}")
            
            subtitle_success = self.add_subtitles_to_video(
                input_video=video_path,
                srt_file=srt_temp_path,
                output_video=output_video_path
            )
            
            if subtitle_success:
                return True, output_video_path
            else:
                return False, ""
                
        except Exception as e:
            self.log_message.emit("ERROR", f"❌ API-specific subtitle error: {str(e)}")
            return False, ""

    def test_single_api_key(self, api_number: int):
        """Test individual API key"""
        if api_number == 1:
            api_key = self.api_key_input.text().strip()
            btn = self.findChild(QPushButton)  # Find test button
        else:
            api_key = self.api_key_input_2.text().strip()
            btn = None
            
        if not api_key:
            self._update_api_status(api_number, "WARNING", "⚠️ API key field is empty")
            return

        # Update button and status
        if btn:
            btn.setEnabled(False)
            btn.setText("🔄 Testing...")
        
        self._update_api_status(api_number, "TESTING", "🔄 Testing API key...")
        QApplication.processEvents()

        try:
            if API_TESTING_AVAILABLE:
                from gg_api.test_api import test_api_key as test_function
                results = test_function(api_key)
                
                if results and results.get("success"):
                    self._update_api_status(api_number, "SUCCESS", "✅ Valid API key")
                    self.add_log("SUCCESS", f"API {api_number} validated: {results.get('text_model', 'N/A')}")
                else:
                    self._update_api_status(api_number, "ERROR", "❌ Invalid API key")
            else:
                self._update_api_status(api_number, "ERROR", "❌ Test module not available")

        except Exception as e:
            self._update_api_status(api_number, "ERROR", f"❌ Test failed: {str(e)}")
        finally:
            if btn:
                btn.setEnabled(True)
                btn.setText("🔍 Test")

    def use_selected_api_key_from_pool(self, api_number: int):
        """Use selected API key from pool"""
        if api_number == 1:
            selected_key = self.api_key_pool_1.currentData()
            selected_text = self.api_key_pool_1.currentText()
            target_input = self.api_key_input
        else:
            selected_key = self.api_key_pool_2.currentData()
            selected_text = self.api_key_pool_2.currentText()
            target_input = self.api_key_input_2
        
        if selected_key and "📊" not in selected_text:
            target_input.setText(selected_key)
            self._update_api_status(api_number, "INFO", "🔑 Key loaded - Click Test")
            self.add_log("SUCCESS", f"✅ API {api_number} key selected: {selected_text}")
        else:
            self._update_api_status(api_number, "WARNING", "⚠️ Please select a valid key")

    def auto_fill_dual_apis(self):
        """Automatically fill both APIs with different keys from pool"""
        try:
            # Get all available keys
            available_keys = []
            for i in range(1, self.api_key_pool_1.count()):  # Skip header
                key_data = self.api_key_pool_1.itemData(i)
                if key_data:
                    available_keys.append((i, key_data))
            
            if len(available_keys) < 2:
                self.add_log("WARNING", "⚠️ Need at least 2 different API keys for parallel processing")
                return
            
            # Select first 2 different keys
            key1_idx, key1 = available_keys[0]
            key2_idx, key2 = available_keys[1]
            
            # Fill both inputs
            self.api_key_input.setText(key1)
            self.api_key_input_2.setText(key2)
            
            # Update dropdowns
            self.api_key_pool_1.setCurrentIndex(key1_idx)
            self.api_key_pool_2.setCurrentIndex(key2_idx)
            
            # Update status
            self._update_api_status(1, "INFO", "🔑 Auto-filled - Click Test")
            self._update_api_status(2, "INFO", "🔑 Auto-filled - Click Test")
            
            self.add_log("SUCCESS", "✅ Auto-filled both API keys from pool")
            self.add_log("INFO", "🔍 Please test both keys before processing")
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Auto-fill failed: {str(e)}")

    def get_dual_api_keys(self) -> Tuple[str, str]:
        """Get both validated API keys"""
        api_key_1 = self.api_key_input.text().strip()
        api_key_2 = self.api_key_input_2.text().strip()
        
        # Validation
        if not api_key_1:
            self.add_log("ERROR", "❌ Primary API key is required")
            return "", ""
        
        if not api_key_2:
            self.add_log("WARNING", "⚠️ Secondary API key empty - will use primary for both")
            return api_key_1, api_key_1
        
        if api_key_1 == api_key_2:
            self.add_log("WARNING", "⚠️ Both API keys are identical - parallel benefit reduced")
        
        return api_key_1, api_key_2

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
        
        # Header
        api_header = QLabel("🚀 DUAL API Configuration (For Parallel Processing)")
        api_header.setObjectName("sectionHeader")
        api_header.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px;")
        api_grid.addWidget(api_header, 0, 0, 1, 3)
        
        # Primary API Key
        api_grid.addWidget(QLabel("Primary API Key:"), 1, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter primary Google AI API key")
        self.api_key_input.setObjectName("modernInput")
        api_grid.addWidget(self.api_key_input, 1, 1)
        
        btn_test_api1 = QPushButton("🔍 Test")
        btn_test_api1.setObjectName("testButton")
        btn_test_api1.clicked.connect(lambda: self.test_single_api_key(1))
        api_grid.addWidget(btn_test_api1, 1, 2)
        
        # Secondary API Key  
        api_grid.addWidget(QLabel("Secondary API Key:"), 2, 0)
        self.api_key_input_2 = QLineEdit()
        self.api_key_input_2.setEchoMode(QLineEdit.Password)
        self.api_key_input_2.setPlaceholderText("Enter secondary API key (for parallel processing)")
        self.api_key_input_2.setObjectName("modernInput")
        api_grid.addWidget(self.api_key_input_2, 2, 1)
        
        btn_test_api2 = QPushButton("🔍 Test")
        btn_test_api2.setObjectName("testButton")
        btn_test_api2.clicked.connect(lambda: self.test_single_api_key(2))
        api_grid.addWidget(btn_test_api2, 2, 2)
        
        # OR separator
        or_label = QLabel("— OR SELECT FROM POOL —")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setObjectName("infoLabel")
        or_label.setStyleSheet("color: #9ca3af; font-weight: bold; margin: 8px 0;")
        api_grid.addWidget(or_label, 3, 0, 1, 3)
        
        # Pool Selection
        api_grid.addWidget(QLabel("Primary from Pool:"), 4, 0)
        self.api_key_pool_1 = QComboBox()
        self.api_key_pool_1.setObjectName("modernCombo")
        api_grid.addWidget(self.api_key_pool_1, 4, 1)
        
        btn_use_pool1 = QPushButton("✅ Use")
        btn_use_pool1.clicked.connect(lambda: self.use_selected_api_key_from_pool(1))
        api_grid.addWidget(btn_use_pool1, 4, 2)
        
        api_grid.addWidget(QLabel("Secondary from Pool:"), 5, 0)
        self.api_key_pool_2 = QComboBox()
        self.api_key_pool_2.setObjectName("modernCombo")
        api_grid.addWidget(self.api_key_pool_2, 5, 1)
        
        btn_use_pool2 = QPushButton("✅ Use")
        btn_use_pool2.clicked.connect(lambda: self.use_selected_api_key_from_pool(2))
        api_grid.addWidget(btn_use_pool2, 5, 2)
        
        # Auto-fill both APIs button
        btn_auto_fill = QPushButton("🎲 Auto-Fill Both APIs from Pool")
        btn_auto_fill.setObjectName("primaryButton")
        btn_auto_fill.clicked.connect(self.auto_fill_dual_apis)
        api_grid.addWidget(btn_auto_fill, 6, 0, 1, 3)
        
        # Status displays
        self.api_status_label = QLabel("Primary API: Not tested")
        self.api_status_label.setObjectName("statusLabel")
        api_grid.addWidget(self.api_status_label, 7, 0, 1, 2)
        
        self.api_status_label_2 = QLabel("Secondary API: Not tested")
        self.api_status_label_2.setObjectName("statusLabel")
        api_grid.addWidget(self.api_status_label_2, 8, 0, 1, 2)
        
        # Parallel processing info
        parallel_info = QLabel("💡 Both APIs will be used for parallel processing (2x faster)")
        parallel_info.setObjectName("infoLabel")
        parallel_info.setStyleSheet("color: #10b981; font-style: italic;")
        api_grid.addWidget(parallel_info, 9, 0, 1, 3)
        
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
            "🔍 Auto Detect",
    
    # === ALPHABETICAL ORDER ===
    "🇦🇱 Albanian",
    "🇸🇦 Arabic",
    "🇦🇪 Arabic (UAE)",
    "🇪🇬 Arabic (Egypt)",
    "🇦🇷 Argentina (Spanish)",
    "🇧🇩 Bengali",
    "🇧🇦 Bosnian",
    "🇧🇷 Brazil (Portuguese)",
    "🇧🇬 Bulgarian",
    "🇪🇸 Catalan",
    "🇨🇱 Chile (Spanish)",
    "🇨🇳 Chinese (Simplified)",
    "🇹🇼 Chinese (Traditional)",
    "🇨🇴 Colombia (Spanish)",
    "🇭🇷 Croatian",
    "🇨🇿 Czech Republic",
    "🇩🇰 Danish",
    "🇳🇱 Dutch",
    "🇺🇸 English (US)",
    "🇬🇧 English (UK)",
    "🇨🇦 English (Canada)",
    "🇦🇺 English (Australia)",
    "🇳🇿 English (New Zealand)",
    "🇮🇪 English (Ireland)",
    "🇿🇦 English (South Africa)",
    "🇪🇪 Estonian",
    "🇵🇭 Filipino",
    "🇫🇮 Finnish",
    "🇫🇷 French",
    "🇩🇪 German",
    "🇬🇷 Greece",
    "🇮🇳 Gujarati",
    "🇮🇱 Hebrew",
    "🇮🇳 Hindi",
    "🇭🇺 Hungary",
    "🇮🇩 Indonesian",
    "🇮🇹 Italian",
    "🇯🇵 Japanese",
    "🇮🇳 Kannada",
    "🇰🇷 Korean",
    "🇱🇻 Latvia",
    "🇱🇹 Lithuania",
    "🇲🇰 Macedonian",
    "🇲🇾 Malay",
    "🇮🇳 Malayalam",
    "🇮🇳 Marathi",
    "🇲🇽 Mexico (Spanish)",
    "🇳🇴 Norwegian",
    "🇮🇷 Persian",
    "🇵🇪 Peru (Spanish)",
    "🇵🇱 Polish",
    "🇵🇹 Portuguese",
    "🇷🇴 Romania",
    "🇷🇺 Russian",
    "🇷🇸 Serbia",
    "🇸🇰 Slovakia",
    "🇸🇮 Slovenia",
    "🇪🇸 Spanish",
    "🇸🇪 Swedish",
    "🇮🇳 Tamil",
    "🇮🇳 Telugu",
    "🇹🇭 Thai",
    "🇹🇷 Turkish",
    "🇺🇦 Ukrainian",
    "🇵🇰 Urdu",
    "🇻🇪 Venezuela (Spanish)",
    "🇻🇳 Vietnamese"

        ])
        lang_grid.addWidget(self.source_lang, 0, 1)
        
        # Target Language
        lang_grid.addWidget(QLabel("Target Language:"), 1, 0)
        self.target_lang = QComboBox()
        self.target_lang.setObjectName("modernCombo")
        self.target_lang.addItems([
            # === ALPHABETICAL ORDER ===
    "🇦🇱 Albanian",
    "🇸🇦 Arabic",
    "🇦🇪 Arabic (UAE)",
    "🇪🇬 Arabic (Egypt)",
    "🇦🇷 Argentina (Spanish)",
    "🇧🇩 Bengali",
    "🇧🇦 Bosnian",
    "🇧🇷 Brazil (Portuguese)",
    "🇧🇬 Bulgarian",
    "🇪🇸 Catalan",
    "🇨🇱 Chile (Spanish)",
    "🇨🇳 Chinese (Simplified)",
    "🇹🇼 Chinese (Traditional)",
    "🇨🇴 Colombia (Spanish)",
    "🇭🇷 Croatian",
    "🇨🇿 Czech Republic",
    "🇩🇰 Danish",
    "🇳🇱 Dutch",
    "🇺🇸 English (US)",
    "🇬🇧 English (UK)",
    "🇨🇦 English (Canada)",
    "🇦🇺 English (Australia)",
    "🇳🇿 English (New Zealand)",
    "🇮🇪 English (Ireland)",
    "🇿🇦 English (South Africa)",
    "🇪🇪 Estonian",
    "🇵🇭 Filipino",
    "🇫🇮 Finnish",
    "🇫🇷 French",
    "🇩🇪 German",
    "🇬🇷 Greece",
    "🇮🇳 Gujarati",
    "🇮🇱 Hebrew",
    "🇮🇳 Hindi",
    "🇭🇺 Hungary",
    "🇮🇩 Indonesian",
    "🇮🇹 Italian",
    "🇯🇵 Japanese",
    "🇮🇳 Kannada",
    "🇰🇷 Korean",
    "🇱🇻 Latvia",
    "🇱🇹 Lithuania",
    "🇲🇰 Macedonian",
    "🇲🇾 Malay",
    "🇮🇳 Malayalam",
    "🇮🇳 Marathi",
    "🇲🇽 Mexico (Spanish)",
    "🇳🇴 Norwegian",
    "🇮🇷 Persian",
    "🇵🇪 Peru (Spanish)",
    "🇵🇱 Polish",
    "🇵🇹 Portuguese",
    "🇷🇴 Romania",
    "🇷🇺 Russian",
    "🇷🇸 Serbia",
    "🇸🇰 Slovakia",
    "🇸🇮 Slovenia",
    "🇪🇸 Spanish",
    "🇸🇪 Swedish",
    "🇮🇳 Tamil",
    "🇮🇳 Telugu",
    "🇹🇭 Thai",
    "🇹🇷 Turkish",
    "🇺🇦 Ukrainian",
    "🇵🇰 Urdu",
    "🇻🇪 Venezuela (Spanish)",
    "🇻🇳 Vietnamese"
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
        
        # START BUTTON WITH SPINNER
        start_button_frame = QFrame()
        start_button_frame.setObjectName("startButtonFrame")
        start_button_layout = QHBoxLayout(start_button_frame)
        start_button_layout.setContentsMargins(0, 20, 0, 10)
        
        self.btn_start_process = QPushButton("🚀 START BATCH PROCESSING")
        self.btn_start_process.setObjectName("startButton")
        self.btn_start_process.clicked.connect(self.start_processing)
        
        # Create spinner
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
        
        # BANNER SETTINGS - UNCHANGED
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
        
        # SUBTITLE SETTINGS - REMOVED POSITION X, ALWAYS CENTERED
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
        
        # SOURCE SETTINGS - UPDATED WITH TWO MODES
        source_group = QGroupBox("📎 Source Text Settings")
        source_group.setObjectName("modernGroupBox")
        source_layout = QVBoxLayout(source_group)
        
        # Source mode selection
        mode_frame = QFrame()
        mode_frame.setObjectName("settingsFrame")
        mode_layout = QVBoxLayout(mode_frame)
        
        mode_layout.addWidget(QLabel("Source Text Mode:"))
        
        # Radio buttons for mode selection
        self.source_mode_filename = QRadioButton("Extract from filename (xxx_source_SourceName.mp4)")
        self.source_mode_custom = QRadioButton("Custom text (same for all videos)")
        self.source_mode_custom.setChecked(True)  # Default to custom mode
        
        self.source_mode_filename.setObjectName("modernRadio")
        self.source_mode_custom.setObjectName("modernRadio")
        
        mode_layout.addWidget(self.source_mode_filename)
        mode_layout.addWidget(self.source_mode_custom)
        
        source_layout.addWidget(mode_frame)
        
        # Custom source text input (enabled when custom mode is selected)
        custom_frame = QFrame()
        custom_frame.setObjectName("settingsFrame")
        custom_layout = QGridLayout(custom_frame)
        
        custom_layout.addWidget(QLabel("Custom Source Text:"), 0, 0)
        self.source_text = QLineEdit()
        self.source_text.setObjectName("modernInput")
        self.source_text.setPlaceholderText("e.g., @YourChannel, website.com, News Source")
        self.source_text.setText("@YourChannel")
        custom_layout.addWidget(self.source_text, 0, 1)
        
        source_layout.addWidget(custom_frame)
        
        # Font info
        font_info_frame = QFrame()
        font_info_frame.setObjectName("settingsFrame")
        font_info_layout = QVBoxLayout(font_info_frame)
        
        self.font_status_label = QLabel("Font: Plus Jakarta Sans")
        self.font_status_label.setObjectName("infoLabel")
        font_info_layout.addWidget(self.font_status_label)
        
        source_layout.addWidget(font_info_frame)
        
        # Position and styling settings
        position_frame = QFrame()
        position_frame.setObjectName("settingsFrame")
        position_layout = QGridLayout(position_frame)
        
        position_layout.addWidget(QLabel("Position X:"), 0, 0)
        self.source_x = QSpinBox()
        self.source_x.setObjectName("modernSpin")
        self.source_x.setRange(0, 1080)
        self.source_x.setValue(50)
        self.source_x.setSingleStep(10)
        self.source_x.setSuffix(" px")
        position_layout.addWidget(self.source_x, 0, 1)
        
        position_layout.addWidget(QLabel("Position Y:"), 1, 0)
        self.source_y = QSpinBox()
        self.source_y.setObjectName("modernSpin")
        self.source_y.setRange(0, 1920)
        self.source_y.setValue(50)
        self.source_y.setSingleStep(10)
        self.source_y.setSuffix(" px")
        position_layout.addWidget(self.source_y, 1, 1)
        
        position_layout.addWidget(QLabel("Font Size:"), 2, 0)
        self.source_font_size = QSpinBox()
        self.source_font_size.setObjectName("modernSpin")
        self.source_font_size.setRange(10, 200)
        self.source_font_size.setValue(14)
        self.source_font_size.setSuffix("px")
        position_layout.addWidget(self.source_font_size, 2, 1)
        
        position_layout.addWidget(QLabel("Font Color:"), 3, 0)
        self.source_font_color = QComboBox()
        self.source_font_color.setObjectName("modernCombo")
        self.source_font_color.addItems(["white", "black", "yellow", "red", "blue"])
        position_layout.addWidget(self.source_font_color, 3, 1)
        
        source_layout.addWidget(position_frame)
        
        # Connect radio buttons to enable/disable custom text input
        self.source_mode_filename.toggled.connect(self.on_source_mode_changed)
        self.source_mode_custom.toggled.connect(self.on_source_mode_changed)
        
        settings_layout.addWidget(source_group)
        
        settings_layout.addStretch()
        settings_scroll.setWidget(settings_widget)
        settings_scroll.setWidgetResizable(True)
        
        layout.addWidget(settings_scroll)
        return widget

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
        """Begin batch video processing - CHỈ setup và start worker thread"""
        if self.file_list.count() == 0:
            self.add_log("WARNING", "⚠️ No files selected for processing")
            return

        if self.is_processing:
            self.add_log("WARNING", "⚠️ Processing already in progress")
            return

        # Validate output directory
        output_dir = self.output_path.text().strip()
        if not output_dir or not os.path.isdir(output_dir):
            self.add_log("ERROR", "❌ Output directory not found")
            return


        # Validate API key nếu subtitle được bật
        if self.chk_add_subtitle.isChecked():
            api_key_1, api_key_2 = self.get_dual_api_keys()
            if not api_key_1:
                self.add_log("ERROR", "❌ At least one API key required for subtitle processing")
                return
            
            if api_key_1 == api_key_2:
                self.add_log("WARNING", "⚠️ Using same API key for both - parallel benefit reduced")
            else:
                self.add_log("SUCCESS", "✅ DUAL API keys validated - ready for parallel processing!")

        # Validate banner file nếu banner được bật
        if self.chk_add_banner.isChecked():
            banner_path = self.banner_path.text().strip()
            if not banner_path or not os.path.exists(banner_path):
                self.add_log("ERROR", "❌ Banner file required for banner processing")
                return

        # Bắt đầu processing state
        self.set_processing_state(True)
        
        try:
            # Collect files to process
            files_to_process = []
            for i in range(self.file_list.count()):
                item_text = self.file_list.item(i).text().split("📹 ")[-1]
                files_to_process.append(item_text)

            # Collect ALL settings để pass cho worker
            settings = {
                'add_banner': self.chk_add_banner.isChecked(),
                'add_subtitle': self.chk_add_subtitle.isChecked(),
                'add_source': self.chk_add_source.isChecked(),
                'add_voice': self.chk_voice_over.isChecked(),
                'api_key': self.get_validated_api_key() if self.chk_add_subtitle.isChecked() else '',
                'source_lang': self.source_lang.currentText(),
                'target_lang': self.target_lang.currentText(),
                'banner_path': self.banner_path.text().strip(),
                'banner_x': self.banner_x.value(),
                'banner_y': self.banner_y.value(),
                'banner_height_ratio': self.banner_height_ratio.value(),
                'banner_start_time': self.banner_start_time.value(),
                'banner_end_time': self.banner_end_time.value(),
                'chroma_color': self._get_chroma_color(),
                'chroma_tolerance': self.chroma_tolerance.value(),
                'enable_chromakey': self.enable_chromakey.isChecked(),
                'source_mode_filename': hasattr(self, 'source_mode_filename') and self.source_mode_filename.isChecked(),
                'source_text': self.source_text.text().strip() if hasattr(self, 'source_text') else '',
                'source_x': self.source_x.value() if hasattr(self, 'source_x') else 50,
                'source_y': self.source_y.value() if hasattr(self, 'source_y') else 50,
                'source_font_size': self.source_font_size.value() if hasattr(self, 'source_font_size') else 14,
                'source_font_color': self.source_font_color.currentText() if hasattr(self, 'source_font_color') else 'white',
                'subtitle_size': self.subtitle_size.value(),
                'subtitle_y': self.subtitle_y.value(),
                'subtitle_style': self.subtitle_style.currentText()
            }

            # Log settings
            self.add_log("INFO", "🚀 Starting background processing...")
            self.add_log("INFO", f"📊 Files: {len(files_to_process)}")
            self.add_log("INFO", f"📁 Output: {output_dir}")
            
            effects = []
            if settings['add_banner']: effects.append("Banner")
            if settings['add_subtitle']: effects.append("Subtitle")
            if settings['add_source']: effects.append("Source")
            if settings['add_voice']: effects.append("Voice")
            
            if effects:
                self.add_log("INFO", f"🎨 Effects: {', '.join(effects)}")

            # Clear and setup queue
            if hasattr(self, 'queue_list'):
                self.queue_list.clear()
                for file_path in files_to_process:
                    queue_item = QListWidgetItem(f"⏳ {os.path.basename(file_path)}")
                    self.queue_list.addItem(queue_item)

            # 🔥 Setup và start worker - ĐÂY LÀ ĐIỂM QUAN TRỌNG
            self.processing_worker.setup_processing(files_to_process, output_dir, settings)
            self.processing_worker.start()  # Bắt đầu background thread
            
            self.add_log("SUCCESS", "✅ Background processing started - GUI remains responsive!")
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Error starting processing: {str(e)}")
            self.set_processing_state(False)
    
    def stop_processing(self):
        """Stop current processing"""
        if self.is_processing and self.processing_worker.isRunning():
            self.add_log("INFO", "🛑 Stopping processing...")
            self.processing_worker.stop_processing()
            self.processing_worker.wait(5000)  # Wait max 5 seconds
            self.set_processing_state(False)
            self.add_log("WARNING", "⚠️ Processing stopped by user")

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
        self.btn_stop_queue = QPushButton("🛑 Stop")
        self.btn_stop_queue.setObjectName("dangerButton")
        self.btn_stop_queue.clicked.connect(self.stop_processing)
        self.btn_cancel_queue = QPushButton("❌ Cancel All")
        self.btn_cancel_queue.setObjectName("dangerButton")

        queue_controls.addWidget(self.btn_pause_queue)
        queue_controls.addWidget(self.btn_resume_queue)
        queue_controls.addWidget(self.btn_stop_queue)  # 🔥 THÊM DÒNG NÀY
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
        """Add formatted log entry with timestamp and color - FIXED SYNC"""
        color_map = {
            "INFO": "#0A86DE",
            "SUCCESS": "#68d391", 
            "WARNING": "#f6ad55",
            "ERROR": "#fc8181",
            "DEBUG": "#9ca3af"  # Thêm DEBUG level
        }
        
        color = color_map.get(level, "#e2e8f0")
        
        # 🔥 FIX: Lấy thời gian thực từ hệ thống
        import datetime
        now = datetime.datetime.now()
        timestamp = now.strftime("%H:%M:%S")  # Format: 14:35:42
        
        formatted_msg = f'<span style="color: {color};">[{timestamp}] [{level}]</span> {message}'
        
        # Thêm vào log display
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.append(formatted_msg)
            
            # Auto scroll to bottom if enabled
            if hasattr(self, 'auto_scroll_enabled') and self.auto_scroll_enabled:
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
    
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

    #Hàm liên quan đến add source text
    def on_source_mode_changed(self):
        """Handle source mode radio button changes"""
        is_custom_mode = self.source_mode_custom.isChecked()
        self.source_text.setEnabled(is_custom_mode)
        
        if is_custom_mode:
            self.source_text.setStyleSheet("")  # Normal style
            self.add_log("INFO", "Source mode: Custom text")
        else:
            self.source_text.setStyleSheet("color: #888888;")  # Grayed out
            self.add_log("INFO", "Source mode: Extract from filename")

    def check_source_text_setup(self):
        """Check if source text processing is properly set up"""
        if not SOURCE_TEXT_AVAILABLE:
            self.add_log("ERROR", "Source text module not available")
            if hasattr(self, 'font_status_label'):
                self.font_status_label.setText("Font: Module not found")
                self.font_status_label.setStyleSheet("color: #fc8181;")
            return False
        
        font_path = get_plus_jakarta_font_path()
        font_available = validate_font_file(font_path)
        
        if font_available:
            self.add_log("SUCCESS", f"Plus Jakarta Sans font found: {font_path}")
            if hasattr(self, 'font_status_label'):
                self.font_status_label.setText("Font: Plus Jakarta Sans (Available)")
                self.font_status_label.setStyleSheet("color: #15803d;")
        else:
            self.add_log("WARNING", f"Plus Jakarta Sans font not found: {font_path}")
            self.add_log("INFO", "Will use system default font")
            if hasattr(self, 'font_status_label'):
                self.font_status_label.setText("Font: System default (Plus Jakarta Sans not found)")
                self.font_status_label.setStyleSheet("color: #d97706;")
        
        return True

    def calculate_universal_source_params(self, video_width: int, video_height: int) -> dict:
        """ NEW: Tính toán source text params với universal mapping"""
        try:
            # Reference size (1080x1920)
            REFERENCE_WIDTH = 1080
            REFERENCE_HEIGHT = 1920
            
            # Input validation
            if video_width <= 0 or video_height <= 0:
                self.add_log("ERROR", f"❌ Invalid video dimensions: {video_width}x{video_height}")
                return None
            
            # 🔥 Lấy GUI values với safety checks
            gui_x = self.source_x.value() if hasattr(self, 'source_x') and self.source_x is not None else 50
            gui_y = self.source_y.value() if hasattr(self, 'source_y') and self.source_y is not None else 50
            gui_font_size = self.source_font_size.value() if hasattr(self, 'source_font_size') and self.source_font_size is not None else 14
            gui_font_color = self.source_font_color.currentText() if hasattr(self, 'source_font_color') and self.source_font_color is not None else "white"
            
            # 🔥 SCALING CALCULATIONS
            width_scale = video_width / REFERENCE_WIDTH
            height_scale = video_height / REFERENCE_HEIGHT
            
            # Scale position
            actual_x = int(gui_x * width_scale)
            actual_y = int(gui_y * height_scale)
            
            # Scale font size (use minimum scale to maintain readability)
            font_scale = min(width_scale, height_scale)
            actual_font_size = max(8, int(gui_font_size * font_scale))  # Minimum 8px
            
            # Boundary checks - ensure text doesn't go off screen
            text_width_estimate = len("Source: Example Text") * actual_font_size * 0.6  # Rough estimation
            max_x = max(0, video_width - int(text_width_estimate))
            max_y = max(actual_font_size, video_height - actual_font_size)  # Keep within bounds
            
            final_x = max(0, min(actual_x, max_x))
            final_y = max(actual_font_size, min(actual_y, max_y))
            
            # 🔥 Build parameters
            params = {
                "position_x": final_x,
                "position_y": final_y,
                "font_size": actual_font_size,
                "font_color": gui_font_color,
                "video_width": video_width,
                "video_height": video_height
            }
            
            # Detailed logging
            self.add_log("SUCCESS", f"📎 Source text universal mapping calculated:")
            self.add_log("INFO", f"   📐 Video: {video_width}x{video_height}")
            self.add_log("INFO", f"   📏 Scale factors: {width_scale:.3f}x (W), {height_scale:.3f}x (H)")
            self.add_log("INFO", f"   📍 Position: ({gui_x}, {gui_y}) → ({final_x}, {final_y})")
            self.add_log("INFO", f"   🔤 Font: {gui_font_size}px → {actual_font_size}px (scale: {font_scale:.3f})")
            self.add_log("INFO", f"   🎨 Color: {gui_font_color}")
            
            return params
            
        except Exception as e:
            self.add_log("ERROR", f"❌ Source text calculation error: {str(e)}")
            import traceback
            self.add_log("ERROR", f"   📋 Traceback: {traceback.format_exc()}")
            return None
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Video Editor Tool")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Automation Team")
    
    window = VideoEditorMainWindow()
    window.show()
    sys.exit(app.exec_())