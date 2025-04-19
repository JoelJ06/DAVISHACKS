import sys
import cv2
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMainWindow
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
import numpy as np
import pyautogui

class GazeOverlay(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.gaze_pos = None
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.showFullScreen()
        self.hide()

    def set_gaze(self, pos):
        self.gaze_pos = pos
        self.update()

    def paintEvent(self, event):
        if self.gaze_pos:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(0, 255, 0, 180), 4)
            painter.setPen(pen)
            x, y = self.gaze_pos
            painter.drawEllipse(x-15, y-15, 30, 30)
            painter.drawLine(x-25, y, x+25, y)
            painter.drawLine(x, y-25, x, y+25)

class BlinkDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Blink Counter')
        self.blink_count = 0
        self.is_blinking = False
        self.calibrated = False
        self.calibration_points = []  # [(iris_x, iris_y), ...]
        self.screen_points = []  # [(screen_x, screen_y), ...]
        self.calibration_step = 0
        self.gaze_history = []  # For smoothing
        self.gaze_history_len = 5  # Number of points to average
        self.smoothed_gaze = None  # For exponential smoothing
        self.last_cursor_pos = None  # For movement threshold
        self.move_threshold = 20  # Minimum pixels to move cursor
        self.smoothing_alpha = 0.3  # Smoothing factor (0 < alpha < 1)
        self.init_ui()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.instructions = [
            'Look at the TOP-LEFT corner and press SPACE',
            'Look at the TOP-RIGHT corner and press SPACE',
            'Look at the BOTTOM-RIGHT corner and press SPACE',
            'Look at the BOTTOM-LEFT corner and press SPACE',
            'Look at the CENTER and press SPACE',
        ]
        self.current_instruction = QLabel(self.instructions[0])
        self.current_instruction.setAlignment(Qt.AlignCenter)
        self.layout().insertWidget(0, self.current_instruction)
        self.recalibrate_button = QPushButton('Recalibrate')
        self.recalibrate_button.clicked.connect(self.start_recalibration)
        self.layout().addWidget(self.recalibrate_button)
        self.settings_button = QPushButton('Settings')
        self.settings_button.clicked.connect(self.open_settings)
        self.layout().addWidget(self.settings_button)
        self.settings_window = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.overlay = GazeOverlay()

    def init_ui(self):
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.blink_label = QLabel('Blinks: 0')
        self.blink_label.setAlignment(Qt.AlignCenter)
        self.reset_button = QPushButton('Reset')
        self.reset_button.clicked.connect(self.reset_count)
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.blink_label)
        layout.addWidget(self.reset_button)
        self.setLayout(layout)

    def reset_count(self):
        self.blink_count = 0
        self.blink_label.setText(f'Blinks: {self.blink_count}')

    def keyPressEvent(self, event):
        if not self.calibrated and event.key() == Qt.Key_Space:
            iris_pos = self.get_iris_position()
            if iris_pos:
                self.calibration_points.append(iris_pos)
                screen_w, screen_h = pyautogui.size()
                screen_targets = [
                    (0, 0),
                    (screen_w-1, 0),
                    (screen_w-1, screen_h-1),
                    (0, screen_h-1),
                    (screen_w//2, screen_h//2)
                ]
                self.screen_points.append(screen_targets[self.calibration_step])
                self.calibration_step += 1
                if self.calibration_step < len(self.instructions):
                    self.current_instruction.setText(self.instructions[self.calibration_step])
                else:
                    self.calibrated = True
                    self.current_instruction.setText('Calibration complete!')
            else:
                self.current_instruction.setText('Iris not detected, try again!')

    def get_iris_position(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        iris_idx = 468
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                if len(face_landmarks.landmark) > iris_idx:
                    iris = face_landmarks.landmark[iris_idx]
                    iris_x = iris.x
                    iris_y = iris.y
                    return (iris_x, iris_y)
        return None

    def map_iris_to_screen(self, iris_x, iris_y):
        # Simple linear mapping using calibration points
        if len(self.calibration_points) < 5:
            return None
        # Use center and corners for bilinear interpolation
        # Unpack calibration
        (tl, tr, br, bl, center) = self.calibration_points
        (stl, str_, sbr, sbl, sc) = self.screen_points
        # Find weights for bilinear interpolation
        # For simplicity, use average of x and y ratios
        min_x = min([p[0] for p in [tl, tr, br, bl]])
        max_x = max([p[0] for p in [tl, tr, br, bl]])
        min_y = min([p[1] for p in [tl, tr, br, bl]])
        max_y = max([p[1] for p in [tl, tr, br, bl]])
        rx = 1 - ((iris_x - min_x) / (max_x - min_x) if max_x != min_x else 0.5)  # Invert X for correct direction
        ry = (iris_y - min_y) / (max_y - min_y) if max_y != min_y else 0.5
        # Interpolate screen position
        sx = stl[0] * (1 - rx) * (1 - ry) + str_[0] * rx * (1 - ry) + sbr[0] * rx * ry + sbl[0] * (1 - rx) * ry
        sy = stl[1] * (1 - rx) * (1 - ry) + str_[1] * rx * (1 - ry) + sbr[1] * rx * ry + sbl[1] * (1 - rx) * ry
        # Optionally blend with center
        sx = (sx + sc[0]) / 2
        sy = (sy + sc[1]) / 2
        return int(sx), int(sy)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        screen_w, screen_h = pyautogui.size()
        import time
        if self.calibrated and results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_ear = self.eye_aspect_ratio(face_landmarks, self.LEFT_EYE)
                right_ear = self.eye_aspect_ratio(face_landmarks, self.RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0
                iris_idx = 468
                if len(face_landmarks.landmark) > iris_idx:
                    iris = face_landmarks.landmark[iris_idx]
                    iris_x = iris.x
                    iris_y = iris.y
                    mapped = self.map_iris_to_screen(iris_x, iris_y)
                    if mapped:
                        # Exponential smoothing
                        if self.smoothed_gaze is None:
                            self.smoothed_gaze = mapped
                        else:
                            sx = int(self.smoothing_alpha * mapped[0] + (1 - self.smoothing_alpha) * self.smoothed_gaze[0])
                            sy = int(self.smoothing_alpha * mapped[1] + (1 - self.smoothing_alpha) * self.smoothed_gaze[1])
                            self.smoothed_gaze = (sx, sy)
                        self.overlay.set_gaze(self.smoothed_gaze)
                        self.overlay.show()
                        # Only move cursor if moved enough
                        if self.last_cursor_pos is None or (abs(self.smoothed_gaze[0] - self.last_cursor_pos[0]) > self.move_threshold or abs(self.smoothed_gaze[1] - self.last_cursor_pos[1]) > self.move_threshold):
                            pyautogui.moveTo(self.smoothed_gaze[0], self.smoothed_gaze[1], duration=0.18)
                            self.last_cursor_pos = self.smoothed_gaze
                if ear < 0.21:
                    if not self.is_blinking:
                        self.blink_count += 1
                        self.blink_label.setText(f'Blinks: {self.blink_count}')
                        pyautogui.click()
                        self.is_blinking = True
                else:
                    self.is_blinking = False
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def eye_aspect_ratio(self, face_landmarks, eye_indices):
        points = [face_landmarks.landmark[i] for i in eye_indices]
        p = lambda i: np.array([points[i].x, points[i].y])
        # Compute EAR
        A = np.linalg.norm(p(1) - p(5))
        B = np.linalg.norm(p(2) - p(4))
        C = np.linalg.norm(p(0) - p(3))
        ear = (A + B) / (2.0 * C)
        return ear

    def start_recalibration(self):
        self.calibrated = False
        self.calibration_points = []
        self.screen_points = []
        self.calibration_step = 0
        self.current_instruction.setText(self.instructions[0])
        self.smoothed_gaze = None
        self.last_cursor_pos = None

    def open_settings(self):
        if self.settings_window is None:
            from PyQt5.QtWidgets import QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton
            self.settings_window = QDialog(self)
            self.settings_window.setWindowTitle('Settings')
            layout = QFormLayout()
            dwell_spin = QDoubleSpinBox()
            dwell_spin.setValue(self.dwell_time)
            dwell_spin.setMinimum(0.2)
            dwell_spin.setMaximum(3.0)
            dwell_spin.setSingleStep(0.1)
            dwell_spin.valueChanged.connect(lambda v: setattr(self, 'dwell_time', v))
            layout.addRow('Dwell Click Time (s):', dwell_spin)
            threshold_spin = QSpinBox()
            threshold_spin.setValue(self.move_threshold)
            threshold_spin.setMinimum(1)
            threshold_spin.setMaximum(100)
            threshold_spin.valueChanged.connect(lambda v: setattr(self, 'move_threshold', v))
            layout.addRow('Cursor Move Threshold (px):', threshold_spin)
            smoothing_spin = QDoubleSpinBox()
            smoothing_spin.setValue(self.smoothing_alpha)
            smoothing_spin.setMinimum(0.01)
            smoothing_spin.setMaximum(0.99)
            smoothing_spin.setSingleStep(0.01)
            smoothing_spin.valueChanged.connect(lambda v: setattr(self, 'smoothing_alpha', v))
            layout.addRow('Smoothing Alpha:', smoothing_spin)
            close_btn = QPushButton('Close')
            close_btn.clicked.connect(self.settings_window.close)
            layout.addWidget(close_btn)
            self.settings_window.setLayout(layout)
        self.settings_window.show()

    def closeEvent(self, event):
        self.overlay.close()
        self.cap.release()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BlinkDetector()
    window.show()
    sys.exit(app.exec_())
