import sys, os, random, sqlite3, csv, threading, json, webbrowser, re, openpyxl, socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QStackedWidget, QFrame, QButtonGroup, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QSizePolicy, QMessageBox, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QFormLayout, QInputDialog, QStyleFactory, QScrollArea, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QSize, QRectF, QRect, Signal, QPointF
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush, QConicalGradient, QMovie, QLinearGradient, QIcon, QPolygonF

if getattr(sys, 'frozen', False): curr_dir = os.path.dirname(sys.executable)
else:
    try: curr_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError: curr_dir = os.getcwd()
os.chdir(curr_dir)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return f"{IP}:8000"

SERVER_STATE = {"is_active": False, "exam_started": False, "course": "", "duration": 60, "pass_pct": 50, "questions": []}
READY_STUDENTS = set(); SUBMITTED_RESULTS = []

class ExamNetworkHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass 
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
            self.wfile.write(json.dumps(SERVER_STATE).encode('utf-8'))
        else: self.send_response(404); self.end_headers()
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0)); post_data = self.rfile.read(content_length)
        if self.path == '/ready':
            try: data = json.loads(post_data.decode('utf-8')); READY_STUDENTS.add(data.get("roll", "Unknown")); self.send_response(200); self.end_headers()
            except: self.send_response(400); self.end_headers()
        elif self.path == '/submit':
            try: data = json.loads(post_data.decode('utf-8')); SUBMITTED_RESULTS.append(data); self.send_response(200); self.end_headers()
            except: self.send_response(400); self.end_headers()

class ServerThread(threading.Thread):
    def __init__(self, port=8000): super().__init__(); self.port = port; self.server = None; self.daemon = True
    def run(self): self.server = HTTPServer(('0.0.0.0', self.port), ExamNetworkHandler); self.server.serve_forever()

try: import pyttsx3; VOICE_AVAILABLE = True
except ImportError: VOICE_AVAILABLE = False
class VoiceAssistant:
    def __init__(self):
        self.engine = None
        if VOICE_AVAILABLE:
            try: self.engine = pyttsx3.init(); self.engine.setProperty('rate', 160); self.engine.setProperty('volume', 0.9)
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

COURSE_LIST = ["CNC Milling Course", "Harness Manufacturing Course", "Rubber Technology Course", "Fundamentals of NDT", "Rotor and Turbine Balancing", "Aviation Standard Pipe Bending", "Investment Casting", "Aircraft Painting Course", "CAD/CAM Course", "Aviation Standard Riveting", "Heat & Surface Treatment Course", "CNC Turning Course", "Avcs Life Cycle Support, PCB Repair & RF Cable Mfg", "Intro to Avionics Systems & IPC Standards", "Composite Parts Manufacturing Course", "Conventional Machining Course"]

# =====================================================================
# BULLETPROOF DATA EXTRACTION LOGIC
# =====================================================================

def clean_text(text):
    if text is None: return ""
    text = str(text).strip()
    if text == "" or text.lower() == 'nan': return ""
    if text.endswith('.0') and text[:-2].isdigit(): return text[:-2]
    return " ".join(text.split())

def clean_question_number(q_text):
    """Safely strips leading numbers like '34.', 'Q3:', '1)' without hurting actual content"""
    q_text = q_text.strip()
    old_q = ""
    while old_q != q_text:
        old_q = q_text
        q_text = re.sub(r'^(?:[Qq]\d*[\.\:\-\)]+|\d+[\.\:\-\)]+)\s*', '', q_text).strip()
    return q_text

def get_actual_file(course_name):
    mapping = { "Avcs Life Cycle Support, PCB Repair & RF Cable Mfg": ["1. ALC"], "Conventional Machining Course": ["2. CMC"], "Aircraft Painting Course": ["3. Painting"], "CNC Turning Course": ["4. CNC Turning"], "Composite Parts Manufacturing Course": ["5. Composit"], "Investment Casting": ["6. Investment"], "Fundamentals of NDT": ["7. NDT"], "Aviation Standard Pipe Bending": ["8. Pipe"], "Rotor and Turbine Balancing": ["9. RTB"], "Rubber Technology Course": ["10. Rubber"], "Heat & Surface Treatment Course": ["11. HST"], "Aviation Standard Riveting": ["12. Aviation"], "CNC Milling Course": ["13. CNC Milling"], "Harness Manufacturing Course": ["14. Harness"], "Intro to Avionics Systems & IPC Standards": ["15. Intro"], "CAD/CAM Course": ["16. CAD"] }
    keywords = mapping.get(course_name, [course_name.split()[0]])
    for f in os.listdir(curr_dir):
        if f.startswith('~$'): continue
        if not (f.endswith('.xlsx') or f.endswith('.csv')): continue
        f_lower = f.lower()
        for kw in keywords:
            if kw.lower() in f_lower: return os.path.join(curr_dir, f)
    return None

