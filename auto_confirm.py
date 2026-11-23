"""
ROB RUN: AUTO START DUTY

Presses E every 0.5s and checks the screen.
When the green CONFIRM buttons appear, clicks the CONFIRM_BUTTON-th one and stops pressing E (F8 resumes).

F8 = pause/resume | F9 = quit
Install:  pip install mss opencv-python numpy pydirectinput
"""
import ctypes
import time

import cv2
import mss
import numpy as np
import pydirectinput

# Which CONFIRM button to click, counting from the left (1 = Patrol Officer, 2 = Sergeant I,
# 3 = Sergeant II, 4 = Lieutenant I, 5 = Captain). Change to 4 once Lieutenant is unlocked.
CONFIRM_BUTTON = 3

# ================== SETTINGS ==================
E_INTERVAL = 0.5           # seconds between each E press
KEY = "e"
EXPECTED_GREEN_COUNT = CONFIRM_BUTTON  # minimum green buttons to consider "screen changed"
SORT_BY = "x"              # "x" = left->right | "y" = top->bottom
MIN_AREA = 1500            # minimum area (px) of a button; tune with DEBUG
MAX_AREA = 200_000
WAIT_AFTER_CLICK = 2.0     # seconds to wait for the screen to close after clicking

# Green range in HSV (OpenCV: H 0-179). Adjust if your green is different.
# CONFIRM is lime green (H≈38, S≈204, V≈251); the dark-green cards are excluded by V.
GREEN_MIN = np.array([30, 150, 200])
GREEN_MAX = np.array([45, 255, 255])

# Screen region to analyze (None = whole monitor). E.g.: {"left": 600, "top": 400, "width": 800, "height": 400}
REGION = None
DEBUG = False              # True = saves debug_mask.png and prints the areas found
# ==============================================

VK_F8, VK_F9 = 0x77, 0x78
pydirectinput.PAUSE = 0.02
pydirectinput.FAILSAFE = True  # mouse in the top-left corner = abort

# Makes screenshot coordinates match mouse coordinates on scaled displays (125%, 150%...)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()


def key_pressed(vk):
    return ctypes.windll.user32.GetAsyncKeyState(vk) & 1


def find_green_buttons(sct, area):
    img = np.array(sct.grab(area))[:, :, :3]          # BGRA -> BGR
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, GREEN_MIN, GREEN_MAX)
    # close the "holes" left by the CONFIRM text inside the button
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    buttons = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        a = w * h
        if MIN_AREA <= a <= MAX_AREA and w > h:        # button is wider than tall
            buttons.append((x + w // 2 + area["left"], y + h // 2 + area["top"], a))

    if DEBUG:
        cv2.imwrite("debug_mask.png", mask)
        print("Greens found (x, y, area):", buttons)

    idx = 0 if SORT_BY == "x" else 1
    return sorted(buttons, key=lambda b: b[idx])


def main():
    print("Starting in 3s... switch to the game window.")
    print("F8 = pause/resume | F9 = quit")
    time.sleep(3)

    paused = False
    with getattr(mss, "MSS", mss.mss)() as sct:
        area = REGION or sct.monitors[1]
        while True:
            if key_pressed(VK_F9):
                print("Exiting.")
                break
            if key_pressed(VK_F8):
                paused = not paused
                print("PAUSED" if paused else "RUNNING")
            if paused:
                time.sleep(0.1)
                continue

            buttons = find_green_buttons(sct, area)
            if len(buttons) >= EXPECTED_GREEN_COUNT:
                x, y, _ = buttons[CONFIRM_BUTTON - 1]
                print(f"Screen changed! {len(buttons)} green buttons -> clicking #{CONFIRM_BUTTON} at ({x}, {y})")
                pydirectinput.moveTo(x, y)
                time.sleep(0.05)
                pydirectinput.click()
                time.sleep(WAIT_AFTER_CLICK)
                paused = True
                print("Confirmed! Stopped pressing E. F8 = restart | F9 = quit")
                continue

            pydirectinput.press(KEY)
            time.sleep(E_INTERVAL)


if __name__ == "__main__":
    main()
