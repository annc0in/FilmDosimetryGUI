import os
import platform
import sys
import time
import json
import getpass
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QProgressBar, QTextEdit, QTableWidget, 
                           QTableWidgetItem, QSizePolicy, QHeaderView, QApplication)
from PyQt6.QtCore import Qt, QProcess, QTimer, pyqtSignal, QProcessEnvironment
from PyQt6.QtGui import QPixmap, QTextCursor
import psutil

class ProcessingScreen(QWidget):
   processing_finished = pyqtSignal(int, QProcess.ExitStatus)
   
   def __init__(self, parent=None):
       super().__init__(parent)
       self.main_window = parent
       self.setProperty("window_title", "Calibration & Film Processing")
       
       # Process state
       self.process = None
       self.start_time = None
       self.is_paused = False
       
       # Image handling
       self.current_cal_pixmap = None
       self.current_image_path = None
       self.waiting_for_calibration = False
       
       # File monitoring
       self.data_file_path = 'octave_gui_data.txt'
       self.last_read_position = 0
       
       # Output handling
       self._stdout_buffer = ""
       
       # Timers
       self.timer = QTimer()
       self.timer.timeout.connect(self.update_elapsed_time)
       
       self.file_monitor_timer = QTimer()
       self.file_monitor_timer.timeout.connect(self.check_data_file)

       self.keep_alive_timer = QTimer()
       self.keep_alive_timer.timeout.connect(lambda: QApplication.processEvents())
       
       self._create_ui()
       
   def _create_ui(self):
       """Initialize UI layout and components"""
       main_layout = QVBoxLayout(self)
       main_layout.setContentsMargins(20, 20, 20, 20)
       main_layout.setSpacing(15)
       
       # Header with info button and progress bar
       header = self._create_header()
       
       # Main content with console and table panels
       content_widget = QWidget()
       content_layout = QHBoxLayout(content_widget)
       content_layout.setSpacing(20)
       content_layout.setContentsMargins(0, 0, 0, 0)
       
       left_panel = self._create_left_panel()
       right_panel = self._create_right_panel()
       
       content_layout.addWidget(left_panel, stretch=1)
       content_layout.addWidget(right_panel, stretch=1)
       
       # Footer with navigation controls
       footer = self._create_footer()
       
       main_layout.addWidget(header)
       main_layout.addWidget(content_widget, stretch=1)
       main_layout.addWidget(footer)
   
   def _create_header(self):
        """Create header with info button and progress bar"""
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        # Info button row
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_btn = QPushButton("ℹ️")
        self.info_btn.setFixedSize(40, 40)
        self.info_btn.clicked.connect(self.show_instructions)
        self.info_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                border: none;
                background: transparent;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 30);
                border-radius: 20px;
            }
            QPushButton:pressed {
                background: rgba(128, 128, 128, 50);
            }
            QPushButton:disabled {
                color: rgba(128, 128, 128, 100);
            }
        """)
        self.info_btn.setEnabled(False)
        
        top_row_layout.addStretch()
        top_row_layout.addWidget(self.info_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                border-radius: 3px;
            }
        """)
        
        header_layout.addWidget(top_row)
        header_layout.addWidget(self.progress_bar)
        
        return header
   
   def _create_left_panel(self):
       """Create left panel with console and calibration image"""
       panel = QWidget()
       layout = QVBoxLayout(panel)
       layout.setSpacing(10)
       layout.setContentsMargins(0, 0, 0, 0)
       
       # Console output
       self.console_output = QTextEdit()
       self.console_output.setReadOnly(True)
       self.console_output.setMinimumHeight(200)
       self.console_output.setStyleSheet("""
           QTextEdit {
               font-family: 'Courier New', monospace;
               font-size: 11px;
               background-color: transparent;
               border: 1px solid #ccc;
               border-radius: 4px;
           }
       """)
       
       # Calibration image display
       self.cal_image_label = QLabel()
       self.cal_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
       self.cal_image_label.setText("Calibration curve will be displayed here")
       self.cal_image_label.setScaledContents(False)
       self.cal_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
       self.cal_image_label.setStyleSheet("border: none; background-color: transparent;")
       
       layout.addWidget(self.console_output, stretch=1)
       layout.addWidget(self.cal_image_label, stretch=1)
       
       return panel
   
   def _create_right_panel(self):
       """Create right panel with data table"""
       panel = QWidget()
       layout = QVBoxLayout(panel)
       layout.setContentsMargins(0, 0, 0, 0)
       
       # Data table configuration
       self.data_table = QTableWidget()
       self.data_table.setColumnCount(4)
       self.data_table.setHorizontalHeaderLabels(["Film #", "Dose (Gy)", "STD", "Charge"])
       self.data_table.setAlternatingRowColors(True)
       self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
       self.data_table.verticalHeader().setVisible(False)
       self.data_table.setStyleSheet("""
           QTableWidget {
               gridline-color: #d0d0d0;
               background-color: transparent;
               border: 1px solid #ccc;
               border-radius: 4px;
           }
           QHeaderView::section {
               background-color: transparent;
               border: 1px solid #ccc;
               padding: 5px;
               font-weight: bold;
           }
           QTableWidget::item:selected {
               background-color: #3daee9;
               color: white;
           }
       """)
       
       # Column width configuration
       header = self.data_table.horizontalHeader()
       header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
       header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
       header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
       header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
       
       layout.addWidget(self.data_table, stretch=1)
       return panel

   def _create_footer(self):
        """Create footer with navigation and control buttons"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Back button
        self.back_btn = QPushButton("⬅️")
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                border: none;
                background: transparent;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 30);
                border-radius: 20px;
            }
            QPushButton:pressed {
                background: rgba(128, 128, 128, 50);
            }
            QPushButton:disabled {
                color: rgba(128, 128, 128, 100);
            }
        """)
        
        # Pause button (оставляем как есть)
        self.pause_btn = QPushButton("Pause ⏸")
        self.pause_btn.setFixedSize(100, 40)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #d3d3d3;
                border-radius: 20px;
                padding: 5px 15px;
                background-color: transparent;
                color: palette(text);
            }
            QPushButton:hover {
                background-color: rgba(211, 211, 211, 50);
            }
            QPushButton:pressed {
                border: 2px solid #a8a8a8;
            }
        """)
        
        # Elapsed time label
        self.elapsed_time_label = QLabel("Elapsed Time: 00.00 sec")
        self.elapsed_time_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        # Home button
        self.home_btn = QPushButton("🏠")
        self.home_btn.setFixedSize(40, 40)
        self.home_btn.clicked.connect(self.go_home)
        self.home_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                border: none;
                background: transparent;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 30);
                border-radius: 20px;
            }
            QPushButton:pressed {
                background: rgba(128, 128, 128, 50);
            }
            QPushButton:disabled {
                color: rgba(128, 128, 128, 100);
            }
        """)
        
        footer_layout.addWidget(self.back_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.pause_btn)
        footer_layout.addSpacing(20)
        footer_layout.addWidget(self.elapsed_time_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.home_btn)
        
        return footer
   
   def start_processing(self):
       """Start calibration processing"""
       self.clear()
       self._set_navigation_enabled(False)
       self._load_calibration_image()
       
       # Check for new calibration creation
       try:
           with open('user_inputs.json', 'r') as f:
               user_data = json.load(f)
           self.waiting_for_calibration = not user_data.get('use_existing_calibration', False)
       except (OSError, json.JSONDecodeError):
           self.waiting_for_calibration = False

       # Reset monitoring
       self.last_read_position = 0
       if os.path.exists(self.data_file_path):
           os.remove(self.data_file_path)
       
       # Start monitoring and process
       self.file_monitor_timer.start(200)
       self._configure_and_start_process()
       
       # Start timers
       self.start_time = time.time()
       self.timer.start(200)
       self.keep_alive_timer.start(100)
       
       # Update UI
       self.pause_btn.setText("Pause ⏸")
       self.pause_btn.setEnabled(True)
       
       # Set high priority after process starts
       QTimer.singleShot(100, self._set_process_priority)

   def _configure_and_start_process(self):
        """Configure and start Octave process"""
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._on_process_finished)
        self.process.setWorkingDirectory(os.getcwd())
        
        if platform.system() == "Windows":
            self._setup_windows_process()
        elif platform.system() == "Darwin":
            self._setup_macos_process()
        else:
            self._setup_linux_process()

   def _set_process_priority(self):
        """Set high priority for Octave process"""
        if not self.process or self.process.processId() == 0:
            return
        
        try:
            p = psutil.Process(self.process.processId())
            if platform.system() == "Windows":
                p.nice(psutil.REALTIME_PRIORITY_CLASS)
            else:
                p.nice(-20)
        except:
            pass
        
   def _setup_windows_process(self):
        """Configure Windows process environment"""
        env = QProcessEnvironment.systemEnvironment()
        current_path = env.value("PATH", "")

        octave_path = self._find_octave_executable()
        octave_dir = os.path.dirname(octave_path)
        octave_root = os.path.normpath(os.path.join(octave_dir, "..", ".."))
        unzip_dir = os.path.join(octave_root, "usr", "bin")

        additional_paths = [
            unzip_dir,
            "C:\\Windows\\System32"
        ]
        env.insert("PATH", current_path + ";" + ";".join(additional_paths))
        env.insert("OCTAVE_GUI_MODE", "1")
        self.process.setProcessEnvironment(env)

        octave_command = (
            "pkg load io; pkg load image; "
            "Check_calibration_XD_add_films();"
        )
        self.process.start(octave_path, ["--no-gui", "--eval", octave_command])

   def _setup_linux_process(self):
       """Configure Linux process environment"""
       username = getpass.getuser()
       runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/tmp/runtime-{username}")
       os.makedirs(runtime_dir, exist_ok=True)

       env_vars = [
           "-i",
           f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
           f"XAUTHORITY={os.environ.get('XAUTHORITY', '')}",
           f"XDG_RUNTIME_DIR={runtime_dir}",
           "OCTAVE_GUI_MODE=1",
           "QT_QPA_PLATFORM=offscreen",
           f"HOME={os.environ.get('HOME', '')}",
           "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
           "/usr/bin/octave",
           "--no-gui",
           "--eval",
           "pkg load io image statistics; Check_calibration_XD_add_films();"
       ]
       
       self.process.start("/usr/bin/env", env_vars)

   def _setup_macos_process(self):
        """Configure macOS process environment using wrapper script"""
        # Auto-set execute permissions for wrapper
        wrapper_path = os.path.join(os.getcwd(), "octave_wrapper.sh")
        if os.path.exists(wrapper_path):
            os.chmod(wrapper_path, 0o755)  # Give execute permissions automatically
        
        # Use minimal environment
        env = QProcessEnvironment()
        env.insert("PATH", "/usr/local/bin:/usr/bin:/bin")
        env.insert("HOME", os.environ.get('HOME', ''))
        
        self.process.setProcessEnvironment(env)
        
        # Get path to wrapper script (relative to executable)
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            wrapper_path = os.path.join(sys._MEIPASS, "octave_wrapper.sh")
        else:
            # Running in development
            wrapper_path = os.path.join(os.getcwd(), "octave_wrapper.sh")
        
        # Execute wrapper with current directory as argument
        self.process.start("/bin/bash", [wrapper_path, os.getcwd()])

   def _find_octave_executable(self):
        """Locate Octave executable on different platforms"""
        import shutil
        
        # Check PATH
        octave_path = shutil.which("octave" if platform.system() != "Windows" else "octave.exe")
        
        if octave_path:
            return octave_path
        
        # Fallback
        if platform.system() == "Windows":
            return "octave.exe"
        elif platform.system() == "Darwin":
            return "octave"
        else:
            return "/usr/bin/octave"

   def toggle_pause(self):
       """Terminate process and cleanup"""
       if self.process and self.process.state() == QProcess.ProcessState.Running:
           self.is_paused = True
           self.pause_btn.setText("Pause  ▶")
           QApplication.processEvents()

           self.process.terminate()
           if not self.process.waitForFinished(1000):
               self.process.kill()

           self._cleanup_temp_files()
           self._stop_timers()
           self._set_navigation_enabled(True)
           self._append_console_output("\n[PAUSED] Processing terminated by user.\n")

   def _on_process_finished(self, exit_code, exit_status):
       """Handle process completion"""
       self._stop_timers()
       self._cleanup_temp_files()

       if exit_code == 0:
           self.progress_bar.setValue(100)
       else:
           self._append_console_output(f"\n[ERROR] Processing failed with exit code {exit_code}\n")

       self._set_navigation_enabled(True)
       self.pause_btn.setText("Pause  ▶")
       self.pause_btn.setEnabled(False)
       self.processing_finished.emit(exit_code, exit_status)

   def _cleanup_temp_files(self):
       """Remove temporary files"""
       temp_files = ["user_inputs.json", "octave_gui_data.txt"]
       
       for file_name in temp_files:
           file_path = os.path.join(os.getcwd(), file_name)
           if os.path.exists(file_path):
               try:
                   os.remove(file_path)
               except OSError as e:
                   self._append_console_output(f"[WARNING] Failed to delete {file_path}: {str(e)}")

   def _stop_timers(self):
       """Stop all active timers"""
       self.timer.stop()
       self.file_monitor_timer.stop()
       self.keep_alive_timer.stop()

   def check_data_file(self):
       """Monitor data file for new entries"""
       if not os.path.exists(self.data_file_path):
           return
       
       try:
           with open(self.data_file_path, 'r') as f:
               f.seek(self.last_read_position)
               new_lines = f.readlines()
               self.last_read_position = f.tell()
               
               for line in new_lines:
                   line = line.strip()
                   if line.startswith('[FILM_DATA]'):
                       try:
                           json_str = line.replace('[FILM_DATA]', '').strip()
                           film_data = json.loads(json_str)
                           self._add_film_data(film_data)
                       except (ValueError, json.JSONDecodeError):
                           self._append_console_output(f"Invalid film data format: {line}\n")
       
       except OSError:
           pass

   def _handle_stdout(self):
       """Process stdout output"""
       if not self.process:
           return

       raw_data = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='ignore')
       
       # Handle calibration image notification
       if 'Calibration curve is saved to' in raw_data:
           path = raw_data.split('Calibration curve is saved to')[1].split('\n')[0].strip()
           if self.waiting_for_calibration:
               self._display_calibration_image(path)
               self.waiting_for_calibration = False
       
       # Process output with cursor handling
       cursor = self.console_output.textCursor()
       cursor.movePosition(QTextCursor.MoveOperation.End)
       
       if '\r' in raw_data:
           parts = raw_data.split('\r')
           last_part = parts[-1]
           
           cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
           prev_text = cursor.selectedText()
           
           if ("Processing" in last_part and "Processing" in prev_text) or \
              ("Saving" in last_part and "Saving" in prev_text):
               cursor.removeSelectedText()
           else:
               cursor.movePosition(QTextCursor.MoveOperation.End)
           
           cursor.insertText(last_part)
       else:
           cursor.insertText(raw_data)
       
       self.console_output.setTextCursor(cursor)
       self.console_output.ensureCursorVisible()
       
       # Update progress indicators
       self._update_progress_from_output(raw_data)

   def _handle_stderr(self):
        """Filter and process stderr output"""
        if not self.process:
            return
            
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf-8", errors="ignore")
        
        # On macOS, show all stderr for debugging
        if platform.system() == "Darwin":
            for line in stderr.split('\n'):
                line = line.strip()
                if line:
                    self._append_console_output(f"[stderr] {line}\n")
            return
        
        # Filter common warnings on other platforms
        filter_patterns = [
            "shadows a core library function",
            "/packages/statistics-",
            "statistics-1.7.5/PKG_ADD",
            "load_packages_and_dependencies",
            "load_packages",
            "called from"
        ]
        
        if any(pattern in stderr for pattern in filter_patterns):
            return

        # Display filtered errors
        for line in stderr.split('\n'):
            line = line.strip()
            if line and not any(pattern in line.lower() for pattern in ["shadow", "statistics", "pkg_add", "load_packages"]):
                self._append_console_output(f"[stderr] {line}\n")

   def _update_progress_from_output(self, output):
       """Update progress based on output content"""
       if "Processing calibration film 1" in output:
           self.progress_bar.setValue(20)
       elif "Processing experimental film 1" in output:
           self.progress_bar.setValue(30)
       elif "Saving results to: !Processed" in output:
           self.progress_bar.setValue(70)

   def _append_console_output(self, text):
       """Append text to console output"""
       self.console_output.append(text.strip())

   def _add_film_data(self, film_data):
       """Add film data to results table"""
       row_count = self.data_table.rowCount()
       self.data_table.insertRow(row_count)
       
       # Populate row data
       data_items = [
           str(film_data.get('num', '')),
           f"{film_data.get('dose', 0):.3f}",
           f"{film_data.get('std', 0):.3f}",
           f"{film_data.get('charge', 0):.2f}"
       ]
       
       for col, value in enumerate(data_items):
           item = QTableWidgetItem(value)
           if col > 0:  # Center align numeric columns
               item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
           self.data_table.setItem(row_count, col, item)
       
       self.data_table.scrollToBottom()

   def _load_calibration_image(self):
       """Load calibration curve image"""
       try:
           with open('user_inputs.json', 'r') as f:
               user_data = json.load(f)
           
           if user_data.get('use_existing_calibration', False):
               cal_file = user_data.get('selected_cal', '')
               if cal_file:
                   image_path = os.path.join('!CalibrationCurves', cal_file)
                   if os.path.exists(image_path):
                       self._display_calibration_image(image_path)
                   else:
                       self.cal_image_label.setText("Calibration image not found")
           else:
               self.cal_image_label.setText("Calibration curve will be generated...")
               
       except (OSError, json.JSONDecodeError) as e:
           self.cal_image_label.setText(f"Error loading calibration: {str(e)}")

   def _display_calibration_image(self, image_path):
       """Display calibration curve image with scaling"""
       self.current_image_path = image_path
       
       if os.path.exists(image_path):
           pixmap = QPixmap(image_path)
           if not pixmap.isNull():
               self.current_cal_pixmap = pixmap
               available_height = self.cal_image_label.height()
               
               if available_height <= 0:
                   QTimer.singleShot(50, lambda: self._display_calibration_image(image_path))
                   return
               
               scaled_pixmap = self._scale_image_to_panel_height(pixmap)
               self.cal_image_label.setPixmap(scaled_pixmap)
           else:
               self.cal_image_label.setText("Failed to load calibration image")
       else:
           self.cal_image_label.setText("Calibration image not found")

   def _scale_image_to_panel_height(self, pixmap):
       """Scale image to fit panel height maintaining aspect ratio"""
       if pixmap.isNull():
           return pixmap
       
       available_height = self.cal_image_label.height() or 400
       device_pixel_ratio = self.devicePixelRatio()
       
       scaled_pixmap = pixmap.scaledToHeight(
           int(available_height * device_pixel_ratio),
           Qt.TransformationMode.SmoothTransformation
       )
       scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
       
       return scaled_pixmap

   def resizeEvent(self, event):
       """Handle window resize to update image scaling"""
       super().resizeEvent(event)
       if hasattr(self, 'current_image_path') and self.current_image_path:
           QTimer.singleShot(100, lambda: self._display_calibration_image(self.current_image_path))

   def _set_navigation_enabled(self, enabled):
        """Toggle navigation button states"""
        self.back_btn.setEnabled(True)  # Always allow back navigation
        self.home_btn.setEnabled(enabled)
        self.info_btn.setEnabled(enabled)

   def update_elapsed_time(self):
       """Update elapsed time display"""
       if self.start_time and not self.is_paused:
           elapsed = time.time() - self.start_time
           self.elapsed_time_label.setText(f"Elapsed Time: {elapsed:.2f} sec")

   def show_instructions(self):
       """Navigate to instructions screen"""
       if self.is_paused or not self.process or self.process.state() != QProcess.ProcessState.Running:
           if self.main_window:
               self.main_window.stacked_widget.setCurrentWidget(
                   self.main_window.instruction_screen)
   
   def go_back(self):
        """Navigate back to calibration screen"""
        if (self.is_paused or not self.process or 
            self.process.state() != QProcess.ProcessState.Running):
            if self.main_window and hasattr(self.main_window, 'calibration_screen'):
                self.main_window.stacked_widget.setCurrentWidget(self.main_window.calibration_screen)
   
   def go_home(self):
       """Navigate to main screen"""
       if self.is_paused or not self.process or self.process.state() != QProcess.ProcessState.Running:
           if self.main_window and hasattr(self.main_window, 'main_screen'):
               self.main_window.stacked_widget.setCurrentWidget(self.main_window.main_screen)

   def clear(self):
        """Reset UI to initial state"""
        self.console_output.clear()
        self.data_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.elapsed_time_label.setText("Elapsed Time: 00.00 sec")
        self.cal_image_label.clear()
        self.cal_image_label.setText("Calibration curve will be displayed here")
        self.current_image_path = None
        self.waiting_for_calibration = False
        self.last_read_position = 0
        self.is_paused = False
        self.start_time = None
        
        self._stop_timers()
        self.pause_btn.setText("Pause ⏸")
        self.pause_btn.setEnabled(True)
        self._set_navigation_enabled(False)