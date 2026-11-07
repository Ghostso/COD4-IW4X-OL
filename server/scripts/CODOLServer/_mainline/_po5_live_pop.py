# -*- coding: utf-8 -*-
"""
_po5_live_pop.py - live poller for the in-game "[100] cannot connect to lobby" panel.

Runtime point of this tool: the panel is NOT a Win32 dialog, it is rendered by
the game's own UI.  So the only reliable detector is pixel-level: every tick we
grab the desktop with BitBlt (user-mode, no elevation needed) and look for the
panel's signature = a bright cyan/blue 2px border box on a very dark screen,
whose interior contains bright text pixels.

It records, for every tick:
    t, game_pid, game_alive, window_titles, panel_score, panel_bbox, saved_png

Nothing is written into the game process, nothing is patched, no network or
firewall change.  Pure read-only observation.

Usage:
    python -X utf8 CODOLServer\\_mainline\\_po5_live_pop.py --out DIR --seconds 150
    python -X utf8 CODOLServer\\_mainline\\_po5_live_pop.py --out DIR --seconds 150 --pid 1234
    python -X utf8 CODOLServer\\_mainline\\_po5_live_pop.py --out DIR --seconds 150 --attach
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import time

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
k32 = ctypes.windll.kernel32

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class RECT(ctypes.Structure):
    _fields_ = [('L', ctypes.c_long), ('T', ctypes.c_long),
                ('R', ctypes.c_long), ('B', ctypes.c_long)]


class BMI(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', ctypes.c_long),
                ('biHeight', ctypes.c_long), ('biPlanes', wt.WORD),
                ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wt.DWORD),
                ('biClrImportant', wt.DWORD)]


class Grabber(object):
    """Reusable desktop grabber: allocates the DC/bitmap once, then only BitBlt."""

    def __init__(self):
        self.w = u32.GetSystemMetrics(0)
        self.h = u32.GetSystemMetrics(1)
        self.screen = u32.GetDC(0)
        self.mem = g32.CreateCompatibleDC(self.screen)
        self.bmp = g32.CreateCompatibleBitmap(self.screen, self.w, self.h)
        g32.SelectObject(self.mem, self.bmp)
        self.bi = BMI()
        self.bi.biSize = ctypes.sizeof(BMI)
        self.bi.biWidth = self.w
        self.bi.biHeight = -self.h
        self.bi.biPlanes = 1
        self.bi.biBitCount = 32
        self.bufsz = self.w * self.h * 4
        self.buf = ctypes.create_string_buffer(self.bufsz)
        self.px = None

    def grab(self):
        ok = g32.BitBlt(self.mem, 0, 0, self.w, self.h, self.screen, 0, 0, SRCCOPY)
        if not ok:
            return None
        got = g32.GetDIBits(self.mem, self.bmp, 0, self.h, self.buf,
                            ctypes.byref(self.bi), DIB_RGB_COLORS)
        if not got:
            return None
        self.px = self.buf.raw
        return self.px

    def save_bmp(self, path):
        """Write the current buffer as a top-down 32bpp BMP (roughly 1/4 size of raw)."""
        hdr = (b'BM' + (self.bufsz + 54).to_bytes(4, 'little') + b'\x00\x00\x00\x00' +
               (54).to_bytes(4, 'little') + (40).to_bytes(4, 'little') +
               self.w.to_bytes(4, 'little') + self.h.to_bytes(4, 'little') +
               (1).to_bytes(2, 'little') + (32).to_bytes(2, 'little') +
               b'\x00' * 24)
        with open(path, 'wb') as fh:
            fh.write(hdr)
            fh.write(self.px)

    def close(self):
        g32.DeleteObject(self.bmp)
        g32.DeleteDC(self.mem)
        u32.ReleaseDC(0, self.screen)


def enum_windows_for(pid=None):
    """List visible top-level windows; optionally only those owned by pid."""
    out = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(hwnd, _lp):
        if not u32.IsWindowVisible(hwnd):
            return True
        wpid = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if pid and wpid.value != pid:
            return True
        cn = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cn, 256)
        tl = ctypes.create_unicode_buffer(512)
        u32.GetWindowTextW(hwnd, tl, 512)
        if cn.value or tl.value:
            out.append({'hwnd': hex(hwnd), 'pid': wpid.value,
                        'class': cn.value, 'title': tl.value})
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return out


def find_game_pid():
    """PID of codoMP_client_shipRetail.exe by scanning our own window list."""
    for w in enum_windows_for(None):
        if w['class'] in ('CODO', 'CoD Splash Screen'):
            return w['pid']
    # fall back to the process name so a Win32 error box also counts
    try:
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq codoMP_client_shipRetail.exe',
             '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, timeout=8).stdout or ''
        for line in out.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2 and parts[0].lower().startswith('codomp'):
                return int(parts[1])
    except Exception:
        pass
    return None


BRINGFRONT = None


def bring_to_front(pid):
    """Force the game's main window to the foreground so BitBlt sees it.

    A DirectX window that sits behind another window is NOT part of the desktop
    bitmap, so a plain BitBlt returns the occluding window instead.  The known
    working way to steal the foreground (bypassing the OS foreground lock) is
    AttachThreadInput + BringWindowToTop + SetForegroundWindow, which is what
    run_codol_001\\observer\\BringFront.exe already implements.
    """
    global BRINGFRONT
    if BRINGFRONT is None:
        BRINGFRONT = os.path.join(
            r'D:\BaiduNetdiskDownload\使命召唤OL', 'run_codol_001', 'observer',
            'BringFront.exe')
    if not pid or not os.path.isfile(BRINGFRONT):
        return None
    try:
        p = subprocess.run([BRINGFRONT, str(pid)], capture_output=True,
                           text=True, timeout=8)
        out = (p.stdout or '').strip()
        return out or None
    except Exception as exc:
        return 'ERR:%s' % exc


def game_hwnds(pid):
    """Top-level handles of the game, largest first (the CODO render window)."""
    u32_ = ctypes.windll.user32
    out = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(hwnd, _lp):
        if not u32_.IsWindowVisible(hwnd):
            return True
        wpid = wt.DWORD()
        u32_.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value != pid:
            return True
        r = RECT()
        u32_.GetWindowRect(hwnd, ctypes.byref(r))
        area = max(0, r.R - r.L) * max(0, r.B - r.T)
        cn = ctypes.create_unicode_buffer(256)
        u32_.GetClassNameW(hwnd, cn, 256)
        out.append((area, hwnd, cn.value, r))
        return True

    u32_.EnumWindows(EnumProc(cb), 0)
    out.sort(reverse=True)
    return out


def read_dialog_text(pid):
    """Read the text of every Win32 dialog the game owns, children included.

    This is the literal "watch the popup" channel: a #32770 box can be read
    without touching the game's memory at all, so it works even while ACE
    blocks OpenProcess, and it gives us the exact message string and the exact
    tick it appeared.
    """
    u32_ = ctypes.windll.user32
    boxes = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    ChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def child_cb(hwnd, _lp):
        cn = ctypes.create_unicode_buffer(64)
        u32_.GetClassNameW(hwnd, cn, 64)
        tl = ctypes.create_unicode_buffer(1024)
        u32_.GetWindowTextW(hwnd, tl, 1024)
        vis = bool(u32_.IsWindowVisible(hwnd))
        rid = u32_.GetDlgCtrlID(hwnd)
        boxes[-1]['children'].append(
            {'class': cn.value, 'text': tl.value, 'visible': vis, 'id': rid})
        return True

    def top_cb(hwnd, _lp):
        wpid = wt.DWORD()
        u32_.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value != pid:
            return True
        cn = ctypes.create_unicode_buffer(64)
        u32_.GetClassNameW(hwnd, cn, 64)
        if cn.value not in ('#32770', 'iipsinit'):
            return True
        tl = ctypes.create_unicode_buffer(1024)
        u32_.GetWindowTextW(hwnd, tl, 1024)
        boxes.append({'hwnd': hex(hwnd), 'class': cn.value,
                      'title': tl.value, 'children': []})
        u32_.EnumChildWindows(hwnd, ChildProc(child_cb), 0)
        return True

    u32_.EnumWindows(EnumProc(top_cb), 0)
    return boxes


def scan_panel(px, w, h, step=2):
    """Find the [100] panel: a saturated cyan 1-2px border box on a dark screen.

    Strategy: a pixel counts as 'border' when blue is high, green is moderately
    high, red is low  ->  that is the cyan/steel-blue frame of the CODOL popup.
    We then look for the densest horizontal run of such pixels, which is the
    panel's top edge, and report its bbox + how many border pixels we saw.
    """
    R = 0
    G = 1
    B = 2
    rows = {}
    total = 0
    for y in range(0, h, step):
        base = y * w * 4
        run = 0
        best_run = 0
        best_x = 0
        cur_x = 0
        for x in range(0, w, step):
            o = base + x * 4
            b = px[o + B]
            g = px[o + G]
            r = px[o + R]
            # cyan-ish frame: strong blue, decent green, weak red
            if b > 120 and g > 90 and r < b - 30 and g < b + 20:
                total += 1
                if run == 0:
                    cur_x = x
                run += 1
                if run > best_run:
                    best_run = run
                    best_x = cur_x
            else:
                run = 0
        if best_run >= 40:
            rows[y] = (best_x, best_run)
    if not rows:
        return {'score': 0, 'bbox': None}
    ys = sorted(rows)
    y0, y1 = ys[0], ys[-1]
    x0 = min(v[0] for v in rows.values())
    x1 = max(v[0] + v[1] for v in rows.values())
    return {'score': total,
            'bbox': [x0, y0, x1, y1],
            'rows': len(rows),
            'panel_w': x1 - x0, 'panel_h': y1 - y0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=150.0)
    ap.add_argument('--step', type=float, default=2.0)
    ap.add_argument('--pid', type=int, default=0)
    ap.add_argument('--attach', action='store_true',
                    help='attach to a running game instead of waiting for it')
    ap.add_argument('--save-on-panel', type=int, default=1,
                    help='save a PNG/BMP on the first panel hit and when it clears')
    ap.add_argument('--save-every', type=float, default=0.0,
                    help='also snapshot every N seconds (0 = off)')
    ap.add_argument('--no-front', action='store_true',
                    help='do not steal the foreground (debug only; will see occluders)')
    args = ap.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(
        r'D:\BaiduNetdiskDownload\使命召唤OL', args.out)
    os.makedirs(out, exist_ok=True)
    jsonl = os.path.join(out, 'live_pop.jsonl')
    shots = os.path.join(out, 'shots')
    os.makedirs(shots, exist_ok=True)

    g = Grabber()
    log = open(jsonl, 'a', encoding='utf-8')
    t0 = time.time()
    pid = args.pid or 0
    seen_pid = False
    panel_prev = False
    dialog_prev = None
    first_panel_t = None
    clear_t = None
    n = 0
    last_shot = 0.0

    print('out=%s  seconds=%.0f step=%.1f attach=%s' % (out, args.seconds, args.step, args.attach))
    print('screen=%dx%d' % (g.w, g.h))

    while True:
        el = time.time() - t0
        if el > args.seconds:
            break
        px = g.grab()
        rec = {'t': round(el, 3)}

        if not pid:
            pid = find_game_pid() or 0
        rec['game_pid'] = pid
        if pid:
            if not args.no_front:
                rec['front'] = bring_to_front(pid)
                hw = game_hwnds(pid)
                rec['game_hwnds'] = [
                    {'area': a, 'hwnd': hex(h), 'class': c,
                     'rect': [r.L, r.T, r.R, r.B]} for a, h, c, r in hw]
            h = k32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
            alive = bool(h)
            if h:
                k32.CloseHandle(h)
                code = wt.DWORD()
                h2 = k32.OpenProcess(0x1000, False, pid)
                if h2:
                    k32.GetExitCodeProcess(h2, ctypes.byref(code))
                    rec['exit_code'] = code.value
                    k32.CloseHandle(h2)
            rec['alive'] = alive
            if alive:
                seen_pid = True
            dlg = read_dialog_text(pid)
            if dlg:
                rec['dialogs'] = dlg
                txt = ' | '.join(
                    '%s:%r' % (b['class'], b['title']) for b in dlg)
                kids = []
                for b in dlg:
                    for c in b.get('children', []):
                        if c.get('text'):
                            kids.append(c['text'])
                rec['dialog_text'] = kids
                if kids:
                    txt += ' :: ' + ' / '.join(kids)
                if rec.get('dialog_text') and rec['dialog_text'] != dialog_prev:
                    rec['event'] = 'DIALOG_TEXT'
                    if args.save_on_panel:
                        p = os.path.join(shots, 'dlg_%05.2fs.bmp' % el)
                        g.save_bmp(p)
                        rec['shot'] = p
                    dialog_prev = rec['dialog_text']
                elif not rec.get('dialog_text'):
                    dialog_prev = None
        else:
            rec['alive'] = False

        if px is not None:
            sc = scan_panel(px, g.w, g.h)
            rec['panel_score'] = sc['score']
            rec['panel_bbox'] = sc['bbox']
            rec['panel_h'] = sc.get('panel_h')
            rec['panel_w'] = sc.get('panel_w')
            hit = bool(sc['bbox']) and sc['score'] > 3000
            rec['panel'] = hit
            if hit and not panel_prev:
                rec['event'] = 'PANEL_APPEAR'
                first_panel_t = el
                if args.save_on_panel:
                    p = os.path.join(shots, 'panel_%05.2fs.bmp' % el)
                    g.save_bmp(p)
                    rec['shot'] = p
            elif panel_prev and not hit:
                rec['event'] = 'PANEL_CLEAR'
                clear_t = el
                if args.save_on_panel:
                    p = os.path.join(shots, 'clear_%05.2fs.bmp' % el)
                    g.save_bmp(p)
                    rec['shot'] = p
            panel_prev = hit
        else:
            rec['panel'] = None

        wins = enum_windows_for(rec.get('game_pid') or None)
        game_wins = [w for w in wins if w['class'] in
                     ('CODO', 'CoD Splash Screen', '#32770')]
        rec['game_windows'] = game_wins
        rec['window_count'] = len(wins)

        if args.save_every and el - last_shot >= args.save_every:
            p = os.path.join(shots, 'tick_%05.2fs.bmp' % el)
            g.save_bmp(p)
            last_shot = el

        log.write(json.dumps(rec, ensure_ascii=False) + '\n')
        log.flush()
        n += 1
        if rec.get('event') or n % 10 == 0:
            print('t=%6.2f pid=%s alive=%s panel=%s score=%s %s'
                  % (el, pid, rec.get('alive'), rec.get('panel'),
                     rec.get('panel_score'), rec.get('event', '')))
        time.sleep(max(0.0, args.step))

    summary = {'ticks': n, 'out': out, 'jsonl': jsonl,
               'first_panel_t': first_panel_t, 'panel_clear_t': clear_t,
               'game_pid_seen': seen_pid}
    open(os.path.join(out, 'summary.json'), 'w', encoding='utf-8').write(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    g.close()
    log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
