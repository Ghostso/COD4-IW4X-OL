import ctypes, time
from PIL import ImageGrab
import win32gui, win32process, psutil

# Find process
pid = None
for p in psutil.process_iter(['pid', 'name']):
    if 'codoMP' in p.info['name']:
        pid = p.info['pid']
        break

print("codoMP PID:", pid)

hwnds = []
def enum_win(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
        if win_pid == pid:
            hwnds.append(hwnd)
    return True

if pid:
    win32gui.EnumWindows(enum_win, None)
    print("Found HWNDs:", hwnds)
    if hwnds:
        h = hwnds[0]
        title = win32gui.GetWindowText(h)
        print("Window Title:", title)
        ctypes.windll.user32.ShowWindow(h, 9)
        ctypes.windll.user32.SetForegroundWindow(h)
        time.sleep(1.0)

im = ImageGrab.grab()
im.save(r"D:\BaiduNetdiskDownload\使命召唤OL\game_screen.png")
print("Saved to game_screen.png")
