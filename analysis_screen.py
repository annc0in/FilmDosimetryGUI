import os
import glob
import json
import tarfile
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QComboBox, QCheckBox, QLineEdit, QMessageBox,
                            QScrollArea, QFrame, QGroupBox, QGridLayout, QSpacerItem,
                            QSizePolicy, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QProcess

class AnalysisScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_roi_pixmap = None  # Stores original pixmap for resizing
        self.extraction_timer = QTimer()  # Timer for delayed archive extraction
        self.extraction_timer.setSingleShot(True)
        self.extraction_timer.timeout.connect(self.extract_archive)
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """Initialize the main UI layout and components"""
        self.setProperty("window_title", "Image Analysis & Dose Calculation")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section
        header = self.create_header()
        
        # Main content area with two columns
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(30)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left and right panels
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        content_layout.addWidget(left_panel, stretch=1)
        content_layout.addWidget(right_panel, stretch=1)
        
        # Add sections to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(content_widget, stretch=1)
        
        # Footer section
        footer = self.create_footer()
        main_layout.addWidget(footer)
    
    def create_header(self):
        """Create header section with info button"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        info_btn = QPushButton("ℹ️")
        info_btn.setFixedSize(40, 40)
        info_btn.clicked.connect(self.show_instructions)
        info_btn.setStyleSheet("""
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
        """)
        
        header_layout.addStretch()
        header_layout.addWidget(info_btn)
        
        return header
    
    def create_left_panel(self):
        """Create left panel with ROI selection and data info"""
        panel = QWidget()
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        # Shape and size selection
        shape_size_group = QWidget()
        shape_size_layout = QHBoxLayout(shape_size_group)
        
        shape_label = QLabel("ROI shape:")
        shape_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Circle", "Square"])
        
        size_label = QLabel("Radius/Side length (mm):")
        size_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.size_input = QLineEdit()
        self.size_input.setPlaceholderText("e.g., 2 or 2.5")
        
        shape_size_layout.addWidget(shape_label)
        shape_size_layout.addWidget(self.shape_combo)
        shape_size_layout.addWidget(size_label)
        shape_size_layout.addWidget(self.size_input)
        shape_size_layout.addStretch()
        
        layout.addWidget(shape_size_group)
        
        # Data directory selection
        data_dir_group = QWidget()
        data_dir_layout = QHBoxLayout(data_dir_group)
        
        data_dir_label = QLabel("Calibrated data directory:")
        data_dir_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.data_dir_combo = QComboBox()
        self.data_dir_combo.currentTextChanged.connect(self.on_data_directory_changed)
        
        data_dir_layout.addWidget(data_dir_label)
        data_dir_layout.addWidget(self.data_dir_combo)
        data_dir_layout.addStretch()
        
        layout.addWidget(data_dir_group)
        
        # Archive info
        archive_info_group = QWidget()
        archive_info_layout = QHBoxLayout(archive_info_group)

        archive_info_text = QLabel("Archive info:")
        archive_info_text.setStyleSheet("font-size: 16px;")
        self.archive_info_label = QLabel("No directory selected")

        archive_info_layout.addWidget(archive_info_text)
        archive_info_layout.addWidget(self.archive_info_label)
        archive_info_layout.addStretch()

        layout.addWidget(archive_info_group)
        
        # ROI lead image selection
        roi_group = QWidget()
        roi_layout = QHBoxLayout(roi_group)

        roi_label = QLabel("Image of the lead films:")
        roi_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.roi_combo = QComboBox()
        self.roi_combo.currentTextChanged.connect(self.on_roi_image_changed)

        roi_layout.addWidget(roi_label)
        roi_layout.addWidget(self.roi_combo)
        roi_layout.addStretch()

        layout.addWidget(roi_group)

        # ROI image display
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.roi_image_label = QLabel()
        self.roi_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.roi_image_label.setText("No ROI image available")
        self.roi_image_label.setScaledContents(False)
        self.roi_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        image_container_layout.addWidget(self.roi_image_label)
        layout.addWidget(image_container, stretch=1)

        # Lead region selection
        lead_group = QWidget()
        lead_layout = QHBoxLayout(lead_group)

        lead_label = QLabel("Enter mask numbers:")
        lead_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.mask_input = QLineEdit()
        self.mask_input.setPlaceholderText("(e.g., 25-28 or 25,27)")

        lead_layout.addWidget(lead_label)
        lead_layout.addWidget(self.mask_input)
        lead_layout.addStretch()

        layout.addWidget(lead_group)
        
        return panel

    def create_right_panel(self):
        """Create right panel with background settings"""
        panel = QWidget()
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Background selection
        bg_label = QLabel("Background Settings:")
        bg_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(bg_label)
        
        bg_option_frame = QFrame()
        bg_option_layout = QHBoxLayout(bg_option_frame)
        bg_option_layout.setContentsMargins(0, 0, 0, 0)

        self.existing_bg_checkbox = QCheckBox("Select existing background")
        self.existing_bg_combo = QComboBox()
        self.existing_bg_combo.setMinimumWidth(100)
        self.existing_bg_combo.setEnabled(False)

        bg_option_layout.addWidget(self.existing_bg_checkbox)
        bg_option_layout.addWidget(self.existing_bg_combo)
        bg_option_layout.addStretch()
        layout.addWidget(bg_option_frame)
        
        self.compute_bg_checkbox = QCheckBox("Compute new background")
        self.edge_bg_checkbox = QCheckBox("Edge-based detection")
        
        # Background file numbers input
        bg_files_group = QWidget()
        bg_files_layout = QHBoxLayout(bg_files_group)
        
        bg_files_label = QLabel("File numbers for background:")
        self.bg_files_input = QLineEdit()
        self.bg_files_input.setPlaceholderText("e.g., 30-33 or 31,32")
        self.bg_files_input.setEnabled(False)
        
        bg_files_layout.addWidget(bg_files_label)
        bg_files_layout.addWidget(self.bg_files_input)
        
        # Main image set input
        main_files_group = QWidget()
        main_files_layout = QHBoxLayout(main_files_group)
        
        main_files_label = QLabel("File numbers for main image set:")
        main_files_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.main_files_input = QLineEdit()
        self.main_files_input.setPlaceholderText("e.g., 1-28 or 1,10,20")
        self.main_files_input.textChanged.connect(self.update_film_count)
        
        main_files_layout.addWidget(main_files_label)
        main_files_layout.addWidget(self.main_files_input)
        
        # Calibration plot checkbox
        self.include_calib_checkbox = QCheckBox("Include calibration plot in the pdf report")
        self.include_calib_checkbox.setStyleSheet("font-size: 16px;")
        
        # Notes section
        notes_group = QWidget()
        notes_layout = QVBoxLayout(notes_group)
        
        self.film_count_label = QLabel("Notes for each film (0 films total):")
        self.film_count_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Optional notes separated by commas")
        
        notes_layout.addWidget(self.film_count_label)
        notes_layout.addWidget(self.notes_input)
        
        # Add widgets to layout
        layout.addWidget(self.existing_bg_checkbox)
        layout.addWidget(self.existing_bg_combo)
        layout.addWidget(self.compute_bg_checkbox)
        layout.addWidget(self.edge_bg_checkbox)
        layout.addWidget(bg_files_group)
        layout.addWidget(main_files_group)
        layout.addWidget(self.include_calib_checkbox)
        layout.addWidget(notes_group)
        
        # Connect signals
        self.existing_bg_checkbox.toggled.connect(self.on_background_option_changed)
        self.compute_bg_checkbox.toggled.connect(self.on_background_option_changed)
        self.edge_bg_checkbox.toggled.connect(self.on_background_option_changed)
        
        layout.addStretch()
        
        # Start analysis button
        self.start_btn = QPushButton("Start analysis")
        self.start_btn.setMinimumSize(400, 80)
        self.start_btn.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        self.start_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.start_btn)
        
        return panel
    
    def create_footer(self):
        """Create footer with back and forward buttons"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        back_btn = QPushButton("⬅️")
        back_btn.setFixedSize(40, 40)
        back_btn.clicked.connect(lambda: self.main_window.stacked_widget.setCurrentWidget(
            self.main_window.main_screen))
        back_btn.setStyleSheet("""
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
        """)
        
        forward_btn = QPushButton("➡️")
        forward_btn.setFixedSize(40, 40)
        forward_btn.clicked.connect(lambda: self.main_window.stacked_widget.setCurrentWidget(
            self.main_window.progress_screen))
        forward_btn.setStyleSheet("""
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
        """)
        
        footer_layout.addWidget(back_btn)
        footer_layout.addWidget(forward_btn)
        footer_layout.addStretch()
        
        return footer
    
    # Data loading methods
    def load_initial_data(self):
        """Load initial data when screen is created"""
        self.load_calibrated_directories()
        self.load_background_files()
        self.load_roi_files()
    
    def load_calibrated_directories(self):
        """Load all calibrated directories into combo box"""
        current_dir = os.getcwd()
        parent_dir = os.path.abspath('..')
        
        search_dirs = [current_dir, parent_dir]
        calibrated_dirs = []
        
        for search_dir in search_dirs:
            pattern = os.path.join(search_dir, '*_CALIBRATED')
            found_dirs = glob.glob(pattern)
            for dir_path in found_dirs:
                if os.path.isdir(dir_path):
                    relative_path = os.path.relpath(dir_path, current_dir)
                    calibrated_dirs.append((relative_path, dir_path))
        
        self.data_dir_combo.clear()
        if len(calibrated_dirs) == 1:
            relative_path, absolute_path = calibrated_dirs[0]
            self.data_dir_combo.addItem(relative_path, absolute_path)
            self.extraction_timer.start(3000)
        elif len(calibrated_dirs) > 1:
            for relative_path, absolute_path in calibrated_dirs:
                self.data_dir_combo.addItem(relative_path, absolute_path)
        else:
            self.data_dir_combo.addItem("No calibrated directories found")
            self.archive_info_label.setText("No directories available")

    def load_background_files(self):
        """Load existing background files from scripts directory"""
        scripts_dir = os.path.join(os.getcwd(), 'scripts')
        if not os.path.exists(scripts_dir):
            scripts_dir = os.getcwd()
        
        bgnd_files = glob.glob(os.path.join(scripts_dir, '*bgnd*.mat'))
        
        self.existing_bg_combo.clear()
        if bgnd_files:
            self.existing_bg_combo.addItems([os.path.basename(f) for f in bgnd_files])
            self.existing_bg_checkbox.setEnabled(True)
        else:
            self.existing_bg_combo.addItem("No background files found")
            self.existing_bg_checkbox.setEnabled(False)
    
    def load_roi_files(self):
        """Load ROI lead image files from !ROIlead subdirectory"""
        current_dir = os.getcwd()
        roi_dir = os.path.join(current_dir, '!ROIlead')
        
        if not os.path.exists(roi_dir):
            self.roi_combo.clear()
            self.roi_combo.addItem("!ROIlead directory not found")
            self.roi_image_label.setText("No ROI image available")
            return
        
        roi_png_files = glob.glob(os.path.join(roi_dir, 'ROIlead_*.png'))
        
        valid_roi_files = []
        for png_file in roi_png_files:
            base_name = os.path.splitext(png_file)[0]
            mat_file = base_name + '.mat'
            if os.path.exists(mat_file):
                valid_roi_files.append((png_file, mat_file))
        
        self.roi_combo.clear()
        if valid_roi_files:
            for png_file, mat_file in valid_roi_files:
                display_name = os.path.basename(png_file)
                self.roi_combo.addItem(display_name, (png_file, mat_file))
            
            self.on_roi_image_changed(self.roi_combo.currentText())
        else:
            self.roi_combo.addItem("No ROI files found")
            self.roi_image_label.setText("No ROI image available")
    
    # Event handlers
    def on_data_directory_changed(self, text):
        """Handle directory selection change"""
        if text == "No calibrated directories found":
            self.archive_info_label.setText("No directories available")
            return
        
        self.extraction_timer.stop()
        self.archive_info_label.setText("Preparing extraction...")
        self.extraction_timer.start(3000)
    
    def extract_archive(self):
        """Extract archive and count data files"""
        current_text = self.data_dir_combo.currentText()
        if current_text == "No calibrated directories found":
            self.archive_info_label.setText("No directories available")
            return
            
        current_data = self.data_dir_combo.currentData()
        if not current_data:
            self.archive_info_label.setText("No directory selected")
            return
            
        calibrated_dir = current_data
        
        # Check for existing dat files first
        dat_files = glob.glob(os.path.join(calibrated_dir, "*.dat"))
        if dat_files:
            self.archive_info_label.setText(f"{len(dat_files)} data files available")
            return
        
        tar_files = glob.glob(os.path.join(calibrated_dir, "experimental_films_data.tar.gz"))
        if not tar_files:
            self.archive_info_label.setText("Archive file not found")
            return
        
        self.archive_info_label.setText("Extracting archive...")
        
        try:
            with tarfile.open(tar_files[0], 'r') as tar:
                tar.extractall(path=calibrated_dir)
            
            dat_files = glob.glob(os.path.join(calibrated_dir, "*.dat"))
            self.archive_info_label.setText(f"{len(dat_files)} data files extracted")
            
        except Exception as e:
            self.archive_info_label.setText(f"Extraction failed: {str(e)}")

    def on_roi_image_changed(self, text):
        """Handle ROI image selection change"""
        if not text or text == "No ROI files found":
            self.roi_image_label.clear()
            self.roi_image_label.setText("No ROI image available")
            self.current_roi_pixmap = None
            return
            
        current_data = self.roi_combo.currentData()
        if not current_data:
            return
            
        png_file, mat_file = current_data
        
        try:
            original_pixmap = QPixmap(png_file)
            if not original_pixmap.isNull():
                self.current_roi_pixmap = original_pixmap
                available_height = self.roi_image_label.height()
                
                if available_height <= 0:
                    QTimer.singleShot(50, lambda: self.on_roi_image_changed(text))
                    return
                
                scaled_pixmap = self.scale_image_to_panel_height(original_pixmap)
                self.roi_image_label.setPixmap(scaled_pixmap)
            else:
                self.roi_image_label.setText("Could not load image")
                self.current_roi_pixmap = None
        except Exception as e:
            self.roi_image_label.setText(f"Error loading image: {str(e)}")
            self.current_roi_pixmap = None
             
    def scale_image_to_panel_height(self, pixmap):
        """Scale image to fit panel height while maintaining aspect ratio"""
        if pixmap.isNull():
            return pixmap
        
        available_height = self.roi_image_label.height() or 400  # Fallback height
        device_pixel_ratio = self.devicePixelRatio()
        
        scaled_pixmap = pixmap.scaledToHeight(
            int(available_height * device_pixel_ratio),
            Qt.TransformationMode.SmoothTransformation
        )
        scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
        
        return scaled_pixmap

    def on_background_option_changed(self):
        """Handle background option changes (mutually exclusive)"""
        sender = self.sender()
        
        if sender.isChecked():
            if sender != self.existing_bg_checkbox:
                self.existing_bg_checkbox.setChecked(False)
            if sender != self.compute_bg_checkbox:
                self.compute_bg_checkbox.setChecked(False)
            if sender != self.edge_bg_checkbox:
                self.edge_bg_checkbox.setChecked(False)
            
            sender.setChecked(True)
        
        self.existing_bg_combo.setEnabled(self.existing_bg_checkbox.isChecked())
        self.bg_files_input.setEnabled(self.compute_bg_checkbox.isChecked())
    
    def update_film_count(self):
        """Update film count based on input"""
        text = self.main_files_input.text().strip()
        if not text:
            self.film_count_label.setText("Notes for each film (0 films total):")
            return
            
        count = 0
        parts = text.replace(" ", "").split(",")
        for part in parts:
            if "-" in part:
                try:
                    start, end = map(int, part.split("-"))
                    count += end - start + 1
                except:
                    pass
            else:
                try:
                    int(part)
                    count += 1
                except:
                    pass
        
        self.film_count_label.setText(f"Notes for each film ({count} films total):")
    
    # Validation and processing methods
    def validate_inputs(self):
        """Validate user inputs before analysis"""
        if self.data_dir_combo.currentText() == "No calibrated directories found":
            self.show_error("Please select a valid calibrated directory")
            return False

        if not (self.existing_bg_checkbox.isChecked() or 
                self.compute_bg_checkbox.isChecked() or 
                self.edge_bg_checkbox.isChecked()):
            self.show_error("Please select at least one background option")
            return False

        try:
            size_value = float(self.size_input.text())
            if size_value <= 0:
                self.show_error("Size must be a positive number")
                return False
        except ValueError:
            self.show_error("Please enter a valid number for size")
            return False
        
        if not self.main_files_input.text().strip():
            self.show_error("Please enter file numbers for main image set")
            return False
        
        if self.compute_bg_checkbox.isChecked() and not self.bg_files_input.text().strip():
            self.show_error("Please enter file numbers for background when computing new background")
            return False
            
        return True
    
    def parse_number_range(self, text):
        """Parse number range string into list of integers"""
        if not text.strip():
            return []
        
        numbers = []
        parts = text.replace(" ", "").split(",")
        
        for part in parts:
            if "-" in part:
                start, end = map(int, part.split("-"))
                numbers.extend(range(start, end + 1))
            else:
                numbers.append(int(part))
        
        return numbers
    
    def collect_parameters(self):
        """Collect all parameters from the form"""
        # Get selected calibrated directory
        calibrated_dir_text = self.data_dir_combo.currentText()
        if calibrated_dir_text == "No calibrated directories found":
            calibrated_dir = ""
        else:
            dir_name = os.path.basename(calibrated_dir_text.rstrip('/\\'))
            calibrated_dir = f"../{dir_name}/"
        
        # Get ROI image paths
        roi_data = self.roi_combo.currentData()
        roi_image_path = ""
        roi_mat_path = ""
        if roi_data:
            roi_image_abs, roi_mat_abs = roi_data
            roi_image_name = os.path.basename(roi_image_abs)
            roi_mat_name = os.path.basename(roi_mat_abs)
            roi_image_path = f"..//!ROIlead//{roi_image_name}"
            roi_mat_path = f"..//!ROIlead//{roi_mat_name}"
        
        # Parse selected masks
        mask_text = self.mask_input.text().strip()
        if mask_text:
            try:
                selected_masks = self.parse_number_range(mask_text)
                if len(selected_masks) == 1:
                    selected_masks = selected_masks[0]
            except:
                selected_masks = mask_text
        else:
            selected_masks = ""
        
        # Parse main file numbers
        main_nums = self.parse_number_range(self.main_files_input.text().strip())
        
        # Parse background file numbers
        bg_nums = []
        if self.compute_bg_checkbox.isChecked():
            bg_nums = self.parse_number_range(self.bg_files_input.text().strip())
        
        # Parse notes
        notes_text = self.notes_input.toPlainText().strip()
        if notes_text:
            film_notes = [note.strip() for note in notes_text.split(',')]
            while len(film_notes) < len(main_nums):
                film_notes.append("")
        else:
            film_notes = [""] * len(main_nums)
        
        # Determine background choice
        bgnd_choice = "none"
        bgnd_file = ""
        
        if self.existing_bg_checkbox.isChecked():
            bgnd_choice = "existing"
            bgnd_file = self.existing_bg_combo.currentText()
        elif self.compute_bg_checkbox.isChecked():
            bgnd_choice = "compute"
        elif self.edge_bg_checkbox.isChecked():
            bgnd_choice = "edge"
        
        # Build parameters dictionary
        params = {
            "roi_shape": self.shape_combo.currentText().lower(),
            "roi_size": float(self.size_input.text()),
            "directory_films": calibrated_dir,
            "roi_image_path": roi_image_path,
            "roi_mat_path": roi_mat_path,
            "selected_masks": selected_masks,
            "bgnd_choice": bgnd_choice,
            "bgnd_file": bgnd_file,
            "bg_nums": bg_nums,
            "main_nums": main_nums,
            "include_calib_plot": 1 if self.include_calib_checkbox.isChecked() else 0,
            "film_notes": film_notes
        }
        
        return params
        
    def start_analysis(self):
        """Start the analysis process"""
        if not self.validate_inputs():
            return
        
        params = self.collect_parameters()
        
        # Save parameters to JSON file
        scripts_dir = os.path.join(os.getcwd(), 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        
        json_filename = "get_user_inputs.json"
        json_path = os.path.join(scripts_dir, json_filename)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(params, f, separators=(',', ':'))
        except Exception as e:
            self.show_error(f"Failed to save parameters: {str(e)}")
            return
        
        # Navigate to progress screen and start processing
        self.main_window.stacked_widget.setCurrentWidget(
            self.main_window.progress_screen)
        self.main_window.progress_screen.start_analysis_process()

    # Utility methods
    def show_error(self, message):
        """Show error message dialog"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Input Error")
        msg.setText(message)
        msg.exec()
    
    def show_instructions(self):
        """Navigate to instructions screen"""
        if self.main_window:
            self.main_window.stacked_widget.setCurrentWidget(
                self.main_window.instruction_screen)

    # Event overrides
    def showEvent(self, event):
        """Refresh data when screen becomes visible"""
        super().showEvent(event)
        # Save current selections
        saved_data_dir = self.data_dir_combo.currentText()
        saved_roi = self.roi_combo.currentText()
        saved_bg = self.existing_bg_combo.currentText()
        saved_shape = self.shape_combo.currentText()
        
        self.load_calibrated_directories()
        self.load_background_files()
        self.load_roi_files()
        
        # Restore selections
        data_index = self.data_dir_combo.findText(saved_data_dir)
        if data_index >= 0:
            self.data_dir_combo.setCurrentIndex(data_index)
        
        roi_index = self.roi_combo.findText(saved_roi)
        if roi_index >= 0:
            self.roi_combo.setCurrentIndex(roi_index)
        
        bg_index = self.existing_bg_combo.findText(saved_bg)
        if bg_index >= 0:
            self.existing_bg_combo.setCurrentIndex(bg_index)
        
        shape_index = self.shape_combo.findText(saved_shape)
        if shape_index >= 0:
            self.shape_combo.setCurrentIndex(shape_index)

    def focusInEvent(self, event):
        """Refresh data when screen gains focus"""
        super().focusInEvent(event)
        # Save current selections
        saved_data_dir = self.data_dir_combo.currentText()
        saved_roi = self.roi_combo.currentText()
        saved_bg = self.existing_bg_combo.currentText()
        saved_shape = self.shape_combo.currentText()
        
        self.load_calibrated_directories()
        self.load_background_files()
        self.load_roi_files()
        
        # Restore selections
        data_index = self.data_dir_combo.findText(saved_data_dir)
        if data_index >= 0:
            self.data_dir_combo.setCurrentIndex(data_index)
        
        roi_index = self.roi_combo.findText(saved_roi)
        if roi_index >= 0:
            self.roi_combo.setCurrentIndex(roi_index)
        
        bg_index = self.existing_bg_combo.findText(saved_bg)
        if bg_index >= 0:
            self.existing_bg_combo.setCurrentIndex(bg_index)
        
        shape_index = self.shape_combo.findText(saved_shape)
        if shape_index >= 0:
            self.shape_combo.setCurrentIndex(shape_index)