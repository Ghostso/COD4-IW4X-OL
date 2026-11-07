# -*- coding: utf-8 -*-
"""Enumerate ALL windows of game processes, including child dialogs."""
import ctypes, ctypes.wintypes as w
u32 = ctypes.windll.user32
EnumWindows = u32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

def get_text(h):
    n = u32.GetWindowTextLengthW(h)
    if n == 0: return ""
    buf = ctypes.create_unicode_buffer(n+1)
    u32.GetWindowTextW(h, buf, n+1)
    return buf.value

def get_class(h):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, buf, 256)
    return buf.value

def pid_of(h):
    p = w.DWORD()
    u32.GetWindowThreadProcessId(h, ctypes.byref(p))
    return p.value

rows = []
def cb(h, l):
    if not u32.IsWindowVisible(h):
        return True
    rows.append((pid_of(h), get_class(h), get_text(h)))
    return True

EnumWindows(EnumWindowsProc(cb), 0)

# which pids are game-related
import subprocess
r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process | Where-Object {$_.ProcessName -match 'codo|IIPS|ACE|TP3|TQM|VSD|Ten'} | ForEach-Object { '{0}|{1}' -f $_.Id,$_.ProcessName }"],
  capture_output=True)
gp = {}
for line in r.stdout.decode("utf-8","replace").splitlines():
    if "|" in line:
        a,b = line.split("|",1); gp[int(a)] = b

print("=== game processes ===")
for k,v in sorted(gp.items()): print("  pid=%-8d %s" % (k,v))
print()
print("=== ALL visible windows belong to game pids ===")
found = False
for pid, cls, txt in rows:
    if pid in gp:
        found = True
        print("  pid=%-8d class=%-28s text=%r" % (pid, cls, txt))
if not found:
    print("  (none)")
print()
print("=== any #32770 dialogs system-wide (top-level) ===")
hit = [r for r in rows if r[1] == "#32770"]
for pid, cls, txt in hit:
    print("  pid=%-8d class=%s text=%r" % (pid, cls, txt))
if not hit: print("  (none)")
