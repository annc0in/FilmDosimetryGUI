import os
import platform
import json
import glob
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QSizePolicy, QComboBox, QCheckBox, 
                            QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

class CalibrationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_cal_pixmap = None
        self.setProperty("window_title", "Calibration & Film Processing")
        
        # Cache for directory listings
        self._dir_cache = None
        self._dir_cache_time = 0
        
        self.create_ui()
        
    def create_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        header = self._create_header()
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(30)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        
        content_layout.addWidget(left_panel, stretch=1)
        content_layout.addWidget(right_panel, stretch=1)
        
        footer = self._create_footer()
        
        main_layout.addWidget(header)
        main_layout.addWidget(content_widget, stretch=1)
        main_layout.addWidget(footer)
        
        # Set proper stretch factors
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)
        main_layout.setStretch(2, 0)
    
    def _create_header(self):
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
    
    def _create_left_panel(self):
        left_panel = QWidget()
        left_panel.setMinimumWidth(0)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)

        # Calibration curve selection
        cal_label = QLabel("Select Calibration Curve")
        cal_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.cal_curve_combo = QComboBox()
        self.cal_curve_combo.setMinimumHeight(40)
        self.cal_curve_combo.currentTextChanged.connect(self._on_calibration_selection_changed)

        # Image display
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cal_image_label = QLabel()
        self.cal_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cal_image_label.setText("No calibration curve selected")
        self.cal_image_label.setScaledContents(False)
        self.cal_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        image_container_layout.addWidget(self.cal_image_label)
        left_layout.addWidget(cal_label)
        left_layout.addWidget(self.cal_curve_combo)
        left_layout.addWidget(image_container, stretch=1)
        
        return left_panel
    
    def _create_right_panel(self):
        right_panel = QWidget()
        right_panel.setMinimumWidth(0)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        # Create all form elements
        self.create_new_cal_cb = QCheckBox("Create new calibration")
        self.create_new_cal_cb.setStyleSheet("font-size: 16px;")
        self.create_new_cal_cb.toggled.connect(self._on_create_new_calibration_toggled)
        
        sections = [
            self._create_calibration_films_section(),
            self._create_polynomial_degree_section(),
            self._create_validation_checkbox(),
            self._create_experimental_films_section(),
            self._create_films_charges_section(),
            self._create_charges_manual_section(),
            self._create_lead_films_section(),
            self._create_lead_mask_section(),
        ]
        
        right_layout.addWidget(self.create_new_cal_cb)
        for section in sections[:-2]:
            right_layout.addWidget(section)
        
        right_layout.addSpacing(10)
        for section in sections[-2:]:
            right_layout.addWidget(section)
                
        # Add spacer to push content up
        right_layout.addStretch()
        
        # Start processing button
        self.start_processing_btn = QPushButton("Start processing")
        self.start_processing_btn.setMinimumSize(500, 60)
        self.start_processing_btn.setStyleSheet("QPushButton { font-size: 16px; font-weight: bold; padding: 3px; border: none; }")
        self.start_processing_btn.clicked.connect(self.start_calibration_processing)
        right_layout.addWidget(self.start_processing_btn)
        
        return right_panel
    
    def _create_calibration_films_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Calibration Films:")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        label.setFixedWidth(300)
        
        self.cal_films_combo = QComboBox()
        self.cal_films_combo.setMinimumHeight(40)
        self.cal_films_combo.setEnabled(False)
        
        layout.addWidget(label)
        layout.addWidget(self.cal_films_combo, stretch=1)
        return widget
    
    def _create_polynomial_degree_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Polynomial degree for calibration curve:")
        label.setStyleSheet("font-size: 14px;")
        label.setFixedWidth(300)
        
        self.polynomial_degree_combo = QComboBox()
        self.polynomial_degree_combo.setMinimumHeight(35)
        self.polynomial_degree_combo.addItems([str(i) for i in range(1, 16)])
        self.polynomial_degree_combo.setCurrentIndex(7)  # Default to 8
        self.polynomial_degree_combo.setEnabled(False)
        
        layout.addWidget(label)
        layout.addWidget(self.polynomial_degree_combo, stretch=1)
        return widget
    
    def _create_validation_checkbox(self):
        self.validate_cal_cb = QCheckBox("Validate calibration on reference films")
        self.validate_cal_cb.setStyleSheet("font-size: 14px;")
        self.validate_cal_cb.setEnabled(False)
        return self.validate_cal_cb
    
    def _create_experimental_films_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Experimental Films:")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        label.setFixedWidth(300)
        
        self.exp_films_combo = QComboBox()
        self.exp_films_combo.setMinimumHeight(40)
        self.exp_films_combo.currentTextChanged.connect(self._on_experimental_films_changed)
        
        layout.addWidget(label)
        layout.addWidget(self.exp_films_combo, stretch=1)
        return widget
    
    def _create_films_charges_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.films_count_label = QLabel("Found 0 films. Data set with charges:")
        self.films_count_label.setStyleSheet("font-size: 14px;")
        self.films_count_label.setFixedWidth(250)
        
        self.charges_preset_combo = QComboBox()
        self.charges_preset_combo.setMinimumHeight(35)
        self.charges_preset_combo.addItem("(No presets available)")
        self.charges_preset_combo.setEnabled(False)
        
        layout.addWidget(self.films_count_label)
        layout.addWidget(self.charges_preset_combo, stretch=1)
        return widget
    
    def _create_charges_manual_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel('Or enter charges manually ("0" for all zeros):')
        label.setStyleSheet("font-size: 14px;")
        label.setFixedWidth(300)
        label.setWordWrap(True)
        
        self.charges_input = QLineEdit()
        self.charges_input.setMinimumHeight(35)
        self.charges_input.setPlaceholderText("e.g., 11.88,10.17,7.73 or 0")
        
        layout.addWidget(label)
        layout.addWidget(self.charges_input, stretch=1)
        return widget
    
    def _create_lead_films_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Enter the numbers of the films containing lead:")
        label.setStyleSheet("font-size: 14px;")
        label.setFixedWidth(300)
        label.setWordWrap(True)
        
        self.lead_films_input = QLineEdit()
        self.lead_films_input.setMinimumHeight(35)
        self.lead_films_input.setPlaceholderText("e.g., 25-28 or 25,26,27,28")
        
        layout.addWidget(label)
        layout.addWidget(self.lead_films_input, stretch=1)
        return widget
    
    def _create_lead_mask_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Lead mask type:")
        label.setStyleSheet("font-size: 14px;")
        label.setFixedWidth(100)
        
        self.lead_mask_combo = QComboBox()
        self.lead_mask_combo.setMinimumHeight(35)
        self.lead_mask_combo.addItems(["full", "rectangle"])
        self.lead_mask_combo.currentTextChanged.connect(self._on_lead_mask_type_changed)
        
        height_label = QLabel("Height (mm):")
        height_label.setStyleSheet("font-size: 14px;")
        height_label.setFixedWidth(80)
        
        self.rect_height_input = QLineEdit()
        self.rect_height_input.setMinimumHeight(35)
        self.rect_height_input.setPlaceholderText("e.g., 2.0")
        self.rect_height_input.setEnabled(False)
        
        layout.addWidget(label)
        layout.addWidget(self.lead_mask_combo)
        layout.addSpacing(20)
        layout.addWidget(height_label)
        layout.addWidget(self.rect_height_input, stretch=1)
        return widget
    
    def _create_footer(self):
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        back_btn = QPushButton("⬅️")
        back_btn.setFixedSize(40, 40)
        back_btn.clicked.connect(self.go_back)
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
        forward_btn.clicked.connect(self.go_forward)
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
    
    def go_forward(self):
        """Navigate forward to processing screen"""
        if self.main_window and hasattr(self.main_window, 'processing_screen'):
            self.main_window.stacked_widget.setCurrentWidget(self.main_window.processing_screen)
    
    def _initialize_data(self):
        """Initialize data after UI is ready"""
        # Save current selections
        saved_cal = self.cal_curve_combo.currentText()
        saved_cal_dir = self.cal_films_combo.currentText()
        saved_exp_dir = self.exp_films_combo.currentText()
        saved_preset = self.charges_preset_combo.currentText()
        
        self._populate_calibration_curves()
        self._populate_directory_lists()
        
        # Restore selections if items still exist
        cal_index = self.cal_curve_combo.findText(saved_cal)
        if cal_index >= 0:
            self.cal_curve_combo.setCurrentIndex(cal_index)
        
        cal_dir_index = self.cal_films_combo.findText(saved_cal_dir)
        if cal_dir_index >= 0:
            self.cal_films_combo.setCurrentIndex(cal_dir_index)
        
        exp_dir_index = self.exp_films_combo.findText(saved_exp_dir)
        if exp_dir_index >= 0:
            self.exp_films_combo.setCurrentIndex(exp_dir_index)
        
        preset_index = self.charges_preset_combo.findText(saved_preset)
        if preset_index >= 0:
            self.charges_preset_combo.setCurrentIndex(preset_index)
    
    def _populate_calibration_curves(self):
        """Populate calibration curves dropdown"""
        calibration_dir = '!CalibrationCurves/'
        self.cal_curve_combo.clear()
        
        if not os.path.exists(calibration_dir):
            self.cal_curve_combo.addItem("(No calibration curves found)")
            return
        
        # Use glob for better performance
        pattern = os.path.join(calibration_dir, 'polynomial_calibration_*.png')
        png_files = glob.glob(pattern)
        
        valid_calibrations = []
        for png_file in png_files:
            base_name = os.path.basename(png_file)
            mat_file = os.path.join(calibration_dir, f"data_{base_name[:-4]}.mat")
            if os.path.exists(mat_file):
                valid_calibrations.append(base_name)
        
        if valid_calibrations:
            self.cal_curve_combo.addItems(valid_calibrations)
        else:
            self.cal_curve_combo.addItem("(No valid calibration curves found)")

    def _populate_directory_lists(self):
        """Populate directory dropdowns with caching"""
        import time
        current_time = time.time()
        
        # Use cache if fresh (within 5 seconds)
        if self._dir_cache and (current_time - self._dir_cache_time < 5):
            available_dirs = self._dir_cache
        else:
            project_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
            excluded_dirs = {'!CalibrationCurves', '!Processed', '!ROIlead', 'functions', 'scripts', 'FilmDosimetryGUI.app'}
            available_dirs = [d for d in project_dirs 
                            if d not in excluded_dirs and not d.endswith('_CALIBRATED')]
            
            self._dir_cache = available_dirs
            self._dir_cache_time = current_time
        
        self.cal_films_combo.clear()
        self.exp_films_combo.clear()
        
        if available_dirs:
            self.cal_films_combo.addItems(available_dirs)
            self.exp_films_combo.addItems(available_dirs)
        else:
            self.cal_films_combo.addItem("(No directories found)")
            self.exp_films_combo.addItem("(No directories found)")
    
    def _on_calibration_selection_changed(self, text):
        """Handle calibration curve selection change"""
        if not text or text.startswith("("):
            self.cal_image_label.clear()
            self.cal_image_label.setText("No calibration curve selected")
            self.current_cal_pixmap = None
            return
            
        image_path = os.path.join('!CalibrationCurves', text)
        if not os.path.exists(image_path):
            self.cal_image_label.setText("Image not found")
            self.current_cal_pixmap = None
            return
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.current_cal_pixmap = pixmap
            self._display_scaled_image()
        else:
            self.cal_image_label.setText("Could not load image")
            self.current_cal_pixmap = None

    def _display_scaled_image(self):
        """Display scaled calibration image"""
        if not self.current_cal_pixmap:
            return
            
        available_height = self.cal_image_label.height()
        if available_height <= 0:
            QTimer.singleShot(50, self._display_scaled_image)
            return
        
        device_pixel_ratio = self.devicePixelRatio()
        scaled_pixmap = self.current_cal_pixmap.scaledToHeight(
            int(available_height * device_pixel_ratio),
            Qt.TransformationMode.SmoothTransformation
        )
        scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
        self.cal_image_label.setPixmap(scaled_pixmap)

    def _on_create_new_calibration_toggled(self, checked):
        """Handle new calibration checkbox toggle"""
        self.cal_films_combo.setEnabled(checked)
        self.polynomial_degree_combo.setEnabled(checked)
        self.validate_cal_cb.setEnabled(checked)
        self.cal_curve_combo.setEnabled(not checked)
        
        if checked:
            self.cal_image_label.setText("New calibration will be created")
            self.current_cal_pixmap = None
        else:
            self._on_calibration_selection_changed(self.cal_curve_combo.currentText())

    def _on_experimental_films_changed(self, directory):
        """Update film count when experimental directory changes"""
        if directory and not directory.startswith("("):
            pattern = os.path.join(directory, "*.tif*")
            tiff_files = glob.glob(pattern)
            count = len(tiff_files)
            self.films_count_label.setText(f"Found {count} films. Data set with charges:")
        else:
            self.films_count_label.setText("Found 0 films. Data set with charges:")

    def _on_lead_mask_type_changed(self, mask_type):
        """Handle lead mask type selection change"""
        self.rect_height_input.setEnabled(mask_type == "rectangle")
        if mask_type == "full":
            self.rect_height_input.clear()

    def _validate_inputs(self):
        """Validate all inputs before processing"""
        # Calibration selection
        if not self.create_new_cal_cb.isChecked() and self.cal_curve_combo.currentText().startswith('('):
            return "Please select an existing calibration curve or check 'Create new calibration'"
        
        # Charges input
        charges_text = self.charges_input.text().strip()
        if not charges_text:
            return "Please enter charge values"
        
        if charges_text != "0":
            try:
                clean_text = charges_text.replace('[', '').replace(']', '')
                [float(x.strip()) for x in clean_text.split(',') if x.strip()]
            except ValueError:
                return "Invalid charges format"
        
        # Lead films input
        lead_text = self.lead_films_input.text().strip()
        if not lead_text:
            return "Please enter lead film numbers"
        
        try:
            if '-' in lead_text:
                parts = lead_text.split('-')
                if len(parts) != 2:
                    return "Invalid range format"
                start, end = int(parts[0].strip()), int(parts[1].strip())
                if start > end:
                    return "Invalid range: start > end"
            else:
                [int(x.strip()) for x in lead_text.split(',') if x.strip()]
        except ValueError:
            return "Invalid lead films format"
        
        # Rectangle height validation
        if self.lead_mask_combo.currentText() == "rectangle":
            height_text = self.rect_height_input.text().strip()
            if not height_text:
                return "Please enter height for rectangle mask"
            try:
                height = float(height_text)
                if height <= 0:
                    return "Height must be positive"
            except ValueError:
                return "Invalid height format"
        
        return None

    def start_calibration_processing(self):
        """Start calibration processing after validation"""
        error_msg = self._validate_inputs()
        if error_msg:
            self._show_error_message(error_msg)
            return
        
        # Prepare data
        charges_text = self.charges_input.text().strip()
        lead_text = self.lead_films_input.text().strip()
        
        # Parse charges
        if charges_text == "0":
            exp_dir = self.exp_films_combo.currentText()
            if exp_dir and not exp_dir.startswith("("):
                pattern = os.path.join(exp_dir, "*.tif*")
                tiff_count = len(glob.glob(pattern))
                charges = [0.0] * tiff_count
            else:
                charges = [0.0] * 35
        else:
            charges = [float(x.strip()) 
                      for x in charges_text.replace('[', '').replace(']', '').split(',') 
                      if x.strip()]

        # Parse lead films
        if '-' in lead_text:
            start, end = map(int, lead_text.strip().split('-'))
            lead_films = list(range(start, end + 1))
        else:
            lead_films = [int(x.strip()) for x in lead_text.strip().split(',') if x.strip()]

        # Prepare calibration data
        use_existing = not self.create_new_cal_cb.isChecked()
        
        user_inputs = {
            "use_existing_calibration": use_existing,
            "selected_cal": self.cal_curve_combo.currentText() if use_existing else "",
            "selected_mat": f"data_{self.cal_curve_combo.currentText().replace('.png', '.mat')}" if use_existing else "",
            "cal_dir": "" if use_existing else f"{self.cal_films_combo.currentText().rstrip('/')}/",
            "exp_dir": f"{self.exp_films_combo.currentText().rstrip('/')}/",
            "chargeAll": charges,
            "lead_films": lead_films,
            "validate_calibration": self.validate_cal_cb.isChecked() and not use_existing,
            "polynomial_degree": int(self.polynomial_degree_combo.currentText()),
            "lead_mask_type": self.lead_mask_combo.currentText(),
            "rect_height_mm": float(self.rect_height_input.text().strip()) if self.lead_mask_combo.currentText() == "rectangle" else 0
        }

        # Save and start processing
        with open('user_inputs.json', 'w') as f:
            json.dump(user_inputs, f, indent=2)
        
        if hasattr(self.main_window, 'processing_screen'):
            self.main_window.processing_screen.clear()
            self.main_window.stacked_widget.setCurrentWidget(self.main_window.processing_screen)
            self.main_window.processing_screen.start_processing()
    
    def _show_error_message(self, message):
        """Show error message dialog"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Input Error")
        msg_box.setText(message)
        msg_box.exec()
    
    def show_instructions(self):
        """Navigate to instructions screen"""
        if self.main_window:
            self.main_window.stacked_widget.setCurrentWidget(
                self.main_window.instruction_screen)
    
    def go_back(self):
        """Navigate back to main screen"""
        if self.main_window:
            self.main_window.stacked_widget.setCurrentWidget(self.main_window.main_screen)

    def showEvent(self, event):
        """Refresh data when screen becomes visible"""
        super().showEvent(event)
        self._initialize_data()

    def focusInEvent(self, event):
        """Refresh data when screen gains focus"""
        super().focusInEvent(event)
        self._initialize_data()