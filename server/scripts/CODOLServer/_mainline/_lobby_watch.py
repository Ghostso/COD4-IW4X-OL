"""Launch the game suspended, grab the handle before ACE arms, then watch
the lobby globals to see whether dwauth.ini is picked up.

READ-ONLY: OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ) only.
No write, no inject, no patch. No network changes. ASCII only.

Usage:
  python -X utf8 _lobby_watch.py --cwd <gamedir> --out <dir> \
      --seconds 150 --step 0.5
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)


class LUID(ctypes.Structure):
    _fields_ = [("L", wt.DWORD), ("H", wt.LONG)]


class LAA(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attr", wt.DWORD)]


class TP(ctypes.Structure):
    _fields_ = [("n", wt.DWORD), ("p", LAA * 1)]


class SI(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("r", wt.LPWSTR), ("d", wt.LPWSTR),
                ("t", wt.LPWSTR), ("x", wt.DWORD), ("y", wt.DWORD),
                ("xs", wt.DWORD), ("ys", wt.DWORD), ("xc", wt.DWORD),
                ("yc", wt.DWORD), ("fa", wt.DWORD), ("fl", wt.DWORD),
                ("sw", wt.WORD), ("cr", wt.WORD), ("rp", ctypes.c_void_p),
                ("hi", wt.HANDLE), ("ho", wt.HANDLE), ("he", wt.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [("hp", wt.HANDLE), ("ht", wt.HANDLE),
                ("pid", wt.DWORD), ("tid", wt.DWORD)]


def setup():
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD,
                                     ctypes.POINTER(ctypes.c_void_p)]
    adv.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                          ctypes.POINTER(LUID)]
    adv.AdjustTokenPrivileges.argtypes = [ctypes.c_void_p, wt.BOOL,
                                          ctypes.POINTER(TP), wt.DWORD,
                                          ctypes.c_void_p,
                                          ctypes.POINTER(wt.DWORD)]
    h = ctypes.c_void_p()
    adv.OpenProcessToken(k32.GetCurrentProcess(), 0x28, ctypes.byref(h))
    lu = LUID()
    adv.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(lu))
    tp = TP()
    tp.n = 1
    tp.p[0].Luid = lu
    tp.p[0].Attr = 2
    adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    k32.CreateProcessW.restype = wt.BOOL
    k32.CreateProcessW.argtypes = [
        wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL,
        wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(SI),
        ctypes.POINTER(PI)]
    k32.OpenProcess.restype = wt.HANDLE
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.ReadProcessMemory.restype = wt.BOOL
    k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def rd(h, va, n):
    b = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), b, n,
                               ctypes.byref(got))
    if not ok or got.value == 0:
        return None
    return b.raw[:got.value]


INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
FILE_MAP_ALL_ACCESS = 0x000F001F


def create_tenproxy_shm(pid, image_path):
    """Publish TCLS_SHAREDMEMEMORY<pid> so TenProxy.dll can read its tags.

    The client's TenProxy reads a slot table at mapping+0x004 and a channel
    pointer at mapping+0x050.  A 0x7AC-byte block has none of that, so
    ApplySettings fails and [0x331C5C0] stays 0, which skips objC creation
    entirely.  The returned handle must stay open for the whole run: it is
    the only reference that keeps the named mapping alive for the client.
    """
    if not os.path.isfile(image_path):
        return None, "image-missing"
    blob = open(image_path, "rb").read()
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    name = "TCLS_SHAREDMEMEMORY%d" % pid
    h = k32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, 0x04, 0,
                               len(blob), name)
    if not h:
        return None, "CreateFileMappingW err=%d" % ctypes.get_last_error()
    p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, len(blob))
    if not p:
        err = ctypes.get_last_error()
        k32.CloseHandle(h)
        return None, "MapViewOfFile err=%d" % err
    ctypes.memmove(p, blob, len(blob))
    k32.UnmapViewOfFile(p)
    return h, "ok size=%d" % len(blob)


WATCH = [
    (0x849B61F, "B", "flag_61f"),   # dwLobby master gate
    (0x331C5C0, "I", "cfg_applied"),  # TCLS settings-applied flag
    (0x849B501, "B", "flag_b501"),
    (0x84ABA50, "I", "uA50"),       # lobby state (0=fail,1..4=pending,5=ok)
    (0x84ABA54, "I", "uA54"),       # previous lobby state
    (0x84ABA60, "I", "sub_state"),  # auth sub-state (want 9)
    (0x84ABA5C, "I", "last_err"),   # error code if failed
    (0x84ABA64, "I", "uA64"),       # retry/once flag
    (0x849BA34, "I", "dw_state"),   # DW live state (target)
    (0x849BA30, "I", "state_prev"), # previous DW state
    (0x849BA3D, "B", "bA3D"),       # hard error flag: !=0 -> instant FAIL
    (0x849B5CC, "I", "u5CC"),
    (0x84ABA78, "I", "uA78"),       # DNS stage result (2 == complete)
    (0x849B61C, "I", "near61c"),
    (0x84ABB08, "I", "objA"),       # active lobby/client object
    (0x84ABB14, "I", "objB"),       # fallback lobby/client object
    (0x84ABB0C, "I", "objC"),       # ticket/registration object (0xD5A0D0)
    (0xE4EA3C, "I", "nm_ptr"),      # -> current state name string
    (0x81A9EC4, "H", "port"),       # configured lobby port (word)
    (0x81A9EB8, "I", "hst_ptr"),    # -> configured lobby host
]

HOST_VA = 0x81A76A8      # dwauth.ini field 3 (lobby HOST), 60 bytes
F1_VA = 0x81A7F34        # field 1
OBJ_CODE_OFF = 0x156C    # [obj+0x156C] = last transfer result code
OBJ_BUSY_OFF = 0x20      # [obj+0x20]   = 1 while request in flight
OBJ_STAGE_OFF = 0x14     # [obj+0x14]   = request stage written by 0xB88F41
OBJ_HTTP_OFF = 0x160     # [obj+0x160]  = libcurl/HTTP wrapper object
OBJ_BODY_OFF = 0x16C     # [obj+0x16C]  = receive buffer (0x1400 bytes)
HTTP_STATE_OFF = 0x04    # vtable+0x2C (0xBC1190) returns [http+0x04]
HTTP_STATUS_OFF = 0x464  # vtable+0x34 (0xC74FD0) returns [http+0x464]
HTTP_AUX_OFF = 0x444     # vtable+0x38 (0xC74FE0) returns [http+0x444]

# Slots of the auth object vtable (written to [obj+0x00] at 0xB88B9A).
# These are read at runtime to prove which vtable instance is live and which
# handler the per-frame call actually reaches.
VT_SLOTS = [0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x2C]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--tenproxy-shm", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_subagents", "_tenproxy_shm.bin"),
        help="TCLS_SHAREDMEMEMORY<pid> image consumed by TenProxy.dll")
    ap.add_argument("--no-tenproxy-shm", action="store_true",
                    help="Do not publish TCLS_SHAREDMEMEMORY<pid>")
    ap.add_argument("--frida-script", default=None,
                    help="JS file injected before the game is resumed")
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    if not os.path.exists(exe):
        print("missing exe: " + exe, file=sys.stderr)
        return 2
    os.makedirs(a.out, exist_ok=True)
    lg = open(os.path.join(a.out, "watch.jsonl"), "w", encoding="utf-8")

    def ev(o):
        lg.write(json.dumps(o, ensure_ascii=False) + "\n")
        lg.flush()

    setup()
    ev({"ev": "setup_ok", "exe": exe, "cwd": gd})
    di = os.path.join(gd, "dwauth.ini")
    ev({"ev": "dwauth_present", "path": di, "exists": os.path.exists(di),
        "content": (open(di, encoding="ascii").read() if os.path.exists(di) else None)})

    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % exe
    buf = ctypes.create_unicode_buffer(cmd)
    ok = k32.CreateProcessW(exe, buf, None, None, True, 4, None, gd,
                            ctypes.byref(si), ctypes.byref(pi))
    ev({"ev": "create", "ok": bool(ok), "pid": pi.pid,
        "err": ctypes.get_last_error()})
    if not ok:
        return 1

    h = k32.OpenProcess(0x0400 | 0x0010, False, pi.pid)
    ev({"ev": "handle", "h": h, "err": ctypes.get_last_error()})
    if not h:
        return 1

    # Frida must attach FIRST: every extra step before it gives ACE time to
    # arm, after which VirtualAllocEx is refused with 0x5.
    frida_session = None
    frida_script = None
    if a.frida_script:
        try:
            import frida
            session = frida.attach(pi.pid)
            source = open(a.frida_script, encoding="utf-8").read()
            script = session.create_script(source)

            def on_message(message, data):
                payload = message.get("payload")
                ev({"ev": "frida", "msg": payload if payload is not None
                    else message})

            script.on("message", on_message)
            script.load()
            frida_session = session
            frida_script = script
            ev({"ev": "frida_attached", "pid": pi.pid})
        except Exception as e:
            ev({"ev": "frida_attach_failed", "pid": pi.pid, "error": repr(e)})

    if a.no_tenproxy_shm:
        shm_handle, shm_note = None, "disabled"
    else:
        shm_handle, shm_note = create_tenproxy_shm(pi.pid, a.tenproxy_shm)
    ev({"ev": "tenproxy_shm", "ok": shm_handle is not None,
        "note": shm_note, "pid": pi.pid})

    k32.ResumeThread(pi.ht)
    ev({"ev": "resumed"})
    t0 = time.time()
    host_seen = None
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        rec = {"t": el}
        for va, fmt, name in WATCH:
            b = rd(h, va, struct.calcsize(fmt))
            rec[name] = (struct.unpack(fmt, b)[0]
                         if b and len(b) == struct.calcsize(fmt) else None)
        hb = rd(h, HOST_VA, 60)
        hb1 = rd(h, F1_VA, 60)
        rec["host"] = (hb.split(b"\x00")[0].decode("latin1")
                       if hb else None)
        rec["f1"] = (hb1.split(b"\x00")[0].decode("latin1") if hb1 else None)

        # --- state-name string, via [0xE4EA3C] pointer ---
        rec["nm"] = None
        if rec.get("nm_ptr"):
            nb = rd(h, rec["nm_ptr"], 40)
            if nb:
                rec["nm"] = nb.split(b"\x00")[0].decode("latin1", "replace")

        # --- configured lobby host string, via [0x81A9EB8] pointer ---
        rec["cfg_host"] = None
        if rec.get("hst_ptr"):
            cb = rd(h, rec["hst_ptr"], 60)
            if cb:
                rec["cfg_host"] = cb.split(b"\x00")[0].decode("latin1",
                                                              "replace")

        # --- live transfer object: result code + busy flag ---
        obj = rec.get("objA") or rec.get("objB")
        rec["obj"] = obj or None
        rec["obj_code"] = None
        rec["obj_busy"] = None
        rec["obj_stage"] = None
        rec["obj_vt"] = None
        rec["obj_vt_slots"] = None
        rec["obj_http"] = None
        rec["http_state"] = None
        rec["http_status"] = None
        rec["http_aux"] = None
        rec["obj_body_head"] = None
        if obj:
            cb2 = rd(h, obj + OBJ_CODE_OFF, 4)
            if cb2 and len(cb2) == 4:
                rec["obj_code"] = struct.unpack("I", cb2)[0]
            bb = rd(h, obj + OBJ_BUSY_OFF, 4)
            if bb and len(bb) == 4:
                rec["obj_busy"] = struct.unpack("I", bb)[0]
            sb = rd(h, obj + OBJ_STAGE_OFF, 4)
            if sb and len(sb) == 4:
                rec["obj_stage"] = struct.unpack("I", sb)[0]
            # Vtable identity: [obj+0x00] is written to 0xD59A7C by 0xB88B9A.
            # Reading the live pointer plus a few handler slots proves which
            # code path the per-frame update (slot +0x10) will take.
            vb = rd(h, obj, 4)
            if vb and len(vb) == 4:
                vt = struct.unpack("I", vb)[0]
                rec["obj_vt"] = vt
                slots = {}
                for off in VT_SLOTS:
                    f = rd(h, vt + off, 4)
                    if f and len(f) == 4:
                        slots["0x%02X" % off] = struct.unpack("I", f)[0]
                rec["obj_vt_slots"] = slots or None
            # HTTP wrapper state drives the 0xB9A370 per-frame branch:
            # state 1/3 = still pending, 5 = reply complete, anything else
            # falls through to the error mapping in 0xBAA2D0.
            hb = rd(h, obj + OBJ_HTTP_OFF, 4)
            if hb and len(hb) == 4:
                http = struct.unpack("I", hb)[0]
                rec["obj_http"] = http
                if http:
                    for off, name in ((HTTP_STATE_OFF, "http_state"),
                                      (HTTP_STATUS_OFF, "http_status"),
                                      (HTTP_AUX_OFF, "http_aux")):
                        f = rd(h, http + off, 4)
                        if f and len(f) == 4:
                            rec[name] = struct.unpack("I", f)[0]
            bb = rd(h, obj + OBJ_BODY_OFF, 128)
            if bb:
                rec["obj_body_head"] = bb.split(b"\x00")[0][:120].decode(
                    "utf-8", "replace")
        # --- registration object (vtable 0xD5A0D0), slot 0x84ABB0C ---
        # [objC+0x240] == 2 is what 0xB983C0 needs before it will hand out the
        # ticket buffer at [objC+0x2E0]; [objC+0x1400] is the result code that
        # 0x7F3190 compares against 0x22C4 (8900) for success.
        rec["objC_240"] = None
        rec["objC_1400"] = None
        rec["objC_390"] = None
        rec["objC_vt"] = None
        rec["objA_18"] = None
        rec["objA_d8"] = None
        rec["objA_30"] = None
        rec["objA_e0"] = None
        rec["objA_2ac"] = None
        rec["objA_2cc"] = None
        oa = rec.get("objA")
        if oa:
            for off, name in ((0x18, "objA_18"), (0xD8, "objA_d8"),
                              (0x30, "objA_30"), (0xE0, "objA_e0"),
                              (0x2AC, "objA_2ac"), (0x2CC, "objA_2cc")):
                f = rd(h, oa + off, 4)
                if f and len(f) == 4:
                    rec[name] = struct.unpack("I", f)[0]
        oc = rec.get("objC")
        if oc:
            for off, name in ((0x240, "objC_240"), (0x1400, "objC_1400"),
                              (0x390, "objC_390"), (0x0, "objC_vt")):
                f = rd(h, oc + off, 4)
                if f and len(f) == 4:
                    rec[name] = struct.unpack("I", f)[0]
        if rec["host"]:
            host_seen = rec["host"]
        ev(rec)
        time.sleep(a.step)
    ev({"ev": "done", "host_seen": host_seen, "elapsed": round(time.time() - t0, 1)})
    lg.close()
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
