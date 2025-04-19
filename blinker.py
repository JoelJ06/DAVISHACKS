import sys
import cv2
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
import numpy as np

class BlinkDetector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Blink Counter')
        self.blink_count = 0
        self.is_blinking = False
        self.init_ui()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]

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

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_ear = self.eye_aspect_ratio(face_landmarks, self.LEFT_EYE)
                right_ear = self.eye_aspect_ratio(face_landmarks, self.RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0
                if ear < 0.21:
                    if not self.is_blinking:
                        self.blink_count += 1
                        self.blink_label.setText(f'Blinks: {self.blink_count}')
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

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BlinkDetector()
    window.show()
    sys.exit(app.exec_())