def extract_course_data(course_name):
    actual_file = get_actual_file(course_name)
    if not actual_file: return None, []

    raw_data = []
    try:
        if actual_file.endswith('.xlsx'):
            wb = openpyxl.load_workbook(actual_file, data_only=True)
            ws = wb.worksheets[0]
            for row in ws.iter_rows(values_only=True): raw_data.append([str(v) if v is not None else "" for v in row])
        else:
            with open(actual_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader: raw_data.append([str(v) if v is not None else "" for v in row])
    except Exception:
        return None, []

    # LAYER 1: DYNAMIC COLUMN DETECTION (Fixes shifted columns)
    header_row_idx = -1
    q_col = a_col = b_col = c_col = d_col = ans_col = chap_col = -1

    for i in range(min(15, len(raw_data))):
        row_lower = [str(cell).lower().strip() for cell in raw_data[i]]
        has_q = any("question" in c or "statement" in c or "description" in c for c in row_lower)
        has_ans = any("answer" in c or "correct" in c for c in row_lower)
        
        if has_q or has_ans:
            header_row_idx = i
            for j, cell in enumerate(row_lower):
                if "chapter" in cell or "module" in cell: chap_col = j
                elif "question" in cell or "statement" in cell or "description" in cell: q_col = j
                elif cell in ["a", "opt a", "option a", "opt1", "option 1"]: a_col = j
                elif cell in ["b", "opt b", "option b", "opt2", "option 2"]: b_col = j
                elif cell in ["c", "opt c", "option c", "opt3", "option 3"]: c_col = j
                elif cell in ["d", "opt d", "option d", "opt4", "option 4"]: d_col = j
                elif "answer" in cell or "correct" in cell: ans_col = j
            break

    # Fallback to standard AMSC if headers are completely missing
    if q_col == -1 or ans_col == -1 or a_col == -1:
        chap_col, q_col, a_col, b_col, c_col, d_col, ans_col = 1, 2, 3, 4, 5, 6, 7
        header_row_idx = 0 

    all_questions = []; available_chapters = set(); seen_qs = set()

    for row_idx in range(header_row_idx + 1, len(raw_data)):
        row = raw_data[row_idx]
        raw_vals = [clean_text(v) for v in row]
        
        # Pad row to prevent index out of bounds
        max_needed_col = max(q_col, a_col, b_col, c_col, d_col, ans_col, chap_col)
        while len(raw_vals) <= max_needed_col: raw_vals.append("")

        q_text = raw_vals[q_col]
        ans_text = raw_vals[ans_col]
        chapter_val = raw_vals[chap_col] if chap_col != -1 else "General"

        if not chapter_val or chapter_val == "": chapter_val = "General"

        # LAYER 2: CLEAN QUESTION & STRIP NUMBERS
        if not q_text or len(q_text) < 4: continue
        q_text = clean_question_number(q_text)
        if not re.search(r'[a-zA-Z0-9]', q_text): continue 
        
        q_clean = q_text.lower().replace(".", "").replace(" ", "").strip()
        if q_clean in ["sno", "srno", "serialno", "chapter", "question", "description", "statement", "qno"]: continue
        if q_clean.isdigit(): continue
        
        opts = [raw_vals[a_col], raw_vals[b_col], raw_vals[c_col], raw_vals[d_col]]
        opts = [o if o != "" else "-" for o in opts]
        
        # LAYER 3: CROSS-CONTAMINATION FIREWALL
        for idx, opt in enumerate(opts):
            if opt != "-" and len(opt) > 10 and (q_text.lower() in opt.lower() or opt.lower() in q_text.lower()):
                opts[idx] = "-" 

        ans_text = ans_text.strip()
        if ans_text == "": continue 

        # LAYER 4: SAFE ANSWER RESOLUTION
        ans_clean = ans_text.lower().replace(".", "").replace(")", "").strip()
        correct = ans_text
        
        if ans_clean in ['a', 'opt a', 'option a', '1'] and opts[0] != "-": correct = opts[0]
        elif ans_clean in ['b', 'opt b', 'option b', '2'] and opts[1] != "-": correct = opts[1]
        elif ans_clean in ['c', 'opt c', 'option c', '3'] and opts[2] != "-": correct = opts[2]
        elif ans_clean in ['d', 'opt d', 'option d', '4'] and opts[3] != "-": correct = opts[3]
        elif ans_clean in ['t', 'true']: correct = "True"
        elif ans_clean in ['f', 'false']: correct = "False"

        if correct == "-" or correct == "": continue

        # =====================================================================
        # LAYER 4.5: THE ABSOLUTE TRUE/FALSE OVERRIDE (Fixes the stray 'B' issue)
        # =====================================================================
        correct_clean = correct.lower().strip()
        opts_clean = [str(o).lower().strip() for o in opts]
        
        is_tf = False
        # Condition 1: Answer is explicitly True or False
        if correct_clean in ['true', 'false', 't', 'f']:
            is_tf = True
        # Condition 2: The options contain BOTH True and False (regardless of garbage)
        elif (any(x in ['true', 't'] for x in opts_clean) and any(x in ['false', 'f'] for x in opts_clean)):
            is_tf = True
            
        if is_tf:
            # Force standard capitalization
            if correct_clean in ['true', 't']: correct = "True"
            elif correct_clean in ['false', 'f']: correct = "False"
            else:
                # If correct answer is "A" or "B" and points to a True/False option
                if 'true' in correct_clean: correct = "True"
                elif 'false' in correct_clean: correct = "False"
                elif correct_clean == 'a' and len(opts_clean) > 0: correct = "True" if opts_clean[0] in ['true', 't'] else "False"
                elif correct_clean == 'b' and len(opts_clean) > 1: correct = "True" if opts_clean[1] in ['true', 't'] else "False"
                elif correct_clean == 'c' and len(opts_clean) > 2: correct = "True" if opts_clean[2] in ['true', 't'] else "False"
                elif correct_clean == 'd' and len(opts_clean) > 3: correct = "True" if opts_clean[3] in ['true', 't'] else "False"
                else: correct = "True" # Safe fallback
            
            # WIPE OUT GARBAGE: Force the options array to ONLY contain True and False
            opts = ["True", "False", "-", "-"]
        # =====================================================================

        # LAYER 5: FORCE ANSWER INTO OPTIONS IF MISSING
        if not is_tf and correct not in opts:
            match_found = False
            for idx, opt in enumerate(opts):
                if opt != "-" and (correct.lower().strip() in str(opt).lower().strip() or str(opt).lower().strip() in correct.lower().strip()):
                    correct = opt; match_found = True; break
            if not match_found:
                placed = False
                for idx in range(4):
                    if opts[idx] == "-":
                        opts[idx] = correct; placed = True; break
                if not placed: opts[3] = correct 

        sig = "".join(q_text.split()).lower()
        if sig not in seen_qs:
            seen_qs.add(sig)
            available_chapters.add(chapter_val)
            all_questions.append({"q": q_text, "opts": opts, "ans": correct, "chapter": chapter_val})

    try: sorted_chapters = sorted(list(available_chapters), key=lambda x: float(x) if str(x).replace('.','').isdigit() else x)
    except: sorted_chapters = sorted(list(available_chapters))
        
    return all_questions, sorted_chapters

# =====================================================================
# END DATA EXTRACTION
# =====================================================================

def load_local_questions(course_name, allowed_chapters=None, total_to_ask=50):
    all_qs, _ = extract_course_data(course_name)
    if not all_qs: return None
    filtered_qs = [q for q in all_qs if str(q['chapter']) in allowed_chapters] if allowed_chapters else all_qs
    if not filtered_qs: return None
    for q in filtered_qs:
        opts_with_ans = [opt for opt in q['opts'] if opt != "-"]
        random.shuffle(opts_with_ans); new_opts = ["-", "-", "-", "-"]
        for i in range(len(opts_with_ans)): new_opts[i] = opts_with_ans[i]
        q['opts'] = new_opts
    random.shuffle(filtered_qs); return filtered_qs[:min(total_to_ask, len(filtered_qs))]

class FuturisticButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent); self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background-color: #2563EB; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 10px; border: 1px solid #60A5FA; } QPushButton:hover { background-color: #3B82F6; border: 2px solid #00FFFF; } QPushButton:disabled { background-color: #1E293B; border: 1px solid #334155; color: #64748B; }")
        self.anim = QPropertyAnimation(self, b"geometry"); self.anim.setDuration(100); self.anim.setEasingCurve(QEasingCurve.OutQuad); self.original_rect = QRect()
    def enterEvent(self, event):
        if self.isEnabled():
            self.original_rect = self.geometry(); self.anim.setStartValue(self.original_rect); self.anim.setEndValue(self.original_rect.adjusted(-3, -3, 3, 3)); self.anim.start()
        super().enterEvent(event)
    def leaveEvent(self, event):
        if self.isEnabled(): self.anim.setStartValue(self.geometry()); self.anim.setEndValue(self.original_rect); self.anim.start()
        super().leaveEvent(event)

class ScanlineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.scan_y = 0
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_scan); self.timer.start(50) 
    def update_scan(self):
        self.scan_y += 2; self.scan_y = 0 if self.scan_y > self.height() else self.scan_y; self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setPen(QColor(0, 0, 0, 30))
        for y in range(0, self.height(), 4): painter.drawLine(0, y, self.width(), y)
        grad = QLinearGradient(0, self.scan_y, 0, self.scan_y + 50); grad.setColorAt(0, QColor(0, 255, 255, 0)); grad.setColorAt(0.5, QColor(0, 255, 255, 20)); grad.setColorAt(1, QColor(0, 255, 255, 0))
        painter.fillRect(self.rect(), grad)

class StarParticle:
    def __init__(self, w, h):
        self.x, self.y = random.randint(0, w), random.randint(0, h)
        self.speed, self.size, self.alpha = random.uniform(0.2, 0.8), random.randint(1, 3), random.randint(100, 255)
        self.original_x, self.original_y = self.x, self.y
class BackgroundStars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.stars = []
        self.timer = QTimer(); self.timer.timeout.connect(self.update_stars); self.timer.start(50); self.offset_x = 0; self.offset_y = 0
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
        for s in self.stars:
            painter.setBrush(QBrush(QColor(255, 255, 255, s.alpha))); painter.setPen(Qt.NoPen); painter.drawEllipse(int(s.x), int(s.y), s.size, s.size)

class CGIDonutChart(QWidget):
    def __init__(self, total=0, passed=0):
        super().__init__(); self.total, self.passed, self.current_angle, self.target_angle = total, passed, 0, 0
        self.setFixedSize(160, 160); self.anim_timer = QTimer(); self.anim_timer.timeout.connect(self.animate)
    def update_values(self, total, passed):
        self.total, self.passed = total, passed; self.target_angle = int((passed / total) * 360 * 16) if total > 0 else 0; self.current_angle = 0; self.anim_timer.start(10)
    def animate(self):
        if self.current_angle < self.target_angle: self.current_angle += 80; self.current_angle = min(self.current_angle, self.target_angle); self.update()
        else: self.anim_timer.stop()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); rect = QRectF(10, 10, 140, 140)
        pen = QPen(QColor(0, 0, 0, 20), 15); pen.setCapStyle(Qt.RoundCap); painter.setPen(pen); painter.drawArc(rect, 0, 360 * 16)
        if self.total > 0:
            grad = QConicalGradient(70, 70, 90); grad.setColorAt(0, QColor("#10B981")); grad.setColorAt(1, QColor("#3B82F6"))
            pen = QPen(QBrush(grad), 15); pen.setCapStyle(Qt.RoundCap); painter.setPen(pen); painter.drawArc(rect, 90 * 16, -self.current_angle)
        painter.setPen(QColor("#0F172A")); painter.setFont(QFont("Segoe UI", 20, QFont.Bold)); painter.drawText(rect, Qt.AlignCenter, f"{self.passed}/{self.total}")

