import sys, os, random, threading, time, json, requests
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QStackedWidget, QFrame, QButtonGroup, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QSizePolicy, QMessageBox, QComboBox, QProgressBar, QStyleFactory, QScrollArea)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QSize, QRectF, QRect, QPointF, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush, QConicalGradient, QMovie, QLinearGradient, QIcon, QPolygonF

if getattr(sys, 'frozen', False): curr_dir = os.path.dirname(sys.executable)
else:
    try: curr_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError: curr_dir = os.getcwd()
os.chdir(curr_dir)

class NetworkPoller(QThread):
    status_received = Signal(dict); error_occurred = Signal(str)
    def __init__(self, ip): super().__init__(); self.ip = ip; self.is_running = True
    def run(self):
        while self.is_running:
            try:
                res = requests.get(f"http://{self.ip}/status", timeout=2)
                if res.status_code == 200: self.status_received.emit(res.json())
                else: self.error_occurred.emit(f"Server error: {res.status_code}")
            except: self.error_occurred.emit("Searching for Teacher PC...")
            for _ in range(10):
                if not self.is_running: return
                time.sleep(0.1)
    def stop(self): self.is_running = False

class ReadyTask(QThread):
    def __init__(self, ip, roll): super().__init__(); self.ip = ip; self.roll = roll
    def run(self):
        try: requests.post(f"http://{self.ip}/ready", json={"roll": self.roll}, timeout=3)
        except: pass

class SubmitTask(QThread):
    success = Signal(); failed = Signal(str)
    def __init__(self, ip, payload): super().__init__(); self.ip = ip; self.payload = payload
    def run(self):
        try:
            res = requests.post(f"http://{self.ip}/submit", json=self.payload, timeout=5)
            if res.status_code == 200: self.success.emit()
            else: self.failed.emit(f"Server rejected data")
        except Exception as e: self.failed.emit(str(e))

try: import pyttsx3; VOICE_AVAILABLE = True
except ImportError: VOICE_AVAILABLE = False
class VoiceAssistant:
    def __init__(self):
        self.engine = None
        if VOICE_AVAILABLE:
            try: self.engine = pyttsx3.init(); self.engine.setProperty('rate', 160)
            except: pass
    def speak(self, text):
        if not self.engine: return
        t = threading.Thread(target=self._run_speak, args=(text,)); t.daemon = True; t.start()
    def _run_speak(self, text):
        try: eng = pyttsx3.init(); eng.setProperty('rate', 160); eng.say(text); eng.runAndWait()
        except: pass
speaker = VoiceAssistant()

def find_file(filename):
    if os.path.exists(os.path.join(curr_dir, filename)): return os.path.join(curr_dir, filename).replace('\\', '/')
    for ext in [".xlsx", ".csv", ".png", ".jpg", ".gif"]:
        if os.path.exists(os.path.join(curr_dir, filename + ext)): return os.path.join(curr_dir, filename + ext).replace('\\', '/')
    return None

APP_ICON_NAME = "logo.png"
BACKGROUND_IMAGE_NAME = "main page.png"
CINEMATIC_IMAGE_NAME = "file cover.png"
FLAG_GIF_NAME = "flag.gif"
MAX_WARNINGS = 1
DEFAULT_EXAM_IMAGE = "aircraft_painting.png"
COURSE_IMAGE_MAP = { "Aircraft Painting Course": "aircraft_painting.png", "CNC Milling Course": "cnc_milling.png", "Harness Manufacturing Course": "harness_manufacturing.png", "Rubber Technology Course": "rubber_technology.png", "Fundamentals of NDT": "ndt.png", "Rotor and Turbine Balancing": "rotor_turbine.png", "Aviation Standard Pipe Bending": "pipe_bending.png", "Investment Casting": "investment_casting.png", "CAD/CAM Course": "cad_cam.png", "Aviation Standard Riveting": "riveting.png", "Heat & Surface Treatment Course": "heat_treatment.png", "CNC Turning Course": "cnc_turning.png", "Avcs Life Cycle Support, PCB Repair & RF Cable Mfg": "avcs_support.png", "Intro to Avionics Systems & IPC Standards": "avionics.png", "Composite Parts Manufacturing Course": "composites.png", "Conventional Machining Course": "machining.png" }

class FuturisticButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent); self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background-color: #2563EB; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 10px; border: 1px solid #60A5FA; } QPushButton:hover { background-color: #3B82F6; border: 2px solid #00FFFF; } QPushButton:disabled { background-color: #475569; border: 1px solid #334155; color: #94A3B8; }")
        self.anim = QPropertyAnimation(self, b"geometry"); self.anim.setDuration(100); self.anim.setEasingCurve(QEasingCurve.OutQuad); self.original_rect = QRect()
    def enterEvent(self, event):
        if self.isEnabled(): self.original_rect = self.geometry(); self.anim.setStartValue(self.original_rect); self.anim.setEndValue(self.original_rect.adjusted(-3, -3, 3, 3)); self.anim.start()
        super().enterEvent(event)
    def leaveEvent(self, event):
        if self.isEnabled(): self.anim.setStartValue(self.geometry()); self.anim.setEndValue(self.original_rect); self.anim.start()
        super().leaveEvent(event)

class ScanlineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.scan_y = 0; self.timer = QTimer(self); self.timer.timeout.connect(self.update_scan); self.timer.start(50) 
    def update_scan(self): self.scan_y += 2; self.scan_y = 0 if self.scan_y > self.height() else self.scan_y; self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setPen(QColor(0, 0, 0, 30))
        for y in range(0, self.height(), 4): painter.drawLine(0, y, self.width(), y)
        grad = QLinearGradient(0, self.scan_y, 0, self.scan_y + 50); grad.setColorAt(0, QColor(0, 255, 255, 0)); grad.setColorAt(0.5, QColor(0, 255, 255, 20)); grad.setColorAt(1, QColor(0, 255, 255, 0)); painter.fillRect(self.rect(), grad)

class StarParticle:
    def __init__(self, w, h):
        self.x, self.y = random.randint(0, w), random.randint(0, h)
        self.speed, self.size, self.alpha = random.uniform(0.2, 0.8), random.randint(1, 3), random.randint(100, 255)
        self.original_x, self.original_y = self.x, self.y
class BackgroundStars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.stars = []
        self.timer = QTimer(); self.timer.timeout.connect(self.update_stars); self.timer.start(50); self.offset_x, self.offset_y = 0, 0
    def update_mouse_position(self, mouse_pos): self.offset_x = (self.width() / 2 - mouse_pos.x()) * 0.05; self.offset_y = (self.height() / 2 - mouse_pos.y()) * 0.05
    def resizeEvent(self, event): self.stars = [StarParticle(self.width(), self.height()) for _ in range(120)]
    def update_stars(self):
        for s in self.stars:
            s.original_y -= s.speed
            if s.original_y < 0: s.original_y = self.height(); s.original_x = random.randint(0, self.width())
            s.x, s.y = s.original_x + self.offset_x, s.original_y + self.offset_y
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        for s in self.stars: painter.setBrush(QBrush(QColor(255, 255, 255, s.alpha))); painter.setPen(Qt.NoPen); painter.drawEllipse(int(s.x), int(s.y), s.size, s.size)

class OptionCard(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("OptionCard"); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); self.setCursor(Qt.PointingHandCursor); self.setCheckable(True)
        self.lbl = QLabel(); self.lbl.setWordWrap(True); self.lbl.setAttribute(Qt.WA_TransparentForMouseEvents); self.lbl.setStyleSheet("background: transparent; border: none; text-align: left; color: #0F172A; font-weight: 500; font-size: 14px;")
        layout = QVBoxLayout(self); layout.setContentsMargins(15, 12, 15, 12); layout.addWidget(self.lbl); self.toggled.connect(self.update_style)
    def set_text_safely(self, text): self.lbl.setText(text); self.setProperty("original_text", text)
    def update_style(self, checked):
        if checked: self.lbl.setStyleSheet("background: transparent; border: none; text-align: left; color: #1E3A8A; font-weight: 800; font-size: 14px;")
        else: self.lbl.setStyleSheet("background: transparent; border: none; text-align: left; color: #0F172A; font-weight: 500; font-size: 14px;")
    def sizeHint(self): s = super().sizeHint(); s.setHeight(max(s.height(), self.layout().sizeHint().height())); return s

