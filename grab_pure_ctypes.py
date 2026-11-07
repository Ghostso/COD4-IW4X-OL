import ctypes, time
from PIL import ImageGrab

user32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

found_hwnd = None

def enum_cb(hwnd, lparam):
    global found_hwnd
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        if "使命召唤" in title or "codo" in title.lower():
            print(f"Found game window: HWND=0x{hwnd:X}, Title={title}")
            found_hwnd = hwnd
            return False
    return True

user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

if found_hwnd:
    user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
    user32.SetForegroundWindow(found_hwnd)
    time.sleep(1.0)
    im = ImageGrab.grab()
    im.save(r"D:\BaiduNetdiskDownload\使命召唤OL\game_screen.png")
    print("Screenshot saved to game_screen.png!")
else:
    print("Window not found by title.")
