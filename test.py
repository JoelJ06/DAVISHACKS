import cv2
import mediapipe as mp
import time

# Initialize mediapipe face mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils
drawing_spec = mp_draw.DrawingSpec(thickness=1, circle_radius=1)

# Initialize webcam
cap = cv2.VideoCapture(0)

# Variables for blink detection
blink_counter = 0
last_blink_time = time.time()
EYE_AR_THRESH = 0.2
eye_closed = False

def calculate_EAR(eye_landmarks, face_landmarks):
    # Get the vertical distance between upper and lower eyelid
    upper_lid = face_landmarks.landmark[eye_landmarks[0]]
    lower_lid = face_landmarks.landmark[eye_landmarks[1]]
    return abs(upper_lid.y - lower_lid.y)

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Failed to read from webcam")
        continue

    image = cv2.flip(image, 1)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)
    image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            mp_draw.draw_landmarks(
                image=image,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=drawing_spec,
                connection_drawing_spec=drawing_spec)
            
            # Get nose tip and eye landmarks
            nose_tip = face_landmarks.landmark[1]
            left_eye = face_landmarks.landmark[33]
            right_eye = face_landmarks.landmark[263]
            
            # Calculate EAR (Eye Aspect Ratio) for both eyes
            left_ear = calculate_EAR([159, 145], face_landmarks)  # Upper and lower eyelid indices
            right_ear = calculate_EAR([386, 374], face_landmarks)
            ear = (left_ear + right_ear) / 2
            
            # Detect blink
            if ear < EYE_AR_THRESH and not eye_closed:
                eye_closed = True
                if time.time() - last_blink_time > 0.2:  # Minimum time between blinks
                    blink_counter += 1
                    last_blink_time = time.time()
            elif ear >= EYE_AR_THRESH:
                eye_closed = False
            
            # Calculate direction
            direction_h = "Center"
            direction_v = "Center"
            
            if nose_tip.x < left_eye.x and nose_tip.x < right_eye.x:
                direction_h = "Left"
            elif nose_tip.x > left_eye.x and nose_tip.x > right_eye.x:
                direction_h = "Right"
                
            if nose_tip.y < left_eye.y and nose_tip.y < right_eye.y:
                direction_v = "Up"
            elif nose_tip.y > left_eye.y and nose_tip.y > right_eye.y:
                direction_v = "Down"
            
            # Display direction and blink count
            cv2.putText(image, f"Looking: {direction_h} {direction_v}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(image, f"Blinks: {blink_counter}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow('Face Mesh', image)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()