class NASTPSoftware(QMainWindow):
    def __init__(self):
        super().__init__()
        if "Fusion" in QStyleFactory.keys(): QApplication.setStyle(QStyleFactory.create("Fusion"))
        self.init_db(); self.setWindowTitle("AMSC MID-TERM Teacher Server"); self.setMinimumSize(1300, 850); self.resize(1300, 850); self.setMouseTracking(True)
        icon_path = find_file(APP_ICON_NAME)
        if icon_path: self.setWindowIcon(QIcon(icon_path))
        self.init_flag_animation()
        self.stars = BackgroundStars(self); self.stars.resize(1300, 850); self.stars.lower()
        self.scanlines = ScanlineOverlay(self); self.scanlines.resize(1300, 850); self.scanlines.raise_()
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.init_gatekeeper(); self.init_cinematic(); self.init_dash(); self.init_admin_menu(); self.init_history(); self.init_change_pwd(); self.init_exam_config() 
        self.stack.currentChanged.connect(self.update_background_theme); self.stack.setCurrentWidget(self.gatekeeper_page); self.update_background_theme(0)
        
        self.server_thread = ServerThread(port=8000); self.server_thread.start()
        self.network_timer = QTimer(); self.network_timer.timeout.connect(self.process_network_events); self.network_timer.start(1000)

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
        QWidget#DarkPage QComboBox:hover { border: 2px solid #38BDF8; }
        QWidget#DarkPage QComboBox QAbstractItemView { background-color: #0F172A; color: #FFFFFF; border: 2px solid #38BDF8; selection-background-color: #2563EB; selection-color: white; outline: none; padding: 5px; border-radius: 5px; }
        QWidget#DarkPage QLineEdit, QSpinBox { background-color: #000000; color: #FFFFFF; border: 1px solid #475569; border-radius: 8px; padding: 0px 15px; font-size: 15px; font-weight: bold; height: 40px; }
        QWidget#LightPage { background-color: #FFFFFF; } QWidget#LightPage QLabel { color: #0F172A; }
        QPushButton#SidebarBtn { background-color: rgba(255, 255, 255, 0.05); color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; text-align: center; padding: 12px; font-size: 15px; font-weight: bold; letter-spacing: 1px; }
        QPushButton#SidebarBtn:hover { background-color: rgba(56, 189, 248, 0.15); border: 1px solid #38BDF8; color: #00FFFF; }
        QLabel#Header { font-size: 28px; font-weight: 800; letter-spacing: 1px; }
        QLabel#LabelTitle { font-size: 12px; font-weight: bold; color: #38BDF8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
        QTableWidget { background-color: #FFFFFF; color: #000000; gridline-color: #E2E8F0; border: 1px solid #E2E8F0; border-radius: 10px; }
        QTableWidget::item { color: #000000; }
        QHeaderView::section { background-color: #0F172A; color: #FFFFFF; padding: 10px; border: 1px solid #1E293B; font-weight: bold; }
        QMessageBox, QInputDialog { background-color: #FFFFFF; }
        QMessageBox QLabel, QInputDialog QLabel { color: #0F172A; font-weight: bold; font-size: 14px; }
        QMessageBox QPushButton, QInputDialog QPushButton { background-color: #1E3A8A; color: white; border-radius: 5px; padding: 6px 15px; }
        QInputDialog QLineEdit { background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; padding: 5px; font-weight: bold; }
        QCheckBox { color: white; font-weight: bold; font-size: 14px; padding: 5px; }
        QCheckBox::indicator { width: 20px; height: 20px; border-radius: 3px; border: 2px solid #475569; background: #0F172A; }
        QCheckBox::indicator:checked { background: #3B82F6; border: 2px solid #60A5FA; }
        QScrollArea { background-color: transparent; border: 1px solid #475569; border-radius: 8px; }
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
        
        if index in [0, 2, 3, 6]: 
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
        else:
            self.stars.hide(); self.scanlines.hide()
            if self.flag_label: self.flag_label.hide()
            final_style += "\nQMainWindow { background-color: #FFFFFF; }"
            
        self.setStyleSheet(final_style); self.repaint()

    def init_flag_animation(self):
        flag_path = find_file(FLAG_GIF_NAME)
        if flag_path:
            self.flag_label = QLabel(self); self.flag_movie = QMovie(flag_path); self.flag_movie.setScaledSize(QSize(200, 120))
            self.flag_label.setMovie(self.flag_movie); self.flag_label.setFixedSize(200, 120)
            self.flag_opacity = QGraphicsOpacityEffect(); self.flag_opacity.setOpacity(0.9); self.flag_label.setGraphicsEffect(self.flag_opacity)
            self.flag_movie.start(); self.flag_label.show(); self.flag_label.lower()
        else: self.flag_label = None

    def init_db(self):
        db_path = os.path.join(curr_dir, "database", "nastp_enterprise_midterm.db"); os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False); self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, name TEXT, roll TEXT, course TEXT, score TEXT, status TEXT, date TEXT, details TEXT)")
        self.cur.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, pass1 TEXT, pass2 TEXT, exam_duration INTEGER, course_configs TEXT)")
        self.cur.execute("SELECT COUNT(*) FROM settings")
        if self.cur.fetchone()[0] == 0: self.cur.execute("INSERT INTO settings (pass1, pass2, exam_duration, course_configs) VALUES (?, ?, ?, ?)", ("amsc324", "admin256", 60, "{}"))
        self.conn.commit()

    def get_shadow(self): shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(40); shadow.setOffset(0, 10); shadow.setColor(QColor(0, 0, 0, 80)); return shadow
    def show_error(self, title, message): speaker.speak("Attention."); msg = QMessageBox(self); msg.setWindowTitle(title); msg.setText(message); msg.setIcon(QMessageBox.Warning); msg.exec()

    def init_gatekeeper(self):
        self.gatekeeper_page = QWidget(); self.gatekeeper_page.setObjectName("DarkPage"); self.gatekeeper_page.setMouseTracking(True)
        layout = QVBoxLayout(self.gatekeeper_page); layout.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(450, 500); card.setGraphicsEffect(self.get_shadow())
        l = QVBoxLayout(card); l.setSpacing(25); l.setContentsMargins(50, 50, 50, 50)
        logo = QLabel("AMSC"); logo.setObjectName("Logo"); logo.setAlignment(Qt.AlignCenter); logo.setStyleSheet("color: #00FFFF; font-size: 48px; font-weight: 900;")
        sub = QLabel("TEACHER SERVER TERMINAL"); sub.setObjectName("LabelTitle"); sub.setAlignment(Qt.AlignCenter)
        self.txt_pwd = QLineEdit(); self.txt_pwd.setPlaceholderText("AUTHENTICATION KEY"); self.txt_pwd.setEchoMode(QLineEdit.Password); self.txt_pwd.setAlignment(Qt.AlignCenter); self.txt_pwd.returnPressed.connect(self.check_password)
        btn = FuturisticButton("INITIALIZE SERVER"); btn.setFixedHeight(50); btn.clicked.connect(self.check_password)
        l.addStretch(); l.addWidget(logo); l.addWidget(sub); l.addWidget(self.txt_pwd); l.addWidget(btn); l.addStretch()
        layout.addWidget(card); self.stack.addWidget(self.gatekeeper_page)

    def init_cinematic(self):
        self.cinematic_page = QWidget(); layout = QVBoxLayout(self.cinematic_page); layout.setAlignment(Qt.AlignCenter); layout.setContentsMargins(0,0,0,0)
        self.lbl_cinematic_img = QLabel(); self.lbl_cinematic_img.setAlignment(Qt.AlignCenter)
        cine_path = find_file(CINEMATIC_IMAGE_NAME)
        if cine_path: pixmap = QPixmap(cine_path); scaled = pixmap.scaled(1300, 850, Qt.KeepAspectRatio, Qt.SmoothTransformation); self.lbl_cinematic_img.setPixmap(scaled)
        layout.addWidget(self.lbl_cinematic_img)
        self.cinematic_opacity = QGraphicsOpacityEffect(self.cinematic_page); self.cinematic_page.setGraphicsEffect(self.cinematic_opacity)
        self.stack.addWidget(self.cinematic_page)

    def check_password(self):
        self.cur.execute("SELECT pass1 FROM settings"); stored_p1 = self.cur.fetchone()[0]
        if self.txt_pwd.text() == stored_p1: speaker.speak("Server Authorized."); self.play_cinematic()
        else: self.txt_pwd.clear(); self.txt_pwd.setPlaceholderText("ACCESS DENIED"); self.show_error("Access Denied", "Invalid Key.")

    def play_cinematic(self):
        self.stack.setCurrentWidget(self.cinematic_page); self.cinematic_opacity.setOpacity(0)
        self.anim = QPropertyAnimation(self.cinematic_opacity, b"opacity"); self.anim.setDuration(1500); self.anim.setStartValue(0); self.anim.setEndValue(1); self.anim.setEasingCurve(QEasingCurve.InOutQuad); self.anim.start()
        QTimer.singleShot(3000, lambda: self.stack.setCurrentWidget(self.page_dash))

    def create_sidebar(self):
        sb = QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(260)
        l = QVBoxLayout(sb); l.setSpacing(15); l.setContentsMargins(20, 40, 20, 20)
        logo = QLabel("AMSC"); logo.setObjectName("Logo"); logo.setStyleSheet("font-size: 32px; color: #00FFFF; font-weight: 800;"); logo.setAlignment(Qt.AlignCenter)
        b1 = QPushButton("Dashboard"); b1.setObjectName("SidebarBtn"); b1.setCursor(Qt.PointingHandCursor); b1.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_dash))
        b2 = QPushButton("Admin Panel"); b2.setObjectName("SidebarBtn"); b2.setCursor(Qt.PointingHandCursor); b2.clicked.connect(self.check_admin_access)
        l.addWidget(logo); l.addSpacing(40); l.addWidget(b1); l.addWidget(b2); l.addStretch()
        return sb

    def check_admin_access(self):
        self.cur.execute("SELECT pass1, pass2 FROM settings"); p1, p2 = self.cur.fetchone()
        pwd1, ok1 = QInputDialog.getText(self, "Security Level 1", "Enter Primary Admin Password:", QLineEdit.Password)
        if ok1 and pwd1 == p1:
            pwd2, ok2 = QInputDialog.getText(self, "Security Level 2", "Enter Secondary Admin Password:", QLineEdit.Password)
            if ok2 and pwd2 == p2: speaker.speak("Admin Access Granted."); self.stack.setCurrentWidget(self.page_admin_menu)
            elif ok2: self.show_error("Access Denied", "Secondary Password Incorrect.")
        elif ok1: self.show_error("Access Denied", "Primary Password Incorrect.")

    def init_dash(self):
        self.page_dash = QWidget(); self.page_dash.setObjectName("DarkPage"); self.page_dash.setMouseTracking(True)
        layout = QHBoxLayout(self.page_dash); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        content = QWidget(); c_layout = QVBoxLayout(content); c_layout.setContentsMargins(40, 40, 40, 40); c_layout.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(900, 600); card.setGraphicsEffect(self.get_shadow())
        vl = QVBoxLayout(card); vl.setContentsMargins(50, 50, 50, 50); vl.setSpacing(25)
        
        self.lbl_ip = QLabel(f"STUDENTS SHALL ENTER THIS IP: {get_local_ip()}")
        self.lbl_ip.setStyleSheet("color: #10B981; font-size: 18px; font-weight: bold; border: 2px dashed #10B981; padding: 15px; border-radius: 8px; background-color: rgba(16, 185, 129, 0.1);")
        self.lbl_ip.setAlignment(Qt.AlignCenter)
        
        self.lbl_status = QLabel("SERVER IDLE - SELECT MODULE TO BROADCAST")
        self.lbl_status.setStyleSheet("color: white; font-size: 24px; font-weight: 900; letter-spacing: 2px;"); self.lbl_status.setAlignment(Qt.AlignCenter)
        
        self.lbl_lobby = QLabel("READY CANDIDATES: 0")
        self.lbl_lobby.setStyleSheet("color: #FBBF24; font-size: 18px; font-weight: bold; padding-top: 10px;"); self.lbl_lobby.setAlignment(Qt.AlignCenter)
        
        l_crs = QLabel("MODULE SELECTION:"); l_crs.setObjectName("LabelTitle")
        self.inp_crs = QComboBox(); self.inp_crs.addItems(COURSE_LIST)
        
        btn_box = QHBoxLayout(); btn_box.setSpacing(20)
        self.btn_broadcast = FuturisticButton("BROADCAST / MAKE CHANGES"); self.btn_broadcast.setFixedHeight(70); self.btn_broadcast.clicked.connect(self.trigger_broadcast)
        self.btn_start = FuturisticButton("START EXAM"); self.btn_start.setFixedHeight(70); self.btn_start.setDisabled(True); self.btn_start.clicked.connect(self.trigger_start_exam)
        btn_box.addWidget(self.btn_broadcast); btn_box.addWidget(self.btn_start)
        
        vl.addWidget(self.lbl_ip); vl.addSpacing(10); vl.addWidget(self.lbl_status); vl.addWidget(self.lbl_lobby); vl.addSpacing(40); vl.addWidget(l_crs); vl.addWidget(self.inp_crs); vl.addStretch(); vl.addLayout(btn_box)
        c_layout.addWidget(card); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_dash)

    def trigger_broadcast(self):
        crs = self.inp_crs.currentText()
        self.cur.execute("SELECT course_configs FROM settings WHERE id=1"); row = self.cur.fetchone()
        crs_config = (json.loads(row[0]) if row and row[0] else {}).get(crs, {})
        loaded_qs = load_local_questions(crs, crs_config.get("chapters", None), crs_config.get("total_q", 50))
        if not loaded_qs: self.show_error("Configuration Error", f"No questions found for {crs}. Check your admin panel configuration."); return
            
        SERVER_STATE.update({"course": crs, "duration": crs_config.get("duration", 60), "pass_pct": crs_config.get("pass_pct", 50), "questions": loaded_qs, "exam_started": False, "is_active": True})
        READY_STUDENTS.clear() 
        self.lbl_status.setText("BROADCASTING TO LOBBY"); self.lbl_status.setStyleSheet("color: #38BDF8; font-size: 24px; font-weight: 900; letter-spacing: 2px;")
        speaker.speak("Module synchronized. Students may now enter the lobby.")

    def trigger_start_exam(self):
        SERVER_STATE["exam_started"] = True
        self.lbl_status.setText("EXAM IN PROGRESS - DO NOT CLOSE SERVER"); self.lbl_status.setStyleSheet("color: #EF4444; font-size: 24px; font-weight: 900; letter-spacing: 2px;")
        self.btn_broadcast.setDisabled(True); self.btn_start.setDisabled(True); self.inp_crs.setDisabled(True); speaker.speak("Exam commenced.")

    def process_network_events(self):
        lobby_count = len(READY_STUDENTS)
        if SERVER_STATE["is_active"] and not SERVER_STATE["exam_started"]:
            self.lbl_lobby.setText(f"READY CANDIDATES: {lobby_count}")
            self.btn_start.setEnabled(True) if lobby_count > 0 else self.btn_start.setEnabled(False)
        while SUBMITTED_RESULTS:
            res = SUBMITTED_RESULTS.pop(0)
            self.cur.execute("INSERT INTO results (name, roll, course, score, status, date, details) VALUES (?,?,?,?,?,?,?)", (res['name'], res['roll'], res['course'], f"{res['score_pct']}%", res['status'], str(datetime.now()), res['details']))
            self.conn.commit()

    def init_admin_menu(self):
        self.page_admin_menu = QWidget(); self.page_admin_menu.setObjectName("DarkPage"); self.page_admin_menu.setMouseTracking(True)
        layout = QHBoxLayout(self.page_admin_menu); layout.setContentsMargins(0,0,0,0)
        content = QWidget(); cl = QVBoxLayout(content); cl.setAlignment(Qt.AlignCenter); cl.setSpacing(30)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(650, 500)
        vl = QVBoxLayout(card); vl.setSpacing(25); vl.setContentsMargins(50,40,50,40)
        title = QLabel("ADMINISTRATION HUB"); title.setObjectName("Header"); title.setAlignment(Qt.AlignCenter)
        
        btn_config = FuturisticButton("EXAM CONFIGURATION (MAKE PAPER)"); btn_config.setFixedHeight(60); btn_config.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_config))
        btn_hist = FuturisticButton("ACCESS STUDENT DATABASE"); btn_hist.setFixedHeight(60); btn_hist.clicked.connect(self.load_history)
        btn_pwd = FuturisticButton("CHANGE SECURITY CREDENTIALS"); btn_pwd.setFixedHeight(60); btn_pwd.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_change_pwd))
        btn_back = QPushButton("LOG OUT"); btn_back.setCursor(Qt.PointingHandCursor); btn_back.setFixedSize(140, 40)
        btn_back.setStyleSheet("QPushButton { background-color: transparent; color: #EF4444; border: 2px solid #EF4444; border-radius: 8px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #EF4444; color: white; }")
        btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_dash))
        
        vl.addWidget(title); vl.addStretch(); vl.addWidget(btn_config); vl.addWidget(btn_hist); vl.addWidget(btn_pwd); vl.addStretch(); vl.addWidget(btn_back, alignment=Qt.AlignCenter)
        cl.addWidget(card); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_admin_menu)

    def init_exam_config(self):
        self.page_config = QWidget(); self.page_config.setObjectName("DarkPage"); self.page_config.setMouseTracking(True)
        layout = QHBoxLayout(self.page_config); layout.setContentsMargins(0,0,0,0); content = QWidget(); cl = QVBoxLayout(content); cl.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(800, 680); vl = QVBoxLayout(card); vl.setSpacing(10); vl.setContentsMargins(40,40,40,40)
        
        header_layout = QHBoxLayout()
        btn_back = QPushButton("←"); btn_back.setCursor(Qt.PointingHandCursor); btn_back.setFixedSize(40, 40); btn_back.setStyleSheet("QPushButton { background-color: transparent; color: #38BDF8; font-size: 28px; font-weight: bold; border: none; } QPushButton:hover { color: #00FFFF; }")
        btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_admin_menu))
        t = QLabel("EXAM CONFIGURATION"); t.setObjectName("Header"); t.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(btn_back); header_layout.addWidget(t); header_layout.addSpacing(40); vl.addLayout(header_layout); vl.addSpacing(15)

        l1 = QLabel("Select Course to Configure:"); l1.setObjectName("LabelTitle"); self.config_crs = QComboBox(); self.config_crs.addItems(COURSE_LIST); vl.addWidget(l1); vl.addWidget(self.config_crs)
        param_grid = QGridLayout(); param_grid.setSpacing(10)
        l2 = QLabel("Time Limit (Mins):"); l2.setObjectName("LabelTitle"); self.config_time = QSpinBox(); self.config_time.setRange(1, 300)
        l3 = QLabel("Total Questions:"); l3.setObjectName("LabelTitle"); self.config_total_q = QSpinBox(); self.config_total_q.setRange(1, 500)
        l4 = QLabel("Passing Score (%):"); l4.setObjectName("LabelTitle"); self.config_pass_pct = QSpinBox(); self.config_pass_pct.setRange(1, 100); self.config_pass_pct.setValue(50)

        param_grid.addWidget(l2, 0, 0); param_grid.addWidget(self.config_time, 1, 0)
        param_grid.addWidget(l3, 0, 1); param_grid.addWidget(self.config_total_q, 1, 1)
        param_grid.addWidget(l4, 0, 2); param_grid.addWidget(self.config_pass_pct, 1, 2)
        vl.addLayout(param_grid); vl.addSpacing(10)
        
        l_chap = QLabel("Select Chapters to Include in Exam:"); l_chap.setObjectName("LabelTitle")
        self.chapter_scroll = QScrollArea(); self.chapter_scroll.setWidgetResizable(True); self.chapter_widget = QWidget(); self.chapter_layout = QVBoxLayout(self.chapter_widget)
        self.chapter_widget.setStyleSheet("background-color: transparent;"); self.chapter_scroll.setWidget(self.chapter_widget)
        self.chapter_checkboxes = []; self.config_crs.currentIndexChanged.connect(self.load_course_chapters)
        btn_save = FuturisticButton("SAVE EXAM CONFIGURATION"); btn_save.clicked.connect(self.save_exam_config)
        
        vl.addWidget(l_chap); vl.addWidget(self.chapter_scroll); vl.addSpacing(10); vl.addWidget(btn_save)
        cl.addWidget(card); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_config)
        self.load_course_chapters()

    def load_course_chapters(self):
        crs = self.config_crs.currentText(); qs, chapters = extract_course_data(crs)
        for i in reversed(range(self.chapter_layout.count())): 
            widget = self.chapter_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        self.chapter_checkboxes = []
        if not chapters:
            lbl = QLabel("No files or chapters found."); lbl.setStyleSheet("color: #EF4444; font-weight: bold;"); self.chapter_layout.addWidget(lbl); return
        self.cur.execute("SELECT course_configs FROM settings WHERE id=1"); row = self.cur.fetchone()
        crs_config = (json.loads(row[0]) if row and row[0] else {}).get(crs, {})
        self.config_time.setValue(int(crs_config.get("duration", 60))); self.config_total_q.setValue(int(crs_config.get("total_q", 50))); self.config_pass_pct.setValue(int(crs_config.get("pass_pct", 50)))
        saved_chapters = crs_config.get("chapters", [])
        
        self.chk_all = QCheckBox("Select All Chapters"); self.chapter_layout.addWidget(self.chk_all)
        all_selected = True
        for chap in chapters:
            chk = QCheckBox(f"Chapter {chap}")
            if not saved_chapters or str(chap) in saved_chapters: chk.setChecked(True)
            else: chk.setChecked(False); all_selected = False
            chk.setProperty("chapter_val", str(chap)); self.chapter_checkboxes.append(chk); self.chapter_layout.addWidget(chk)
        self.chk_all.setChecked(all_selected); self.chk_all.toggled.connect(self.toggle_all_chapters); self.chapter_layout.addStretch()

    def toggle_all_chapters(self, checked):
        for chk in self.chapter_checkboxes: chk.setChecked(checked)

    def save_exam_config(self):
        crs, duration, total_q, pass_pct = self.config_crs.currentText(), self.config_time.value(), self.config_total_q.value(), self.config_pass_pct.value()
        selected_chaps = [chk.property("chapter_val") for chk in self.chapter_checkboxes if chk.isChecked()]
        self.cur.execute("SELECT course_configs FROM settings WHERE id=1"); row = self.cur.fetchone()
        configs = json.loads(row[0]) if row and row[0] else {}
        configs[crs] = { "duration": duration, "total_q": total_q, "pass_pct": pass_pct, "chapters": selected_chaps }
        self.cur.execute("UPDATE settings SET course_configs=?, exam_duration=? WHERE id=1", (json.dumps(configs), duration)); self.conn.commit()
        speaker.speak("Configuration Saved."); QMessageBox.information(self, "Success", f"Configuration dynamically saved for {crs}.")

    def init_change_pwd(self):
        self.page_change_pwd = QWidget(); self.page_change_pwd.setObjectName("DarkPage"); self.page_change_pwd.setMouseTracking(True)
        layout = QHBoxLayout(self.page_change_pwd); layout.setContentsMargins(0,0,0,0); content = QWidget(); cl = QVBoxLayout(content); cl.setAlignment(Qt.AlignCenter)
        card = QFrame(); card.setObjectName("GlassCard"); card.setFixedSize(600, 500); vl = QVBoxLayout(card); vl.setSpacing(20); vl.setContentsMargins(40,40,40,40)
        t = QLabel("UPDATE CREDENTIALS"); t.setObjectName("Header"); t.setAlignment(Qt.AlignCenter)
        l1 = QLabel("New Password 1:"); l1.setObjectName("LabelTitle"); self.i_p1 = QLineEdit(); self.i_p1.setEchoMode(QLineEdit.Password)
        l2 = QLabel("New Password 2:"); l2.setObjectName("LabelTitle"); self.i_p2 = QLineEdit(); self.i_p2.setEchoMode(QLineEdit.Password)
        btn_save = FuturisticButton("UPDATE SYSTEM"); btn_save.clicked.connect(self.save_new_passwords)
        btn_ret = QPushButton("Cancel"); btn_ret.setStyleSheet("color: white;"); btn_ret.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_admin_menu))
        vl.addWidget(t); vl.addSpacing(20); vl.addWidget(l1); vl.addWidget(self.i_p1); vl.addWidget(l2); vl.addWidget(self.i_p2); vl.addSpacing(20); vl.addWidget(btn_save); vl.addWidget(btn_ret)
        cl.addWidget(card); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_change_pwd)

    def save_new_passwords(self):
        p1, p2 = self.i_p1.text(), self.i_p2.text()
        if p1 and p2:
            self.cur.execute("UPDATE settings SET pass1=?, pass2=? WHERE id=1", (p1, p2)); self.conn.commit()
            speaker.speak("Credentials Updated."); QMessageBox.information(self, "Success", "Security credentials updated successfully.")
            self.i_p1.clear(); self.i_p2.clear(); self.stack.setCurrentWidget(self.page_admin_menu)
        else: self.show_error("Error", "Fields cannot be empty.")

    def init_history(self):
        self.page_hist = QWidget(); self.page_hist.setObjectName("LightPage")
        layout = QHBoxLayout(self.page_hist); layout.setContentsMargins(0,0,0,0); content = QWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(40,40,40,40); cl.setSpacing(20)
        h = QHBoxLayout(); l = QLabel("ADMIN DATABASE"); l.setObjectName("Header"); l.setStyleSheet("color: #0F172A;")
        self.chart = CGIDonutChart(); b = FuturisticButton("EXPORT TO EXCEL"); b.setFixedSize(180, 45); b.clicked.connect(self.export_excel)
        b_back = QPushButton("Back to Menu"); b_back.setFixedSize(120, 45); b_back.setStyleSheet("background: #64748B; color: white; border-radius: 5px; font-weight: bold;"); b_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_admin_menu))
        h.addWidget(l); h.addStretch(); h.addWidget(self.chart); h.addSpacing(20); h.addWidget(b_back); h.addWidget(b)
        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["ID", "Name", "Roll Number", "Course", "Score", "Date", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.verticalHeader().setVisible(False)
        cl.addLayout(h); cl.addWidget(self.table); layout.addWidget(self.create_sidebar()); layout.addWidget(content); self.stack.addWidget(self.page_hist)

    def load_history(self):
        self.cur.execute("SELECT COUNT(*), status FROM results GROUP BY status"); rows = self.cur.fetchall()
        t, p = sum(c for c, s in rows), sum(c for c, s in rows if s == "QUALIFIED")
        self.chart.update_values(t, p)
        self.cur.execute("SELECT id, name, roll, course, score, date, details FROM results ORDER BY id DESC"); rows = self.cur.fetchall()
        self.table.setRowCount(0)
        for r, row in enumerate(rows):
            self.table.insertRow(r)
            for i in range(6): self.table.setItem(r, i, QTableWidgetItem(str(row[i])))
            btn_report = QPushButton("📄 REPORT"); btn_report.setStyleSheet("background-color: #3B82F6; color: white; border-radius: 5px; font-weight: bold;"); btn_report.clicked.connect(lambda checked, rd=row: self.generate_html_report(rd)); self.table.setCellWidget(r, 6, btn_report)
        self.stack.setCurrentWidget(self.page_hist)

    def generate_html_report(self, row_data):
        student_name, roll, course, score, raw_details = row_data[1], row_data[2], row_data[3], row_data[4], row_data[6]
        if not raw_details: QMessageBox.information(self, "No Data", "Detailed logs are not available for this exam."); return
        try:
            details = json.loads(raw_details); total_q = len(details)
            correct_count = sum(1 for item in details if item['user'] == item['correct'])
            blank_count = sum(1 for item in details if item['user'] in ["Not Answered", "", None])
            wrong_count = total_q - correct_count - blank_count
            cp, wp, bp = (correct_count/total_q)*100 if total_q>0 else 0, (wrong_count/total_q)*100 if total_q>0 else 0, (blank_count/total_q)*100 if total_q>0 else 0
        except Exception as e: QMessageBox.warning(self, "Report Error", f"Could not parse details: {e}"); return
        
        # Dense HTML construction to guarantee it doesn't get cut off
        html = f"""<html><head><style>
        body {{ font-family: 'Segoe UI', sans-serif; padding: 40px; background: #F1F5F9; }}
        .c {{ background: white; padding: 40px; max-width: 800px; margin: auto; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #1E3A8A; border-bottom: 2px solid #CBD5E1; padding-bottom: 10px; }}
        .m {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; font-size: 16px; font-weight: bold; color: #475569; }}
        .m span {{ color: #0F172A; }}
        .s {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
        .b {{ padding: 30px 15px; border-radius: 15px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.05); }}
        .v {{ font-size: 38px; font-weight: 900; line-height: 1; }}
        .l {{ font-size: 15px; font-weight: 600; margin-top: 10px; }}
        .q {{ margin-bottom: 20px; padding: 15px; border: 1px solid #E2E8F0; border-radius: 8px; }}
        .qt {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; }}
        </style></head><body><div class="c">
        <h1>OFFICIAL MID-TERM REPORT <span style="float: right; background: #1E3A8A; color: white; padding: 5px 10px; border-radius: 5px; font-size: 14px;">{score}</span></h1>
        <div class="m"><div>Student Name: <span>{student_name}</span></div><div>Roll Number: <span>{roll}</span></div><div>Course: <span>{course}</span></div><div>Date: <span>{row_data[5]}</span></div></div>
        <div class="s">
            <div class="b" style="background: linear-gradient(135deg, #0F172A, #1E293B); border-bottom: 5px solid #38BDF8;"><div class="v" style="color: white;">{total_q}</div><div class="l" style="color: #94A3B8;">Total Questions</div></div>
            <div class="b" style="background: linear-gradient(135deg, #064E3B, #022C22); border-bottom: 5px solid #10B981;"><div class="v" style="color: #4ADE80;">{cp:.1f}%</div><div class="l" style="color: #A7F3D0;">{correct_count} Correct</div></div>
            <div class="b" style="background: linear-gradient(135deg, #7F1D1D, #450A0A); border-bottom: 5px solid #EF4444;"><div class="v" style="color: #F87171;">{wp:.1f}%</div><div class="l" style="color: #FECACA;">{wrong_count} Incorrect</div></div>
            <div class="b" style="background: linear-gradient(135deg, #78350F, #451A03); border-bottom: 5px solid #F59E0B;"><div class="v" style="color: #FCD34D;">{bp:.1f}%</div><div class="l" style="color: #FDE68A;">{blank_count} Skipped</div></div>
        </div>
        <h2 style="color: #1E3A8A; font-size: 22px; margin-bottom: 20px;">Detailed Analysis</h2>
        """
        for i, item in enumerate(details):
            bc = "#10B981" if item['user'] == item['correct'] else "#EF4444"
            si = "✔" if item['user'] == item['correct'] else "✘"
            html += f'<div class="q" style="border-left: 5px solid {bc};"><div class="qt">Q{i+1}: {item["q"]}</div><div style="font-size:14px;">User Selected: <span style="color:{bc}; font-weight:bold;">{item["user"]} {si}</span></div><div style="font-size:14px;">Correct Answer: <span style="color:#0F172A; font-weight:bold;">{item["correct"]}</span></div></div>'
        html += '<div style="text-align:center; margin-top:40px; color:#94A3B8; font-size:12px; font-weight:bold;">Generated by AMSC Exam System. Press Ctrl+P to Save as PDF.</div></div></body></html>'
        
        filename = f"Report_{roll}_{student_name}.html".replace(" ", "_")
        with open(filename, "w", encoding="utf-8") as f: f.write(html)
        webbrowser.open('file://' + os.path.realpath(filename)); speaker.speak("Report generated.")

    def export_excel(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Excel", "student_results.csv", "CSV Files (*.csv)")
        if f:
            self.cur.execute("SELECT id, name, roll, course, score, status, date FROM results"); data = self.cur.fetchall()
            try:
                with open(f, 'w', newline='', encoding='utf-8-sig') as file: csv.writer(file).writerows([["ID", "Name", "Roll", "Course", "Score", "Status", "Date"]] + data)
                speaker.speak("Export Complete."); QMessageBox.information(self, "Export Successful", "Data exported successfully.")
            except Exception as e: self.show_error("Export Failed", str(e))

if __name__ == "__main__":
    app = QApplication.instance()
    if not app: app = QApplication(sys.argv)
    w = StudentTerminalSoftware(); w.showMaximized(); sys.exit(app.exec())