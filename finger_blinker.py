import sys
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMainWindow
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen

class FingerOverlay(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.cursor_pos = None
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.showFullScreen()
        self.hide()

    def set_cursor(self, pos):
        self.cursor_pos = pos
        self.update()

    def paintEvent(self, event):
        if self.cursor_pos:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(255, 0, 0, 180), 4)
            painter.setPen(pen)
            x, y = self.cursor_pos
            painter.drawEllipse(x-15, y-15, 30, 30)
            painter.drawLine(x-25, y, x+25, y)
            painter.drawLine(x, y-25, x, y+25)

class FingerBlinker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Finger Tracking Cursor')
        self.click_count = 0
        self.is_pinching = False
        self.init_ui()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.smoothing_alpha = 0.18  # More smoothing for less wobble
        self.smoothed_pos = None
        self.last_cursor_pos = None
        self.move_threshold = 8  # Lower threshold for more frequent but smaller moves
        self.dead_zone = 35  # Larger dead zone for less jitter
        self.pinch_threshold = 0.07
        self.pinch_release_threshold = 0.10
        self.pinch_active = False
        self.left_pinch_threshold = 0.07
        self.left_pinch_release_threshold = 0.10
        self.left_pinch_active = False
        self.overlay = FingerOverlay()
        # Calibration logic (like eye tracker)
        self.calibrated = False
        self.calibration_points = []  # [(x, y) in camera frame]
        self.screen_points = []  # [(screen_x, screen_y)]
        self.calibration_step = 0
        self.calibration_instructions = [
            'Move your finger to the TOP-LEFT of the camera view and press SPACE',
            'Move your finger to the TOP-RIGHT and press SPACE',
            'Move your finger to the BOTTOM-RIGHT and press SPACE',
            'Move your finger to the BOTTOM-LEFT and press SPACE',
            'Move your finger to the CENTER and press SPACE',
        ]
        self.current_instruction = QLabel(self.calibration_instructions[0])
        self.current_instruction.setAlignment(Qt.AlignCenter)
        self.layout().insertWidget(0, self.current_instruction)
        self.calibrate_button = QPushButton('Calibrate Point')
        self.calibrate_button.clicked.connect(self.calibrate_point)
        self.layout().insertWidget(1, self.calibrate_button)
        self.calibration_frames_required = 5
        self.calibration_frame_buffer = []
        self.setFocusPolicy(Qt.StrongFocus)
        self.dwell_time = 1.2  # Increase dwell time to 1.2 seconds for longer wait before click
        self.dwell_start_time = None
        self.dwell_indicator = QLabel('')
        self.dwell_indicator.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.dwell_indicator)

    def init_ui(self):
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.click_label = QLabel('Clicks: 0')
        self.click_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.click_label)
        self.setLayout(layout)

    def reset_count(self):
        self.click_count = 0
        self.click_label.setText(f'Clicks: {self.click_count}')

    def calibrate_point(self):
        # Collect several frames to ensure stable detection
        collected = 0
        buffer = []
        for _ in range(self.calibration_frames_required):
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)  # Flip the frame horizontally for natural webcam view
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                index_tip = hand_landmarks.landmark[8]
                cam_x = 1 - index_tip.x  # Invert x for correct left/right
                cam_y = index_tip.y
                buffer.append((cam_x, cam_y))
                collected += 1
        if collected == self.calibration_frames_required:
            avg_x = sum([pt[0] for pt in buffer]) / collected
            avg_y = sum([pt[1] for pt in buffer]) / collected
            self.calibration_points.append((avg_x, avg_y))
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
            if self.calibration_step < len(self.calibration_instructions):
                self.current_instruction.setText(self.calibration_instructions[self.calibration_step])
            else:
                self.calibrated = True
                self.current_instruction.setText('Calibration complete!')
        else:
            self.current_instruction.setText('No hand detected, try again!')

    def keyPressEvent(self, event):
        if not self.calibrated and event.key() == Qt.Key_Space:
            self.calibrate_point()

    def map_finger_to_screen(self, cam_x, cam_y):
        if len(self.calibration_points) < 5:
            return None
        (tl, tr, br, bl, center) = self.calibration_points
        (stl, str_, sbr, sbl, sc) = self.screen_points
        min_x = min([p[0] for p in [tl, tr, br, bl]])
        max_x = max([p[0] for p in [tl, tr, br, bl]])
        min_y = min([p[1] for p in [tl, tr, br, bl]])
        max_y = max([p[1] for p in [tl, tr, br, bl]])
        cam_x = max(min_x, min(max_x, cam_x))
        cam_y = max(min_y, min(max_y, cam_y))
        rx = (cam_x - min_x) / (max_x - min_x) if max_x != min_x else 0.5
        ry = (cam_y - min_y) / (max_y - min_y) if max_y != min_y else 0.5
        screen_w, screen_h = pyautogui.size()
        sx = int(rx * (screen_w - 1))
        sy = int(ry * (screen_h - 1))
        return sx, sy

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        screen_w, screen_h = pyautogui.size()
        mouse_x, mouse_y = pyautogui.position()
        self.overlay.set_cursor((mouse_x, mouse_y))
        self.overlay.show()
        # Calibration mode: show fingertip indicator if detected
        if not self.calibrated:
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    index_tip = hand_landmarks.landmark[8]
                    fx = int(index_tip.x * rgb_frame.shape[1])
                    fy = int(index_tip.y * rgb_frame.shape[0])
                    cv2.circle(rgb_frame, (fx, fy), 18, (0, 255, 0), 3)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(qt_image))
            return
        right_hand = None
        left_hand = None
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                if label == 'Right':
                    right_hand = hand_landmarks
                elif label == 'Left':
                    left_hand = hand_landmarks
        # Cursor movement: always allow if right hand is visible
        if right_hand:
            index_tip = right_hand.landmark[8]
            cam_x = index_tip.x
            cam_y = index_tip.y
            mapped = self.map_finger_to_screen(cam_x, cam_y)
            if mapped:
                x, y = mapped
                if self.smoothed_pos is None:
                    self.smoothed_pos = (x, y)
                else:
                    dx = x - self.smoothed_pos[0]
                    dy = y - self.smoothed_pos[1]
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    if dist < self.dead_zone:
                        self.smoothed_pos = self.smoothed_pos
                    else:
                        alpha = min(0.85, max(self.smoothing_alpha, dist / 300))
                        sx = int(alpha * x + (1 - alpha) * self.smoothed_pos[0])
                        sy = int(alpha * y + (1 - alpha) * self.smoothed_pos[1])
                        self.smoothed_pos = (sx, sy)
                if self.last_cursor_pos is None or (abs(self.smoothed_pos[0] - self.last_cursor_pos[0]) > self.move_threshold or abs(self.smoothed_pos[1] - self.last_cursor_pos[1]) > self.move_threshold):
                    pyautogui.moveTo(self.smoothed_pos[0], self.smoothed_pos[1], duration=0)
                    self.last_cursor_pos = self.smoothed_pos
                # Visual feedback for right hand (blue circle)
                fx = int(index_tip.x * rgb_frame.shape[1])
                fy = int(index_tip.y * rgb_frame.shape[0])
                cv2.circle(rgb_frame, (fx, fy), 14, (255, 0, 0), 3)
        # Left hand pinch-to-click
        if left_hand:
            l_index_tip = left_hand.landmark[8]
            l_thumb_tip = left_hand.landmark[4]
            l_dist = ((l_index_tip.x - l_thumb_tip.x) ** 2 + (l_index_tip.y - l_thumb_tip.y) ** 2) ** 0.5
            if l_dist < self.left_pinch_threshold and not self.left_pinch_active:
                pyautogui.click()
                self.click_count += 1
                self.click_label.setText(f'Clicks: {self.click_count}')
                self.left_pinch_active = True
                # Visual feedback for left hand pinch (red circle)
                fx = int(l_index_tip.x * rgb_frame.shape[1])
                fy = int(l_index_tip.y * rgb_frame.shape[0])
                cv2.circle(rgb_frame, (fx, fy), 30, (0, 0, 255), 4)
            elif l_dist > self.left_pinch_release_threshold:
                self.left_pinch_active = False
            # Visual feedback for left hand (green circle)
            fx = int(l_index_tip.x * rgb_frame.shape[1])
            fy = int(l_index_tip.y * rgb_frame.shape[0])
            cv2.circle(rgb_frame, (fx, fy), 14, (0, 255, 0), 3)
        # Draw crosshair at current mouse position (visual feedback)
        # Instead of using pyautogui.position(), use self.smoothed_pos for immediate feedback
        if self.smoothed_pos is not None:
            fx = int(self.smoothed_pos[0] * rgb_frame.shape[1] / screen_w)
            fy = int(self.smoothed_pos[1] * rgb_frame.shape[0] / screen_h)
            cv2.drawMarker(rgb_frame, (fx, fy), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def closeEvent(self, event):
        self.cap.release()
        self.overlay.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FingerBlinker()
    window.show()
    sys.exit(app.exec_())
