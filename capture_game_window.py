import ctypes
import time
from PIL import ImageGrab

user32 = ctypes.windll.user32

# Find window with title "使命召唤online"
hwnd = user32.FindWindowW(None, "使命召唤online")
print("HWND for 使命召唤online:", hwnd)

if hwnd:
    user32.ShowWindow(hwnd, 9) # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

# Grab screenshot
im = ImageGrab.grab()
im.save(r"D:\BaiduNetdiskDownload\使命召唤OL\game_screen.png")
print("Screenshot captured successfully!")
