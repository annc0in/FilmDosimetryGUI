import sys
import os
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
# Fix working directory for macOS .app bundle
if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    exe_dir = os.path.dirname(sys.executable)
    app_bundle_dir = exe_dir
    while app_bundle_dir and not app_bundle_dir.endswith('.app'):
        app_bundle_dir = os.path.dirname(app_bundle_dir)
    
    if app_bundle_dir.endswith('.app'):
        base_dir = os.path.dirname(app_bundle_dir)
        os.chdir(base_dir)
import resources_rc
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, 
                            QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QSizePolicy, QSpacerItem, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPalette, QColor
from calibration_screen import CalibrationScreen
from analysis_screen import AnalysisScreen
from processing_screen import ProcessingScreen
from progress_screen import AnalysisProgressScreen

class CollapsibleSection(QWidget):
    """Collapsible UI section with title and content that can be expanded/collapsed"""
    
    def __init__(self, title, content, font_size=16):
        super().__init__()
        self.font_size = font_size
        self.is_expanded = False
        
        # Pre-compute formatted content to avoid repeated processing
        if isinstance(content, str):
            self.formatted_content = self._format_text(content)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header_btn = QPushButton(f"▶ {title}")
        self.header_btn.clicked.connect(self.toggle_section)
        
        self.content_container = QWidget()
        self.content_container.setVisible(False)
        self._setup_content(content)
        
        layout.addWidget(self.header_btn)
        layout.addWidget(self.content_container)
        self._update_theme_styles()
    
    def _setup_content(self, content):
        """Setup content container with proper layout"""
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(20, 5, 15, 15)
        
        if isinstance(content, str):
            self.content_label = QLabel(self.formatted_content)
            self.content_label.setWordWrap(True)
            self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.content_label.setStyleSheet("font-size: 14px; line-height: 1.4;")
            content_layout.addWidget(self.content_label)
        elif isinstance(content, list):
            self.subsections = []
            for subsection in content:
                if isinstance(subsection, tuple) and len(subsection) == 2:
                    sub_section = CollapsibleSection(subsection[0], subsection[1], font_size=14)
                    self.subsections.append(sub_section)
                    content_layout.addWidget(sub_section)
                else:
                    label = QLabel(self._format_text(str(subsection)))
                    label.setWordWrap(True)
                    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    label.setStyleSheet("font-size: 14px; line-height: 1.4;")
                    content_layout.addWidget(label)
    
    def _format_text(self, text):
        """Format text with basic markdown-style formatting"""
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'`([^`]+)`', r'<span class="code">\1</span>', text)
        return text.replace('\n', '<br>')
    
    def _update_theme_styles(self):
        """Update styles based on current system theme"""
        palette = self.palette()
        is_dark_theme = palette.base().color().lightness() < 128

        text_color = "#ffffff" if is_dark_theme else "#000000"
        hover_color = "rgba(255, 255, 255, 0.1)" if is_dark_theme else "rgba(0, 0, 0, 0.05)"
        code_bg = "#404040" if is_dark_theme else "#e6f3ff"
        code_border = "#606060" if is_dark_theme else "#ddd"
        code_text = "#ffffff" if is_dark_theme else "#000000"

        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 10px 5px;
                font-size: {self.font_size}px;
                font-weight: bold;
                text-decoration: underline;
                border: none;
                background-color: transparent;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-radius: 3px;
            }}
        """)

        if hasattr(self, 'content_label'):
            import re
            formatted_text = re.sub(
                r'<span class="code">([^<]+)</span>',
                f'<span style="font-family: Consolas, Monaco, monospace; background-color: {code_bg}; color: {code_text}; padding: 2px 4px; border: 1px solid {code_border}; border-radius: 3px;">\\1</span>',
                self.content_label.text()
            )
            self.content_label.setText(formatted_text)

        if hasattr(self, 'subsections'):
            for subsection in self.subsections:
                subsection._update_theme_styles()
    
    def toggle_section(self):
        """Toggle section visibility and update arrow indicator"""
        self.is_expanded = not self.is_expanded
        self.content_container.setVisible(self.is_expanded)
        arrow = "▼" if self.is_expanded else "▶"
        text = self.header_btn.text()
        self.header_btn.setText(f"{arrow} {text[2:]}")
        
    def update_theme_styles(self):
        """Public interface for theme updates"""
        self._update_theme_styles()

class MainWindow(QMainWindow):
    """Main application window with screen management and navigation"""
    
    # Static instruction data to avoid repeated string processing
    INSTRUCTION_SECTIONS = [
        ("About", "This software performs film dosimetry analysis in two main stages: calibration with dose calculation, and detailed dose distribution analysis. The application uses Octave scripts that can be executed either from the Octave console or through the GUI.<br><br>Source code and documentation: `https://github.com/annc0in/FilmDosimetryGUI`"),
        ("Required Directory Structure", "The application requires a main directory containing:<br><br>**Essential files:**<br>• `FilmDosimetryGUI` — GUI executable file<br>• Script `Check_calibration_XD_add_films.m` and `functions` folder with supporting functions (5)<br>• `scripts` folder containing script `analyze_shots_films_MOD_centering_Charge_Density_bgnd.m` and its `functions` subfolder (6 supporting functions)<br><br>**Input data folders:**<br>• Calibration films directories (format: `Calibration_*`)<br>&nbsp;&nbsp;- Contains: TIFF film files + Excel file (.xlsx) with Delivered Doses in column F starting from row 2<br>• Experimental films directories<br>&nbsp;&nbsp;- Contains: TIFF film files"),
        ("Output Files Generated", "**After Calibration & Film Processing:**<br>• `!CalibrationCurves` — PNG curve images and corresponding MAT files (reusable)<br>• `!Processed` — Combined PNG images of all processed films<br>• `!ROIlead` — PNG images with lead region highlighted + corresponding MAT files (used in Stage 2)<br>• `[ExperimentalFilmsFolder]_CALIBRATED` — Contains `experimental_films_data.tar.gz` archive with DAT files for each processed film<br>• Optional: `check_Calibration_*.png` (if calibration validation was selected)<br>• Temporary files: `user_inputs.json`, `octave_gui.txt` (automatically deleted upon successful completion)<br><br>**After Image Analysis & Dose Calculation:**<br>• `scripts/images` — PNG images showing dose cross-sections (with background, without background, and CD — 3 images per film)<br>• `scripts/analysis_report.pdf` — 3-page analysis report<br>• Optional: `scripts/bgnd_avg_XX-YY_from_[ExperimentalFilmFolder].mat` — Average background file (reusable if computed)<br>• Temporary files: `scripts/get_user_inputs.json`, `scripts/temp_analysis_results.txt` (automatically deleted upon successful completion)"),
        ("User Interface", [
            ("Main Screen", "Choose between two processing stages:<br>• **Calibration & Film Processing**<br>• **Image Analysis & Dose Calculation**<br><br>Access this instruction guide via the button in the upper-right corner (available from any screen).<br><br>**Navigation**<br>Each stage has two screens: input parameters and real-time processing results. Navigate using:<br>• **Back** button (bottom left) — return to previous screen<br>• **Forward** button (bottom left) — return to results screen<br>• **Home** button (bottom right) — return to main screen"),
            ("Calibration && Film Processing", "**Purpose**<br>Creates calibration curve from known dose films and applies it to experimental films to calculate dose values.<br><br>**Required Input Parameters**<br><br>**1. Calibration Curve Selection:**<br>• Use existing calibration curve, OR<br>• Create new calibration curve by specifying:<br>&nbsp;&nbsp;- Calibration films directory<br>&nbsp;&nbsp;- Polynomial degree (default is 8)<br>&nbsp;&nbsp;- Enable calibration validation (optional)<br><br>**2. Experimental Films Directory**<br>Select folder containing films to be analyzed.<br><br>**3. Charge Values**<br>Enter charges separated by commas, or \"0\" for all zero values.<br><br>**4. Lead Region Detection**<br>• **full** — automatic full detection<br>• **rectangle** — specify height in mm<br><br>**Processing Interface**<br>• **Left panel:** Real-time console output and calibration curve display<br>• **Right panel:** Table showing calculated doses and input charges<br>• **Bottom:** Timer and Pause button (stops processing permanently)"),
            ("Image Analysis && Dose Calculation", "**Purpose**<br>Performs detailed dose distribution analysis using calibrated films from Calibration & Film Processing.<br><br>**Required Input Parameters**<br><br>**1. Region of Interest (ROI) Definition**<br>• Shape: Circle or Square<br>• Size: Radius (circle) or width (square) in mm<br><br>**2. Calibrated Films Directory**<br>Select directory ending with `_CALIBRATED` from Calibration & Film Processing output.<br><br>**3. Lead Region Reference (Optional)**<br>• Select PNG image from `!ROIlead` folder<br>• Specify film numbers for intersection analysis (single number or comma-separated)<br><br>**4. Background Correction**<br>Choose one option:<br>• **Existing background** — use previously calculated background file<br>• **Calculate new background** — specify film numbers from `_CALIBRATED` directory<br>• **Edge-based background** — automatic edge detection<br><br>**5. Analysis Films**<br>Specify film numbers for main dose analysis (comma-separated).<br><br>**6. PDF Report Options**<br>• Include calibration coefficient plot: Yes/No<br><br>**7. Notes (Optional)**<br>Add comments for the analysis report (comma-separated).<br><br>**Processing Interface**<br>• **Left panel:** Real-time console output<br>• **Right panel:** Results table with doses, charges, and statistical parameters for each film<br>• **Bottom:** Timer and Pause button (stops processing permanently)")
        ]),
        ("Error Handling", "• Missing or incorrect required parameters trigger warning messages before processing<br>• Console output displays detailed error information<br>• Processing cannot be resumed after using Pause button"),
        ("Support", "For errors, questions, or suggestions, please contact: `aqcaise5@gmail.com`. Subject line: \"FilmDosimetryGUI\"")
    ]
    
    def __init__(self):
        super().__init__()
        self.instruction_sections = []
        self.previous_screen_index = 0
        self._setup_ui()
        self._setup_screens()
        self._update_theme()
    
    def _setup_ui(self):
        """Initialize main window UI components"""
        app_icon = QIcon(":/_icons/icon.png")
        self.setWindowIcon(app_icon)
        QApplication.instance().setWindowIcon(app_icon)

        self.setWindowTitle("FilmDosimetryGUI")
        self.setMinimumSize(800, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
    
    def _setup_screens(self):
        """Create and configure all application screens"""
        self.main_screen = self._create_main_screen()
        self.instruction_screen = self._create_instruction_screen()
        self.calibration_screen = CalibrationScreen(self)
        self.analysis_screen = AnalysisScreen(self)
        self.processing_screen = ProcessingScreen(self)
        self.progress_screen = AnalysisProgressScreen(self)

        screens = [
            self.main_screen, self.instruction_screen, self.analysis_screen,
            self.calibration_screen, self.processing_screen, self.progress_screen
        ]
        
        for screen in screens:
            self.stacked_widget.addWidget(screen)
        
        self.stacked_widget.currentChanged.connect(self._on_screen_changed)
    
    def _update_theme(self):
        """Update UI colors based on system theme"""
        palette = self.palette()
        is_dark = palette.base().color().lightness() < 128
        
        colors = {
            'bg': QColor(30, 30, 30) if is_dark else QColor(255, 255, 255),
            'text': QColor(255, 255, 255) if is_dark else QColor(0, 0, 0),
            'button': QColor(200, 200, 200)
        }
        
        palette.setColor(QPalette.ColorRole.Window, colors['bg'])
        palette.setColor(QPalette.ColorRole.WindowText, colors['text'])
        palette.setColor(QPalette.ColorRole.Base, colors['bg'])
        palette.setColor(QPalette.ColorRole.Text, colors['text'])
        self.setPalette(palette)
        
        button_style = f"""
            QPushButton {{
                background-color: {colors['button'].name()};
                color: black;
                border-radius: 10px;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['button'].lighter(110).name()};
            }}
        """
        self.setStyleSheet(button_style)
        
        # Update instruction sections
        for section in self.instruction_sections:
            section.update_theme_styles()
    
    def _create_main_screen(self):
        """Create the main screen with navigation buttons and logos"""
        screen = QWidget()
        main_layout = QVBoxLayout(screen)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with info button
        header = self._create_header_with_info()
        
        # Center content with logos and buttons
        center_content = self._create_center_content()
        
        # Footer spacer
        footer_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        
        main_layout.addWidget(header)
        main_layout.addWidget(center_content, stretch=1)
        main_layout.addItem(footer_spacer)
        
        return screen
    
    def _create_header_with_info(self):
        """Create header with info button"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        info_btn = QPushButton("ℹ️")
        info_btn.setFixedSize(40, 40)
        info_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.instruction_screen))
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
    
    def _create_center_content(self):
        """Create center content with logos and navigation buttons"""
        center_content = QWidget()
        center_layout = QHBoxLayout(center_content)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # Logo containers
        left_container = self._create_logo_container('left')
        right_container = self._create_logo_container('right')
        
        # Center buttons
        center_container = self._create_button_container()
        
        center_layout.addWidget(left_container, 35)  # 35%
        center_layout.addWidget(center_container, 30)  # 30% 
        center_layout.addWidget(right_container, 35)  # 35%
        
        QTimer.singleShot(0, self._load_logos)
        return center_content
    
    def _create_logo_container(self, side):
        """Create logo container for left or right side"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        logo = QSvgWidget()
        setattr(self, f'{side}_logo', logo)
        
        stretch_ratio = 8 if side == 'left' else 9
        layout.addStretch(1)
        layout.addWidget(logo, stretch_ratio)
        layout.addStretch(1)
        
        return container
    
    def _create_button_container(self):
        """Create center container with navigation buttons"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        buttons_config = [
            ("Calibration + Film Processing", 
            "Create or load calibration curves\nProcess experimental films\nLead region analysis",
            lambda: self.stacked_widget.setCurrentWidget(self.calibration_screen)),
            ("Image Analysis + Dose Calculation",
            "Background processing\nDose analysis with shape selection\nStatistical calculations", 
            lambda: self.stacked_widget.setCurrentWidget(self.analysis_screen))
        ]
        
        for text, tooltip, callback in buttons_config:
            btn = QPushButton(text)
            btn.setMinimumSize(350, 100)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        return container
    
    def _load_logos(self):
        """Load and scale SVG logos maintaining aspect ratios"""
        available_width = max(200, (self.width() - 400 - 40) // 2)
        
        # CERN logo (square)
        cern_size = int(available_width * 0.7)
        self.left_logo.setFixedSize(cern_size, cern_size)
        self.left_logo.load(":/_logos/CERN.svg")
        
        # CLEAR logo (2.8:1 aspect ratio)
        clear_width = int(available_width * 0.8)
        clear_height = int(clear_width / 2.8)
        self.right_logo.setFixedSize(clear_width, clear_height)
        self.right_logo.load(":/_logos/CLEAR.svg")

    def _on_screen_changed(self, index):
        """Handle screen changes and update window title"""
        if index != self.stacked_widget.indexOf(self.instruction_screen):
            self.previous_screen_index = index
            
        widget = self.stacked_widget.widget(index)
        title = widget.property("window_title")
        self.setWindowTitle(title if title else "FilmDosimetryGUI")
    
    def _create_instruction_screen(self):
        """Create instruction screen with collapsible sections"""
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with info button
        header = self._create_instruction_header()

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        # Create instruction sections
        for title, content in self.INSTRUCTION_SECTIONS:
            section = CollapsibleSection(title, content)
            if title == "User Interface":
                section.toggle_section()
            self.instruction_sections.append(section)
            content_layout.addWidget(section)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)

        # Footer with back button
        footer = self._create_instruction_footer()

        layout.addWidget(header)
        layout.addWidget(scroll_area, stretch=1)
        layout.addWidget(footer)

        return screen
    
    def _create_instruction_header(self):
        """Create instruction screen header"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        info_btn = QPushButton("ℹ️")
        info_btn.setFixedSize(40, 40)
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
    
    def _create_instruction_footer(self):
        """Create instruction screen footer"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        back_btn = QPushButton("⬅️")
        back_btn.setFixedSize(40, 40)
        back_btn.clicked.connect(self.go_back_from_instructions)
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

        footer_layout.addWidget(back_btn)
        footer_layout.addStretch()
        
        return footer

    def go_back_from_instructions(self):
        """Return to previous screen from instructions"""
        if self.previous_screen_index >= 0:
            self.stacked_widget.setCurrentIndex(self.previous_screen_index)

    def resizeEvent(self, event):
        """Handle window resize to update logo sizes"""
        super().resizeEvent(event)
        if hasattr(self, 'left_logo'):
            self._load_logos()

    # Expose methods for compatibility
    def update_theme(self):
        """Public interface for theme updates"""
        self._update_theme()
        
    def create_main_screen(self):
        """Public interface for main screen creation"""
        return self._create_main_screen()
    
    def create_instruction_screen(self):
        """Public interface for instruction screen creation"""
        return self._create_instruction_screen()
    
    def setup_ui(self):
        """Public interface for UI setup"""
        self._setup_ui()
    
    def setup_screens(self):
        """Public interface for screens setup"""
        self._setup_screens()
    
    def load_logos(self):
        """Public interface for logo loading"""
        self._load_logos()
    
    def stacked_widget_changed(self, index):
        """Public interface for screen change handling"""
        self._on_screen_changed(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())