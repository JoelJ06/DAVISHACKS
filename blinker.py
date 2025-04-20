import sys
import cv2
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMainWindow
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
import numpy as np
import pyautogui

class BlinkDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Blink Counter')
        self.blink_count = 0
        self.is_blinking = False
        self.calibrated = False
        self.calibration_points = []
        self.screen_points = []
        self.calibration_step = 0
        self.gaze_history = []
        self.gaze_history_len = 5
        self.smoothed_gaze = None
        self.last_cursor_pos = None
        self.move_threshold = 20
        self.smoothing_alpha = 0.3
        self.pause_on_still = True
        self.still_threshold = 15  # pixels
        self.still_time_required = 1.5  # seconds
        self.last_still_time = None
        self.is_paused = False
        self.scroll_zone_height = 80  # pixels from top/bottom edge
        self.scroll_delay = 0.7  # seconds to trigger scroll
        self.last_scroll_time = 0
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
        if len(self.calibration_points) < 5:
            return None
        (tl, tr, br, bl, center) = self.calibration_points
        (stl, str_, sbr, sbl, sc) = self.screen_points
        # Use min/max from calibration points for normalization
        min_x = min([p[0] for p in [tl, tr, br, bl]])
        max_x = max([p[0] for p in [tl, tr, br, bl]])
        min_y = min([p[1] for p in [tl, tr, br, bl]])
        max_y = max([p[1] for p in [tl, tr, br, bl]])
        # Clamp iris_x and iris_y to calibration range
        iris_x = max(min_x, min(max_x, iris_x))
        iris_y = max(min_y, min(max_y, iris_y))
        # Map normalized gaze to full screen
        rx = 1 - ((iris_x - min_x) / (max_x - min_x) if max_x != min_x else 0.5)
        ry = (iris_y - min_y) / (max_y - min_y) if max_y != min_y else 0.5
        screen_w, screen_h = pyautogui.size()
        sx = int(rx * (screen_w - 1))
        sy = int(ry * (screen_h - 1))
        return sx, sy

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
                        # Adaptive smoothing and dead zone
                        if self.smoothed_gaze is None:
                            self.smoothed_gaze = mapped
                        else:
                            dx = mapped[0] - self.smoothed_gaze[0]
                            dy = mapped[1] - self.smoothed_gaze[1]
                            dist = (dx ** 2 + dy ** 2) ** 0.5
                            dead_zone = 25
                            if dist < dead_zone:
                                pass
                            else:
                                alpha = min(0.85, max(self.smoothing_alpha, dist / 300))
                                sx = int(alpha * mapped[0] + (1 - alpha) * self.smoothed_gaze[0])
                                sy = int(alpha * mapped[1] + (1 - alpha) * self.smoothed_gaze[1])
                                self.smoothed_gaze = (sx, sy)
                        # Pause cursor if gaze is steady
                        if self.last_cursor_pos is not None and abs(self.smoothed_gaze[0] - self.last_cursor_pos[0]) < self.still_threshold and abs(self.smoothed_gaze[1] - self.last_cursor_pos[1]) < self.still_threshold:
                            if self.last_still_time is None:
                                self.last_still_time = time.time()
                            elif time.time() - self.last_still_time > self.still_time_required:
                                self.is_paused = True
                        else:
                            self.last_still_time = None
                            self.is_paused = False
                        if not self.is_paused:
                            pyautogui.moveTo(self.smoothed_gaze[0], self.smoothed_gaze[1], duration=0.08)
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
            dwell_spin.setValue(1.0)
            dwell_spin.setMinimum(0.2)
            dwell_spin.setMaximum(3.0)
            dwell_spin.setSingleStep(0.1)
            dwell_spin.valueChanged.connect(lambda v: None)
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
        self.cap.release()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BlinkDetector()
    window.show()
    sys.exit(app.exec_())