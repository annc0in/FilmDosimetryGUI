import os
import time
import platform
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QProgressBar, QTextEdit, QTableWidget, 
                            QTableWidgetItem, QSplitter, QHeaderView, QApplication,
                            QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QProcess, QProcessEnvironment
from PyQt6.QtGui import QFont
import getpass
import psutil

class AnalysisProgressScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.process = None
        self.start_time = None
        self.is_paused = False
        
        # Progress tracking
        self.total_main_images = 0
        self.processed_main_images = 0
        self.progress_per_image = 0
        
        # File monitoring
        self.results_file_path = os.path.join("scripts", "temp_analysis_results.txt")
        self.last_file_size = 0
        
        # Buffer for stdout handling
        self.stdout_buffer = ""
        
        # Initialize timers
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        
        self.file_monitor_timer = QTimer()
        self.file_monitor_timer.timeout.connect(self.check_results_file)
        
        self.keep_alive_timer = QTimer()
        self.keep_alive_timer.timeout.connect(lambda: QApplication.processEvents())
        
        self.setup_ui()
           
    def setup_ui(self):
        """Initialize the main UI layout and components"""
        self.setProperty("window_title", "Image Analysis & Dose Calculation")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header section
        header = self.create_header()
        
        # Main content area with two columns
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left and right panels
        left_panel = self.create_console_panel()
        right_panel = self.create_table_panel()
        
        content_layout.addWidget(left_panel, stretch=1)
        content_layout.addWidget(right_panel, stretch=1)
        
        # Footer section
        footer = self.create_footer()
        
        # Add all sections to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(content_widget, stretch=1)
        main_layout.addWidget(footer)
    
    def create_header(self):
        """Create header section with info button and progress bar"""
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        # Top row with info button
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_btn = QPushButton("ℹ️")
        self.info_btn.setFixedSize(40, 40)
        self.info_btn.clicked.connect(self.show_instruction_screen)
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
    
    def create_console_panel(self):
        """Create left panel with console output"""
        panel = QWidget()
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        layout.addWidget(self.console_output, stretch=1)
        return panel
    
    def create_table_panel(self):
        """Create right panel with results table"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        headers = ["№", "File", "Charge, nC", "Dose, Gy", 
                 "Dose CD, Gy", "x0, mm", "y0, mm", "xstd, mm", "ystd, mm"]
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # Column width ratios
        self.column_ratios = [0.6, 1.1, 2.2, 2.3, 2.3, 1.5, 1.5, 1.7, 1.7]
        
        # Configure table appearance
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setStyleSheet("""
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
        
        # Set up column resizing
        self.results_table.resizeEvent = lambda e: self.resize_table_columns()
        QTimer.singleShot(100, self.resize_table_columns)
        
        layout.addWidget(self.results_table, stretch=1)
        return panel
    
    def resize_table_columns(self):
        """Resize table columns proportionally"""
        total_width = self.results_table.viewport().width()
        total_ratio = sum(self.column_ratios)
        for col, ratio in enumerate(self.column_ratios):
            width = int(total_width * ratio / total_ratio)
            self.results_table.setColumnWidth(col, width)

    def create_footer(self):
        """Create footer with control buttons"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.back_btn = QPushButton("⬅️")
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.clicked.connect(self.go_to_analysis_screen)
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
        
        self.elapsed_label = QLabel("Elapsed Time: 00.00 sec")
        self.elapsed_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.home_btn = QPushButton("🏠")
        self.home_btn.setFixedSize(40, 40)
        self.home_btn.clicked.connect(self.go_to_main_screen)
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
        footer_layout.addWidget(self.elapsed_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.home_btn)
        
        return footer
    
    # Process control methods
    def start_analysis_process(self):
        """Start the Octave analysis process"""
        if platform.system() != "Darwin":
            os.environ['LC_ALL'] = 'C.UTF-8'

        self.reset_ui_state()
        
        # Reset file monitoring
        if os.path.exists(self.results_file_path):
            os.remove(self.results_file_path)
        
        # Start timers
        self.file_monitor_timer.start(500)
        self.start_time = time.time()
        self.timer.start(100)
        self.keep_alive_timer.start(100)
        
        # Configure and start process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.on_process_finished)
        self.process.setWorkingDirectory(os.getcwd())
        
        if platform.system() == "Windows":
            self.setup_windows_process()
        elif platform.system() == "Darwin":
            self.setup_macos_process()
        else:
            self.setup_linux_process()
        
        # Update UI state
        self.set_navigation_enabled(False)
        self.pause_btn.setText("Pause ⏸")
        self.pause_btn.setEnabled(True)
        
        # Set high priority after process starts
        QTimer.singleShot(100, self.set_process_priority)

    def set_process_priority(self):
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

    def setup_windows_process(self):
        """Configure process for Windows environment"""
        env = QProcessEnvironment.systemEnvironment()
        current_path = env.value("PATH", "")
        octave_path = self.find_octave_executable()
        octave_dir = os.path.dirname(octave_path)
        octave_root = os.path.normpath(os.path.join(octave_dir, "..", ".."))
        unzip_dir = os.path.join(octave_root, "usr", "bin")
        additional_paths = [unzip_dir, "C:\\Windows\\System32"]
        env.insert("PATH", current_path + ";" + ";".join(additional_paths))
        env.insert("OCTAVE_GUI_MODE", "1")
        self.process.setProcessEnvironment(env)

        octave_path = self.find_octave_executable()
        octave_command = "cd('scripts'); pkg load io; pkg load image; analyze_shots_films_MOD_centering_Charge_Density_bgnd();"
        self.process.start(octave_path, ["--no-gui", "--eval", octave_command])

    def setup_linux_process(self):
        """Configure process for Linux environment"""
        env = QProcessEnvironment.systemEnvironment()
        env.insert("QT_QPA_PLATFORM", "offscreen")
        env.insert("OCTAVE_DISABLE_GUI", "1") 
        env.insert("OCTAVE_GUI_MODE", "1")
        env.insert("LC_ALL", "C.UTF-8")
        env.insert("LANG", "C.UTF-8")
        self.process.setProcessEnvironment(env)
        
        octave_command = "cd('scripts'); pkg load io image; try analyze_shots_films_MOD_centering_Charge_Density_bgnd(); catch err error(['Error: ', err.message]); end"
        self.process.start("/usr/bin/octave", ["--no-gui", "--eval", octave_command])

    def setup_macos_process(self):
        """Configure macOS process environment using wrapper script"""
        # Auto-set execute permissions for wrapper
        wrapper_path = os.path.join(os.getcwd(), "octave_wrapper.sh")
        if os.path.exists(wrapper_path):
            os.chmod(wrapper_path, 0o755)
        
        # Use minimal environment
        env = QProcessEnvironment()
        env.insert("PATH", "/usr/local/bin:/usr/bin:/bin")
        env.insert("HOME", os.environ.get('HOME', ''))
        
        self.process.setProcessEnvironment(env)
        
        # Get path to wrapper script (like in processing_screen.py)
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            wrapper_path = os.path.join(sys._MEIPASS, "octave_wrapper.sh")
        else:
            # Running in development
            wrapper_path = os.path.join(os.getcwd(), "octave_wrapper.sh")
        
        octave_command = "cd('scripts'); pkg load io image; analyze_shots_films_MOD_centering_Charge_Density_bgnd();"
        
        # Execute wrapper with full path and arguments
        self.process.start("/bin/bash", [wrapper_path, os.getcwd(), octave_command])
    
    def find_octave_executable(self):
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

    def reset_ui_state(self):
        """Reset UI elements to initial state"""
        self.console_output.clear()
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.elapsed_label.setText("Elapsed Time: 00.00 sec")
        self.stdout_buffer = ""
        self.total_main_images = 0
        self.processed_main_images = 0
        self.progress_per_image = 0
        self.last_file_size = 0
        self.start_time = None
        self.is_paused = False

    # Output handling methods
    def handle_stdout(self):
        """Process stdout with proper line buffering"""
        if not self.process:
            return

        raw_data = bytes(self.process.readAllStandardOutput())
        new_data = raw_data.decode('utf-8', errors='ignore')
        
        if not new_data:
            return

        self.stdout_buffer += new_data
        
        while '\n' in self.stdout_buffer:
            line, self.stdout_buffer = self.stdout_buffer.split('\n', 1)
            line = line.rstrip('\r')
            
            if not line.strip():
                continue
                
            cursor = self.console_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(line + '\n')
            self.console_output.setTextCursor(cursor)
            self.console_output.ensureCursorVisible()
            
            self.update_progress_from_output(line)

    def handle_stderr(self):
        """Filter and process stderr output"""
        if not self.process:
            return

        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf-8", errors='ignore')

        # Filter out specific gnuplot warnings and other unwanted output
        filtered_lines = []
        for line in stderr.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Skip gnuplot multiplot warnings from macOS
            if "Reading from '-' inside a multiplot not supported" in line:
                continue
            if "use a datablock instead" in line:
                continue
            
            # Skip warnings from Windows
            if "/packages/statistics-" in line or "FC_WEIGHT didn't match" in line:
                continue
                
            filtered_lines.append(line)

        # Only display if there are actual error messages
        if filtered_lines:
            error_text = '\n'.join(filtered_lines)
            self.console_output.append(f"ERROR: {error_text}")

    def update_progress_from_output(self, output):
        """Update progress based on console output"""
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if "Processing main image set" in line:
                self.progress_bar.setValue(10)
            elif line.startswith("Processed main image"):
                parts = line.split()
                if len(parts) >= 6 and parts[4] == "of":
                    try:
                        current_image = int(parts[3])
                        total_images = int(parts[5])
                        
                        if self.total_main_images == 0:
                            self.total_main_images = total_images
                            self.progress_per_image = 80.0 / total_images
                        
                        if current_image < total_images:
                            progress_increment = self.progress_per_image * current_image
                            new_progress = 10 + int(progress_increment + 0.5)
                            self.progress_bar.setValue(new_progress)
                    except (ValueError, IndexError):
                        continue
            elif "Generating" in line and "pdf-report" in line:
                self.progress_bar.setValue(90)

    # File monitoring methods
    def check_results_file(self):
        """Monitor results file for updates"""
        if not os.path.exists(self.results_file_path):
            return
        
        current_size = os.path.getsize(self.results_file_path)
        
        if current_size > self.last_file_size:
            try:
                with open(self.results_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                data_lines = [line.strip() for line in lines[1:] if line.strip()]
                
                if len(data_lines) > self.results_table.rowCount():
                    self.update_results_table(data_lines)
                
                self.last_file_size = current_size
            except (IOError, OSError):
                pass

    def update_results_table(self, data_lines):
        """Update results table with new data"""
        current_rows = self.results_table.rowCount()
        
        for i in range(current_rows, len(data_lines)):
            line = data_lines[i]
            parts = line.split('\t')
            
            if len(parts) >= 11:
                self.results_table.insertRow(i)
                
                # Populate table columns
                self.results_table.setItem(i, 0, QTableWidgetItem(parts[0]))
                self.results_table.setItem(i, 1, QTableWidgetItem(parts[1]))
                
                charge = f"{float(parts[2]):.2f}"
                self.results_table.setItem(i, 2, QTableWidgetItem(charge))
                
                dose_cd = float(parts[3])
                dose_cd_std = float(parts[4])
                dose_cd_text = f"{dose_cd:.2f} ± {dose_cd_std:.2f}"
                self.results_table.setItem(i, 3, QTableWidgetItem(dose_cd_text))
                
                dose_bg = float(parts[5])
                dose_bg_std = float(parts[6])
                dose_bg_text = f"{dose_bg:.2f} ± {dose_bg_std:.2f}"
                self.results_table.setItem(i, 4, QTableWidgetItem(dose_bg_text))
                
                xstd = f"{float(parts[7]):.2f}"
                self.results_table.setItem(i, 5, QTableWidgetItem(xstd))
                
                ystd = f"{float(parts[8]):.2f}"
                self.results_table.setItem(i, 6, QTableWidgetItem(ystd))
                
                x0 = f"{float(parts[9]):.2f}"
                self.results_table.setItem(i, 7, QTableWidgetItem(x0))
                
                y0 = f"{float(parts[10]):.2f}"
                self.results_table.setItem(i, 8, QTableWidgetItem(y0))

    # Process control methods
    def toggle_pause(self):
        """Terminate process and clean up temporary files"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.is_paused = True
            self.pause_btn.setText("Pause  ▶")
            QApplication.processEvents()

            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()

            self.cleanup_temp_files()
            self.stop_timers()
            self.set_navigation_enabled(True)
            self.console_output.append("\n[PAUSED] Processing terminated by user.\n")

    def on_process_finished(self, exit_code, exit_status):
        """Handle process completion"""
        self.stop_timers()

        # Process remaining buffer content
        if self.stdout_buffer.strip():
            cursor = self.console_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(self.stdout_buffer.rstrip() + '\n')
            self.console_output.setTextCursor(cursor)
            self.update_progress_from_output(self.stdout_buffer)
            
        self.cleanup_temp_files()

        # Update UI based on exit status
        if exit_code == 0:
            self.progress_bar.setValue(100)
            self.check_results_file()
        else:
            self.console_output.append(f"\n=== Analysis failed with exit code {exit_code} ===")

        self.set_navigation_enabled(True)
        self.pause_btn.setText("Pause  ▶")
        self.pause_btn.setEnabled(False)

    def cleanup_temp_files(self):
        """Remove temporary files"""
        temp_files = [
            os.path.join("scripts", "get_user_inputs.json"),
            os.path.join("scripts", "temp_analysis_results.txt")
        ]
        
        for file_path in temp_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.console_output.append(f"[WARNING] Failed to delete {file_path}: {str(e)}")

    def stop_timers(self):
        """Stop all active timers"""
        self.timer.stop()
        self.file_monitor_timer.stop()
        self.keep_alive_timer.stop()

    # Navigation methods
    def set_navigation_enabled(self, enabled):
        """Enable/disable navigation buttons"""
        self.back_btn.setEnabled(True)  # Always allow back navigation
        self.home_btn.setEnabled(enabled)
        self.info_btn.setEnabled(enabled)

    def update_elapsed_time(self):
        """Update elapsed time display"""
        if self.start_time and not self.is_paused:
            elapsed = time.time() - self.start_time
            self.elapsed_label.setText(f"Elapsed Time: {elapsed:.2f} sec")

    def show_instruction_screen(self):
        """Navigate to instruction screen"""
        if self.is_paused or not self.process or self.process.state() != QProcess.ProcessState.Running:
            self.main_window.stacked_widget.setCurrentWidget(
                self.main_window.instruction_screen)

    def go_to_analysis_screen(self):
        """Navigate back to analysis screen"""
        if (self.is_paused or not self.process or 
            self.process.state() != QProcess.ProcessState.Running):
            self.main_window.stacked_widget.setCurrentWidget(
                self.main_window.analysis_screen)

    def go_to_main_screen(self):
        """Navigate to main screen"""
        if self.is_paused or not self.process or self.process.state() != QProcess.ProcessState.Running:
            self.main_window.stacked_widget.setCurrentWidget(
                self.main_window.main_screen)