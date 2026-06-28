import cv2
import mediapipe as mp
import numpy as np
import math
import pyautogui
from pycaw.pycaw import AudioUtilities

# =======================================================
# 1. LINK TO COMPUTER HARDWARE AUDIO (PyCaw Fix Included)
# =======================================================
devices = AudioUtilities.GetSpeakers()
volume = devices.EndpointVolume  # Modern, working PyCaw syntax

volRange = volume.GetVolumeRange()
minVol = volRange[0]
maxVol = volRange[1]

volBar = 400
volPer = 0
last_action = "None"
counter = 0  # Cooldown counter to prevent rapid multi-clicks

# =======================================================
# 2. SET UP MEDIAPIPE AI ENGINE
# =======================================================
mpHands = mp.solutions.hands
hands = mpHands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
mpDraw = mp.solutions.drawing_utils

# Finger tip landmark IDs
tipIds = [4, 8, 12, 16, 20]

# =======================================================
# 3. WEBCAM STREAM WITH WINDOWS OVERRIDE
# =======================================================
# cv2.CAP_DSHOW forces Windows to instantly connect to your webcam hardware
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

print("Fresh application running... Raise your hand to the camera.")
print("Press 'q' inside the video window when you want to exit.")

while True:
    success, img = cap.read()
    if not success:
        continue # Skip corrupted frames gracefully without crashing

    img = cv2.flip(img, 1) # Mirror view
    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    lmList = []

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)
            for id, lm in enumerate(handLms.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

    # Wait until all 21 hand joints are registered before tracking movements
    if len(lmList) >= 21:
        fingers = []

        # --- THUMB TRACKING ---
        if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # --- 4 FINGERS TRACKING ---
        for id in range(1, 5):
            if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        totalFingers = fingers.count(1)

        # =======================================================
        # 4. ACTION CONTROLLER LOGIC
        # =======================================================
        
        # ✊ FIST -> MUTE VOLUME
        if totalFingers == 0:
            volume.SetMute(1, None)
            last_action = "MUTED"
            
        # ✋ FULL PALM -> UNMUTE VOLUME
        elif totalFingers == 5:
            volume.SetMute(0, None)
            last_action = "UNMUTED"

        # ✌️ PEACE SIGN -> PLAY / PAUSE MEDIA (YouTube, Spotify, etc.)
        elif fingers == [0, 1, 1, 0, 0]:
            counter += 1
            if counter > 15:  # Debounce limit: checks frames to prevent spam clicking
                pyautogui.press('playpause')
                last_action = "PLAY / PAUSE TRACK"
                counter = 0

        # 🤏 PINCH (Thumb + Index only) -> VOLUME VARIABLE SLIDER
        elif fingers == [1, 1, 0, 0, 0] or fingers == [0, 1, 0, 0, 0]:
            x1, y1 = lmList[4][1], lmList[4][2]   
            x2, y2 = lmList[8][1], lmList[8][2]   
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            cv2.circle(img, (x1, y1), 10, (255, 0, 0), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 0, 0), cv2.FILLED)
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 3)

            length = math.hypot(x2 - x1, y2 - y1)

            # Map length between fingers to volume limits
            vol = np.interp(length, [20, 180], [minVol, maxVol])
            volBar = np.interp(length, [20, 180], [400, 150])
            volPer = np.interp(length, [20, 180], [0, 100])

            volume.SetMasterVolumeLevel(vol, None)
            last_action = f"Volume Slider: {int(volPer)}%"

    # Reset frame buffer when changing gesture profiles
    if 'totalFingers' in locals() and fingers != [0, 1, 1, 0, 0]:
        counter = 10 

    # =======================================================
    # 5. USER INTERFACE GRAPHICS (HUD)
    # =======================================================
    # Text Banner
    cv2.rectangle(img, (30, 20), (450, 80), (0, 0, 0), cv2.FILLED)
    cv2.putText(img, f"System Action: {last_action}", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Volume Level Graphic Bar
    cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 2)
    cv2.rectangle(img, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)
    cv2.putText(img, f'{int(volPer)}%', (45, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Smart Media Controller Feed", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()