class StudentTerminalSoftware(QMainWindow):
    def __init__(self):
        super().__init__()
        if "Fusion" in QStyleFactory.keys(): QApplication.setStyle(QStyleFactory.create("Fusion"))

        self.server_ip = "127.0.0.1:8000"; self.exam_active = False; self.cheat_warnings = 0; self.current_q = 0; self.time_left = 0
        self.exam_data = []; self.answers = {}; self.flagged_questions = set(); self.warnings = 0; self.selected_course = ""
        self.nav_buttons = []; self.max_visited_q = -1; self.is_confirming = False; self.current_pass_pct = 50; self.is_ready = False 
        self.poller_thread = None; self.submit_thread = None

        self.setWindowTitle("AMSC STUDENT TERMINAL"); self.setMinimumSize(1300, 850); self.resize(1300, 850); self.setMouseTracking(True)
        icon_path = find_file(APP_ICON_NAME)
        if icon_path: self.setWindowIcon(QIcon(icon_path))

        self.init_flag_animation(); self.stars = BackgroundStars(self); self.stars.resize(1300, 850); self.stars.lower(); self.scanlines = ScanlineOverlay(self); self.scanlines.resize(1300, 850); self.scanlines.raise_()
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.init_gatekeeper(); self.init_cinematic(); self.init_dash(); self.init_exam(); self.init_result()

        self.stack.currentChanged.connect(self.update_background_theme); self.stack.setCurrentWidget(self.gatekeeper_page); self.update_background_theme(0)
        self.timer = QTimer(); self.timer.timeout.connect(self.update_timer)

    def paintEvent(self, event):
        if hasattr(self, 'bg_pixmap') and not self.bg_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            scaled_pixmap = self.bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        super().paintEvent(event)

    def get_global_stylesheet(self):
        return """
        QWidget { font-family: 'Segoe UI', sans-serif; } QWidget#DarkPage QLabel { color: #F8FAFC; }
        QFrame#GlassCard, QFrame#Sidebar { background-color: rgba(15, 23, 42, 0.95); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 20px; }
        QWidget#DarkPage QComboBox { background-color: #000000; color: #FFFFFF; border: 2px solid #475569; border-radius: 8px; padding: 5px 20px; font-size: 16px; font-weight: bold; min-height: 50px; }
        QWidget#DarkPage QComboBox QAbstractItemView { background-color: #0F172A; color: #FFFFFF; border: 2px solid #38BDF8; selection-background-color: #2563EB; selection-color: white; }
        QWidget#DarkPage QLineEdit { background-color: #000000; color: #FFFFFF; border: 1px solid #475569; border-radius: 8px; padding: 0px 15px; font-size: 15px; font-weight: bold; height: 40px; }
        QWidget#LightPage { background-color: #FFFFFF; } QWidget#LightPage QLabel { color: #0F172A; } QWidget#ExamPage { background-color: transparent; }
        QFrame#ExamContentCard { background-color: rgba(255, 255, 255, 0.92); border: 1px solid #CBD5E1; border-radius: 20px; }
        QFrame#NavigatorCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 15px; }
        QFrame#ResultCard { background-color: #FFFFFF; border: 2px solid #1E3A8A; border-radius: 20px; }
        QLabel#Header { font-size: 28px; font-weight: 800; letter-spacing: 1px; } QLabel#SubHeader { color: #94A3B8; font-size: 14px; }
        QLabel#LabelTitle { font-size: 12px; font-weight: bold; color: #38BDF8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
        """

    def mouseMoveEvent(self, event): self.stars.update_mouse_position(event.pos()); super().mouseMoveEvent(event)
    def resizeEvent(self, event):
        self.stars.resize(self.size()); self.scanlines.resize(self.size())
        if hasattr(self, 'flag_label') and self.flag_label: self.flag_label.move(self.width() - 220, 20)
        super().resizeEvent(event)

    def update_background_theme(self, index):
        main_bg = find_file(BACKGROUND_IMAGE_NAME)
        final_style = self.get_global_stylesheet()
        self.bg_pixmap = QPixmap() 
        
        if index in [0, 2, 3]: 
            self.stars.show(); self.scanlines.show()
            if self.flag_label: self.flag_label.show()
            if main_bg:
                self.bg_pixmap = QPixmap(main_bg)
                final_style += "\nQMainWindow { background-color: transparent; }"
            else:
                final_style += "\nQMainWindow { background-color: #0F172A; }"
        elif index == 1:
            self.stars.hide(); self.scanlines.hide()
            if self.flag_label: self.flag_label.hide()
            final_style += "\nQMainWindow { background-color: #000000; }"
        elif index == 4: 
            self.stars.hide(); self.scanlines.hide()
            if self.flag_label: self.flag_label.hide()
            img_filename = COURSE_IMAGE_MAP.get(self.selected_course, DEFAULT_EXAM_IMAGE)
            full_img_path = find_file(img_filename)
            if full_img_path:
                self.bg_pixmap = QPixmap(full_img_path)
                final_style += "\nQMainWindow { background-color: transparent; }"
            else:
                final_style += "\nQMainWindow { background-color: #F1F5F9; }"
        else:
            self.stars.hide(); self.scanlines.hide()
            if self.flag_label: self.flag_label.hide()
            final_style += "\nQMainWindow { background-color: #FFFFFF; }"
            
        self.setStyleSheet(final_style); self.repaint()

    def init_flag_animation(self):
        flag_path = find_file(FLAG_GIF_NAME)
        if flag_path:
            self.flag_label = QLabel(self); self.flag_movie = QMovie(flag_path); self.flag_movie.setScaledSize(QSize(200, 120))
            self.flag_label.setMovie(self.flag_movie); self.flag_label.setFixedSize(200, 120); self.flag_opacity = QGraphicsOpacityEffect(); self.flag_opacity.setOpacity(0.9); self.flag_label.setGraphicsEffect(self.flag_opacity); self.flag_movie.start(); self.flag_label.show(); self.flag_label.lower()
        else: self.flag_label = None

    def get_shadow(self): shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(40); shadow.setOffset(0, 10); shadow.setColor(QColor(0, 0, 0, 80)); return shadow
    def show_error(self, title, message): speaker.speak("Attention."); msg = QMessageBox(self); msg.setWindowTitle(title); msg.setText(message); msg.setIcon(QMessageBox.Warning); msg.exec()

    def init_gatekeeper(self):
        self.gatekeeper_page = QWidget(); self.gatekeeper_page.setObjectName("DarkPage"); self.gatekeeper_page.setMouseTracking(True)
        layout = QVBoxLayout(self.gatekeeper_page); layout.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(450, 500); card.setGraphicsEffect(self.get_shadow())
        l = QVBoxLayout(card); l.setSpacing(25); l.setContentsMargins(50, 50, 50, 50)
        logo = QLabel("AMSC"); logo.setObjectName("Logo"); logo.setAlignment(Qt.AlignCenter); logo.setStyleSheet("color: #00FFFF; font-size: 48px; font-weight: 900;")
        sub = QLabel("STUDENT LOGIN TERMINAL"); sub.setObjectName("LabelTitle"); sub.setAlignment(Qt.AlignCenter)
        self.txt_ip = QLineEdit(); self.txt_ip.setPlaceholderText("IP Address & Port (e.g. 192.168.1.5:8000)"); self.txt_ip.setAlignment(Qt.AlignCenter); self.txt_ip.returnPressed.connect(self.connect_server)
        btn = FuturisticButton("CONNECT TO NETWORK"); btn.setFixedHeight(50); btn.clicked.connect(self.connect_server)
        l.addStretch(); l.addWidget(logo); l.addWidget(sub); l.addWidget(self.txt_ip); l.addWidget(btn); l.addStretch(); layout.addWidget(card); self.stack.addWidget(self.gatekeeper_page)

    def init_cinematic(self):
        self.cinematic_page = QWidget(); layout = QVBoxLayout(self.cinematic_page); layout.setAlignment(Qt.AlignCenter); layout.setContentsMargins(0,0,0,0)
        self.lbl_cinematic_img = QLabel(); self.lbl_cinematic_img.setAlignment(Qt.AlignCenter)
        cine_path = find_file(CINEMATIC_IMAGE_NAME)
        if cine_path: pixmap = QPixmap(cine_path); scaled = pixmap.scaled(1300, 850, Qt.KeepAspectRatio, Qt.SmoothTransformation); self.lbl_cinematic_img.setPixmap(scaled)
        layout.addWidget(self.lbl_cinematic_img); self.cinematic_opacity = QGraphicsOpacityEffect(self.cinematic_page); self.cinematic_page.setGraphicsEffect(self.cinematic_opacity); self.stack.addWidget(self.cinematic_page)

    def connect_server(self):
        raw = self.txt_ip.text().strip().replace("http://", "").replace("https://", "").split("/")[0]
        if not raw: self.server_ip = "127.0.0.1:8000"
        elif ":" not in raw: self.server_ip = f"{raw}:8000"
        else: self.server_ip = raw
        speaker.speak("Network Diagnostics Initiated."); self.play_cinematic()

    def play_cinematic(self):
        self.stack.setCurrentWidget(self.cinematic_page); self.cinematic_opacity.setOpacity(0)
        self.anim = QPropertyAnimation(self.cinematic_opacity, b"opacity"); self.anim.setDuration(1500); self.anim.setStartValue(0); self.anim.setEndValue(1); self.anim.setEasingCurve(QEasingCurve.InOutQuad); self.anim.start()
        self.poller_thread = NetworkPoller(self.server_ip); self.poller_thread.status_received.connect(self.handle_server_status); self.poller_thread.error_occurred.connect(self.handle_server_error); self.poller_thread.start()
        QTimer.singleShot(3000, lambda: self.stack.setCurrentWidget(self.page_dash))

    def create_sidebar(self):
        sb = QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(260)
        l = QVBoxLayout(sb); l.setSpacing(15); l.setContentsMargins(20, 40, 20, 20)
        logo = QLabel("AMSC"); logo.setObjectName("Logo"); logo.setStyleSheet("font-size: 32px; color: #00FFFF; font-weight: 800;"); logo.setAlignment(Qt.AlignCenter)
        b1 = QPushButton("Dashboard"); b1.setObjectName("SidebarBtn"); b1.setCursor(Qt.PointingHandCursor)
        l.addWidget(logo); l.addSpacing(40); l.addWidget(b1); l.addStretch(); return sb

    def init_dash(self):
        self.page_dash = QWidget(); self.page_dash.setObjectName("DarkPage"); self.page_dash.setMouseTracking(True)
        layout = QHBoxLayout(self.page_dash); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        content = QWidget(); c_layout = QVBoxLayout(content); c_layout.setContentsMargins(40, 40, 40, 40); c_layout.setSpacing(20)
        head = QHBoxLayout(); titles = QVBoxLayout()
        h1 = QLabel("STUDENT TERMINAL"); h1.setObjectName("Header"); self.h2_status = QLabel("Status: Initiating Secure Uplink..."); self.h2_status.setObjectName("SubHeader")
        titles.addWidget(h1); titles.addWidget(self.h2_status); head.addLayout(titles); head.addStretch()
        
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedWidth(1000); card.setGraphicsEffect(self.get_shadow())
        grid = QGridLayout(card); grid.setContentsMargins(50, 50, 50, 50); grid.setVerticalSpacing(20); grid.setHorizontalSpacing(20)

        def field(lbl, ph, r, c, w=1):
            l = QLabel(lbl); l.setObjectName("LabelTitle"); i = QLineEdit(); i.setPlaceholderText(ph)
            grid.addWidget(l, r, c, 1, w); grid.addWidget(i, r+1, c, 1, w); return i

        self.inp_name = field("CANDIDATE NAME", "Full Name", 0, 0, 2); self.inp_roll = field("ROLL NUMBER", "2026-X", 2, 0, 2)
        l_crs = QLabel("MODULE SELECTION (SYNCED TO TEACHER)"); l_crs.setObjectName("LabelTitle")
        self.inp_crs = QComboBox(); self.inp_crs.addItem("Waiting for Instructor Broadcast..."); self.inp_crs.setDisabled(True)
        grid.addWidget(l_crs, 4, 0, 1, 2); grid.addWidget(self.inp_crs, 5, 0, 1, 2)
        
        self.btn_start = FuturisticButton("WAITING FOR BROADCAST...")
        self.btn_start.setFixedHeight(55); self.btn_start.setDisabled(True); self.btn_start.clicked.connect(self.mark_as_ready)
        grid.addWidget(self.btn_start, 6, 0, 1, 2)
        
        c_layout.addLayout(head); c_layout.addWidget(card); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_dash)

    def mark_as_ready(self):
        if not self.inp_name.text() or not self.inp_roll.text(): self.show_error("Input Error", "Please fill in your Name and Roll Number first!"); return
        self.is_ready = True; self.inp_name.setDisabled(True); self.inp_roll.setDisabled(True)
        self.ready_thread = ReadyTask(self.server_ip, self.inp_roll.text()); self.ready_thread.start()
        self.btn_start.setText("WAITING FOR TEACHER TO START EXAM...")
        self.btn_start.setStyleSheet("QPushButton { background-color: #EF4444; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 10px; border: 2px solid #7F1D1D; }")
        speaker.speak("Candidate Ready. Awaiting Instructor command.")

    def handle_server_status(self, data):
        if data.get("is_active"):
            new_course = data.get("course", "")
            if new_course != self.selected_course and new_course != "":
                self.selected_course = new_course; self.inp_crs.clear(); self.inp_crs.addItem(self.selected_course)
            
            self.exam_data = data.get("questions", []); self.time_left = data.get("duration", 60) * 60; self.current_pass_pct = data.get("pass_pct", 50)
            
            if not self.is_ready:
                self.h2_status.setText("Status: Broadcast Received! Please Mark as Ready."); self.h2_status.setStyleSheet("color: #10B981; font-weight: bold;")
                self.btn_start.setEnabled(True); self.btn_start.setText("MARK AS READY")
            else:
                self.h2_status.setText("Status: Ready. Waiting for Teacher's Start Signal..."); self.h2_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
                
            if data.get("exam_started") == True and self.is_ready:
                self.poller_thread.stop(); self.actual_start_exam()
        else:
            self.h2_status.setText("Status: Connected. Waiting for Instructor to Broadcast..."); self.h2_status.setStyleSheet("color: #38BDF8;"); self.btn_start.setEnabled(False)

    def handle_server_error(self, err_msg): self.h2_status.setText(f"Status: {err_msg}"); self.h2_status.setStyleSheet("color: #EF4444;")

    def init_exam(self):
        self.page_exam = QWidget(); self.page_exam.setObjectName("ExamPage")
        main_layout = QVBoxLayout(self.page_exam); main_layout.setContentsMargins(40, 0, 40, 40); main_layout.addSpacing(110)
        h_layout = QHBoxLayout(); h_layout.setSpacing(25)
        self.exam_card = QFrame(); self.exam_card.setObjectName("ExamContentCard"); self.exam_card.setMinimumHeight(480); self.exam_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); self.exam_card.setGraphicsEffect(self.get_shadow())
        
        ql = QVBoxLayout(self.exam_card); ql.setContentsMargins(50, 40, 50, 40); header = QHBoxLayout()
        self.prog = QProgressBar(); self.prog.setTextVisible(False); self.prog.setFixedWidth(200); self.prog.setStyleSheet("QProgressBar {background: #CBD5E1; border:none; height: 6px; border-radius: 3px;} QProgressBar::chunk {background: #2563EB; border-radius: 3px;}"); self.prog.setRange(0, 10)
        self.lbl_time = QLabel("00:00"); self.lbl_time.setFont(QFont("Segoe UI", 16, QFont.Bold)); self.lbl_time.setStyleSheet("color: #EF4444; border: 1px solid #EF4444; padding: 4px 10px; border-radius: 6px;")
        header.addWidget(self.prog); header.addStretch(); header.addWidget(self.lbl_time); ql.addLayout(header); ql.addSpacing(15)

        self.q_area = QWidget(); self.q_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); q_layout = QVBoxLayout(self.q_area); q_layout.setContentsMargins(0,0,0,0); q_layout.setSpacing(10); q_layout.setAlignment(Qt.AlignTop)
        self.lbl_q = QLabel("Q"); self.lbl_q.setFont(QFont("Segoe UI", 18, QFont.DemiBold)); self.lbl_q.setWordWrap(True); self.lbl_q.setStyleSheet("color: #0F172A; padding: 5px 0px; margin-bottom: 10px;"); self.lbl_q.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); self.lbl_q.setMinimumHeight(60) 
        q_layout.addWidget(self.lbl_q)
        
        self.bg = QButtonGroup(); self.bg.setExclusive(True); self.rbs = []
        for i in range(4): r = OptionCard(); r.setStyleSheet("QPushButton#OptionCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; margin-bottom: 5px; } QPushButton#OptionCard:hover { background-color: #F8FAFC; border: 2px solid #3B82F6; } QPushButton#OptionCard:checked { background-color: #EFF6FF; border: 2px solid #1E3A8A; }"); self.bg.addButton(r, i); q_layout.addWidget(r); self.rbs.append(r)
        self.bg.buttonClicked.connect(self.save_ans); ql.addWidget(self.q_area); ql.addStretch(1) 

        btn_box = QHBoxLayout(); btn_box.setSpacing(15)
        bp = QPushButton("PREV"); bp.setCursor(Qt.PointingHandCursor); bp.setFixedSize(110, 45); bp.clicked.connect(self.prev_q); bp.setStyleSheet("QPushButton { background-color: #10B981; border: 2px solid transparent; font-size: 13px; font-weight: bold; color: white; border-radius: 22px; } QPushButton:hover { border: 2px solid #064E3B; }")
        bn = QPushButton("NEXT"); bn.setCursor(Qt.PointingHandCursor); bn.setFixedSize(120, 45); bn.clicked.connect(self.next_q); bn.setStyleSheet("QPushButton { background-color: #2563EB; border: 2px solid transparent; font-size: 13px; font-weight: bold; color: white; border-radius: 22px; } QPushButton:hover { border: 2px solid #1E3A8A; }")
        self.btn_flag = QPushButton("⚑ FLAG"); self.btn_flag.setCursor(Qt.PointingHandCursor); self.btn_flag.setFixedSize(120, 45); self.btn_flag.clicked.connect(self.flag_current_q); self.btn_flag.setStyleSheet("QPushButton { background-color: #FBBF24; border: 2px solid transparent; font-size: 13px; font-weight: bold; color: black; border-radius: 22px; } QPushButton:hover { border: 2px solid #78350F; }")
        self.bs = QPushButton("FINISH EXAM"); self.bs.setCursor(Qt.PointingHandCursor); self.bs.setFixedSize(150, 45); self.bs.clicked.connect(self.confirm_submit); self.bs.setStyleSheet("QPushButton { background-color: #EF4444; border: 2px solid transparent; font-size: 13px; font-weight: bold; color: white; border-radius: 22px; } QPushButton:hover { border: 2px solid #7F1D1D; }")
        btn_box.addWidget(bp); btn_box.addWidget(bn); btn_box.addWidget(self.btn_flag); btn_box.addStretch(); btn_box.addWidget(self.bs); ql.addLayout(btn_box); h_layout.addWidget(self.exam_card, 7, Qt.AlignTop)

        self.nav_card = QFrame(); self.nav_card.setObjectName("NavigatorCard"); self.nav_card.setFixedWidth(300); self.nav_card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum); nav_layout = QVBoxLayout(self.nav_card); nav_layout.setContentsMargins(20, 20, 20, 20)
        nav_lbl = QLabel("QUESTION NAVIGATOR"); nav_lbl.setAlignment(Qt.AlignCenter); nav_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold)); nav_lbl.setStyleSheet("color: #1E3A8A;"); nav_layout.addWidget(nav_lbl); nav_layout.addSpacing(15)
        self.nav_grid_widget = QWidget(); self.nav_grid = QGridLayout(self.nav_grid_widget); self.nav_grid.setContentsMargins(0,0,0,0); self.nav_grid.setSpacing(5); nav_layout.addWidget(self.nav_grid_widget); h_layout.addWidget(self.nav_card, 3, Qt.AlignTop)
        main_layout.addLayout(h_layout); self.stack.addWidget(self.page_exam)

    def clear_selection(self):
        self.bg.setExclusive(False)
        for b in self.bg.buttons(): b.setChecked(False)
        self.bg.setExclusive(True)
        if self.current_q in self.answers: del self.answers[self.current_q]
        self.update_nav_colors()

    def populate_nav_buttons(self):
        for i in reversed(range(self.nav_grid.count())): self.nav_grid.itemAt(i).widget().setParent(None)
        self.nav_buttons = []; total = len(self.exam_data); cols = 5
        for i in range(total):
            btn = QPushButton(str(i+1)); btn.setObjectName("NavBtn"); btn.setFixedSize(32, 32); btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(lambda checked, idx=i: self.jump_to_q(idx))
            row = i // cols; col = i % cols; self.nav_grid.addWidget(btn, row, col); self.nav_buttons.append(btn)

    def update_nav_colors(self):
        for i, btn in enumerate(self.nav_buttons):
            style = "border-radius: 5px; font-weight: bold; border: 1px solid #CBD5E1;"
            is_skipped = (i <= self.max_visited_q) and (i not in self.answers) and (i != self.current_q)
            if i in self.flagged_questions: style += "background-color: #F59E0B; color: black;" 
            elif i in self.answers: style += "background-color: #10B981; color: white;"
            elif is_skipped: style += "background-color: #EF4444; color: white;" 
            else: style += "background-color: #F1F5F9; color: #64748B;" 
            if i == self.current_q: style += "border: 2px solid #2563EB;" 
            btn.setStyleSheet(style)

    def actual_start_exam(self):
        self.prog.setRange(0, len(self.exam_data)); self.current_q = 0; self.answers = {}; self.flagged_questions = set(); self.warnings = 0; self.exam_active = True; self.max_visited_q = -1 
        self.populate_nav_buttons(); speaker.speak("Exam Protocol Initiated. Good luck."); self.load_q(); self.timer.start(1000); self.update_background_theme(4); self.stack.setCurrentWidget(self.page_exam)

    def load_q(self):
        if self.current_q >= len(self.exam_data): return
        self.max_visited_q = max(self.max_visited_q, self.current_q); d = self.exam_data[self.current_q]; self.lbl_q.setText(f"Q{self.current_q+1}: {d['q']}"); self.prog.setValue(self.current_q+1)
        self.bg.setExclusive(False)
        for r in self.rbs: r.setChecked(False)
        self.bg.setExclusive(True)
        for i, txt in enumerate(d['opts']):
            if txt == "-" or str(txt).strip() == "": self.rbs[i].hide()
            else:
                self.rbs[i].set_text_safely(str(txt)); is_checked = (self.answers.get(self.current_q) == str(txt))
                self.rbs[i].setChecked(is_checked); self.rbs[i].update_style(is_checked); self.rbs[i].show()
        self.update_nav_colors(); self.lbl_q.updateGeometry()
        for r in self.rbs: r.updateGeometry()
        self.exam_card.updateGeometry(); QApplication.processEvents()
        if not self.isMaximized(): self.resize(1300, 850)

    def save_ans(self, b): self.answers[self.current_q] = b.property("original_text"); self.update_nav_colors()
    def flag_current_q(self):
        if self.current_q in self.flagged_questions: self.flagged_questions.remove(self.current_q)
        else: self.flagged_questions.add(self.current_q)
        self.update_nav_colors()
    def jump_to_q(self, index): self.current_q = index; self.load_q()
    def next_q(self): 
        if self.current_q < len(self.exam_data) - 1: self.current_q += 1; self.load_q()
    def prev_q(self): 
        if self.current_q > 0: self.current_q -= 1; self.load_q()
    def update_timer(self):
        self.time_left -= 1; m, s = divmod(self.time_left, 60); self.lbl_time.setText(f"{m:02d}:{s:02d}")
        if self.time_left <= 0: self.submit()

    def confirm_submit(self):
        self.is_confirming = True; reply = QMessageBox.question(self, 'Confirm Submission', "Are you sure you want to finish the exam?\nYou cannot go back after this.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No); self.is_confirming = False
        if reply == QMessageBox.Yes: self.submit()

    def init_result(self):
        self.page_res = QWidget(); self.page_res.setObjectName("LightPage"); main_layout = QVBoxLayout(self.page_res); main_layout.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("ResultCard"); card.setFixedWidth(600); card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum); card.setStyleSheet("QFrame#ResultCard { background-color: #FFFFFF; border: 2px solid #1E3A8A; border-radius: 20px; }"); card.setGraphicsEffect(self.get_shadow())
        cl = QVBoxLayout(card); cl.setContentsMargins(50, 40, 50, 40); cl.setSpacing(20); t = QLabel("OFFICIAL MID-TERM REPORT"); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size: 24px; font-weight: 900; color: #1E3A8A; letter-spacing: 1px;"); cl.addWidget(t)
        data_frame = QFrame(); data_frame.setStyleSheet("background-color: #0F172A; border-radius: 10px;"); form = QVBoxLayout(data_frame); form.setContentsMargins(35, 35, 35, 35); form.setSpacing(20)
        
        def add_row(label_text):
            item_widget = QWidget(); item_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); il = QVBoxLayout(item_widget); il.setContentsMargins(0, 0, 0, 0); il.setSpacing(4)
            lbl = QLabel(label_text); lbl.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;"); val = QLabel(); val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum); val.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;"); val.setWordWrap(True)
            il.addWidget(lbl); il.addWidget(val); form.addWidget(item_widget); return val
            
        self.res_name = add_row("Candidate Name"); self.res_roll = add_row("Roll Number"); self.res_course = add_row("Module Selected"); self.res_score = add_row("MID-TERM Score"); cl.addWidget(data_frame)
        self.res_status = QLabel("QUALIFIED"); self.res_status.setFont(QFont("Segoe UI", 36, QFont.Bold)); self.res_status.setAlignment(Qt.AlignCenter); cl.addWidget(self.res_status); main_layout.addWidget(card); self.stack.addWidget(self.page_res)

    def submit(self):
        self.exam_active = False; self.timer.stop(); score = sum([1 for i,d in enumerate(self.exam_data) if self.answers.get(i)==d['ans']]); perc = int((score/len(self.exam_data))*100) if self.exam_data else 0
        status = "QUALIFIED" if perc >= self.current_pass_pct else "FAILED"
        detailed_log = []
        for i, q in enumerate(self.exam_data): detailed_log.append({ "q": q['q'], "user": self.answers.get(i, "Not Answered"), "correct": q['ans'] }) 
        
        payload = { "name": self.inp_name.text(), "roll": self.inp_roll.text(), "course": self.selected_course, "score_pct": perc, "status": status, "details": json.dumps(detailed_log) }
        self.submit_thread = SubmitTask(self.server_ip, payload); self.submit_thread.success.connect(self.on_submit_success); self.submit_thread.failed.connect(self.on_submit_failed); self.submit_thread.start()
        
        self.res_name.setText(self.inp_name.text()); self.res_roll.setText(self.inp_roll.text()); self.res_course.setText(self.selected_course); self.res_score.setText(f"{perc}% (Req: {self.current_pass_pct}%)"); self.res_status.setText(status)
        if status == "FAILED": self.res_status.setStyleSheet("color: #EF4444; margin-top: 5px; margin-bottom: 5px;")
        else: self.res_status.setStyleSheet("color: #10B981; margin-top: 5px; margin-bottom: 5px;")
        self.update_background_theme(5); self.stack.setCurrentWidget(self.page_res)

    def on_submit_success(self): speaker.speak("Data successfully submitted to server.")
    def on_submit_failed(self, err_msg): speaker.speak("Network error. Could not send result to teacher."); QMessageBox.warning(self, "Network Error", f"Could not send result to the server.\nError: {err_msg}\nPlease raise your hand.")
    def changeEvent(self, e):
        if hasattr(self, 'exam_active') and self.exam_active and not self.is_confirming and e.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.warnings += 1
            if self.warnings > MAX_WARNINGS: self.exam_active = False; self.timer.stop(); self.submit(); self.show_error("Terminated", "Security Protocol Violated.\nExam Terminated.")
            else: self.activateWindow(); self.show_error("Warning", "Stay in the window.\nThis is a warning.")
    def closeEvent(self, event):
        if self.poller_thread and self.poller_thread.isRunning(): self.poller_thread.stop(); self.poller_thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication.instance()
    if not app: app = QApplication(sys.argv)
    w = StudentTerminalSoftware(); w.showMaximized(); sys.exit(app.exec())