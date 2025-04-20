import cv2
import numpy as np
import mediapipe as mp
import time
import pyautogui  # Import the pyautogui library

class ClickController:
    """Class to manage clicking functionality with the right hand"""
    def __init__(self):
        self.is_clicking = False
        self.touching_threshold = 40  # Threshold for determining if fingers are touching
    
    def update_click_state(self, thumb_pos, index_pos):
        """Update the clicking state based on thumb and index finger positions"""
        # Calculate distance between thumb and index finger
        distance = np.sqrt((thumb_pos[0] - index_pos[0])**2 + (thumb_pos[1] - index_pos[1])**2)
        
        # Update click state
        prev_clicking = self.is_clicking
        self.is_clicking = distance < self.touching_threshold
        
        # Handle mouse button state changes
        if self.is_clicking and not prev_clicking:
            # Start a new click (press down)
            pyautogui.mouseDown()
            click_color = (0, 0, 255)  # Red when clicking
        elif not self.is_clicking and prev_clicking:
            # Release the click
            pyautogui.mouseUp()
            click_color = (0, 255, 0)  # Green when not clicking
        else:
            # Maintain current state
            if self.is_clicking:
                # Ensure mouse stays down while fingers are touching
                self.check_and_hold_click()
                click_color = (0, 0, 255)  # Red when clicking
            else:
                click_color = (0, 255, 0)  # Green when not clicking
            
        return click_color
    
    def reset(self):
        """Reset the clicking state when hand is not detected"""
        if self.is_clicking:
            pyautogui.mouseUp()
            self.is_clicking = False

    def check_and_hold_click(self):
        """Continuously hold mouse button down if clicking state is true"""
        if self.is_clicking:
            pyautogui.mouseDown()

class FingerTracker:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.finger_position = (0, 0)
        self.is_tracking = False
        
        # Get screen size for cursor boundary checks
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Initialize MediaPipe solutions
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Allow detection of both hands
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Create click controller for right hand
        self.click_controller = ClickController()

    def track_finger(self):
        """Track the index fingertip position in the video and move cursor"""
        print("Put your left hand in the frame for tracking and right hand for clicking...")
        
        # Ensure PyAutoGUI doesn't raise exceptions when mouse hits screen edge
        pyautogui.FAILSAFE = False
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # Flip the frame horizontally for a more intuitive experience
            frame = cv2.flip(frame, 1)
            
            # Convert the BGR image to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame and find hands
            results = self.hands.process(rgb_frame)
            
            # Reset tracking status
            right_hand_tracking = False
            left_hand_tracking = False
            
            # Draw hand landmarks on the image
            if results.multi_hand_landmarks and results.multi_handedness:
                # Iterate through detected hands
                for idx, (hand_landmarks, handedness) in enumerate(zip(results.multi_hand_landmarks, results.multi_handedness)):
                    # Get hand type
                    hand_type = handedness.classification[0].label
                    
                    # Draw the hand landmarks
                    self.mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing_styles.get_default_hand_landmarks_style(),
                        self.mp_drawing_styles.get_default_hand_connections_style()
                    )
                    
                    h, w, c = frame.shape
                    
                    # Get the position of the index finger tip (landmark 8)
                    index_finger_tip = hand_landmarks.landmark[8]
                    # Get the position of the thumb tip (landmark 4)
                    thumb_tip = hand_landmarks.landmark[4]
                    
                    # Convert normalized coordinates to pixel coordinates
                    x_px = min(int(index_finger_tip.x * w), w - 1)
                    y_px = min(int(index_finger_tip.y * h), h - 1)
                    
                    # Convert thumb tip coordinates
                    thumb_x = min(int(thumb_tip.x * w), w - 1)
                    thumb_y = min(int(thumb_tip.y * h), h - 1)
                    
                    if hand_type == "Left":  # This is the right hand in mirrored view
                        right_hand_tracking = True
                        # Handle clicking with right hand
                        click_color = self.click_controller.update_click_state((thumb_x, thumb_y), (x_px, y_px))
                        
                        # Draw visualization for right hand (clicking hand)
                        cv2.circle(frame, (x_px, y_px), 10, (255, 0, 255), -1)  # Purple for right hand index
                        cv2.circle(frame, (thumb_x, thumb_y), 10, (255, 0, 255), -1)  # Purple for right hand thumb
                        cv2.line(frame, (x_px, y_px), (thumb_x, thumb_y), click_color, 2)
                        
                        # Draw text for right hand
                        cv2.putText(frame, "Right Hand (Clicking)", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, (255, 0, 255), 2)
                        cv2.putText(frame, f"Clicking: {self.click_controller.is_clicking}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, click_color, 2)
                        
                    elif hand_type == "Right":  # This is the left hand in mirrored view
                        left_hand_tracking = True
                        
                        # Update finger position for cursor control
                        self.finger_position = (x_px, y_px)
                        
                        # Map camera coordinates to screen coordinates
                        screen_x = int(x_px * self.screen_width / w)
                        screen_y = int(y_px * self.screen_height / h)
                        
                        # Move mouse cursor to the mapped position
                        pyautogui.moveTo(screen_x, screen_y)
                        
                        # Draw visualization for left hand (tracking hand)
                        cv2.circle(frame, (x_px, y_px), 10, (0, 255, 0), -1)  # Green for left hand index
                        cv2.circle(frame, (thumb_x, thumb_y), 10, (0, 255, 0), -1)  # Green for left hand thumb
                        
                        # Draw text for left hand
                        cv2.putText(frame, "Left Hand (Tracking)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, (0, 255, 0), 2)
                        cv2.putText(frame, f"Position: ({x_px}, {y_px})", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.7, (0, 255, 0), 2)
            
            # Update tracking status
            self.is_tracking = left_hand_tracking
            
            # Reset click controller if right hand not detected
            if not right_hand_tracking:
                self.click_controller.reset()
            
            # Draw text showing status when hands are not detected
            if not left_hand_tracking:
                cv2.putText(frame, "No left hand detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
            
            if not right_hand_tracking:
                cv2.putText(frame, "No right hand detected", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (255, 0, 255), 2)
                
            # Display the resulting frame
            cv2.imshow('MediaPipe Hand Tracking', frame)
            
            # Exit on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Clean up
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_finger_position(self):
        """Return the current finger position and tracking status"""
        return self.finger_position, self.is_tracking, self.click_controller.is_clicking

# Example usage
if __name__ == "__main__":
    tracker = FingerTracker()
    tracker.track_finger()
