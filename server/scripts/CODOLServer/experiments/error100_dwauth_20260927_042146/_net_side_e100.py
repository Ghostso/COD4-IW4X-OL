"""Network side observer for the error-100 experiment.

Runs two independent, observation-only collectors for one target PID:

  1. netstat polling (no injection): every TCP endpoint the PID owns, plus
     every UDP endpoint, so "did a lobby socket appear" is answered from the
     OS socket table rather than from any in-process assumption.
  2. optional Frida hook of ws2_32 exports, enabled only with --frida, that
     logs getaddrinfo / gethostbyname / connect / WSAConnect / send / sendto /
     recv / recvfrom with addresses and ports. This does not modify return
     values or arguments.

Nothing here writes to the target process or changes system network state.

Usage:
  python -X utf8 _net_side_e100.py --pid <pid> --seconds 150 --out <dir>
  python -X utf8 _net_side_e100.py --pid <pid> --seconds 150 --out <dir> --frida
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _toolhelp_snapshot_pids():
    """Return {pid: name} using CreateToolhelp32Snapshot (no netstat needed)."""
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]

    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k32.Process32First.argtypes = [wt.HANDLE,
                                   ctypes.POINTER(PROCESSENTRY32)]
    k32.Process32Next.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)]

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = {}
    if not snap or snap == wt.HANDLE(-1).value:
        return out
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(pe)
    ok = k32.Process32First(snap, ctypes.byref(pe))
    while ok:
        out[int(pe.th32ProcessID)] = pe.szExeFile.decode("latin1", "replace")
        ok = k32.Process32Next(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return out


def netstat_rows():
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True,
                           timeout=20)
    except Exception:
        return []
    txt = (r.stdout or b"").decode("gbk", "replace")
    rows = []
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        if parts[0] not in ("TCP", "UDP"):
            continue
        rows.append(parts)
    return rows


FRIDA_JS = r"""
'use strict';
function s(p){ try { return p.readAnsiString(); } catch(e){ return null; } }
function sa(ptr, len){
  try {
    var fam = ptr.readU16();
    if (fam === 2){
      var port = (ptr.add(2).readU8() << 8) | ptr.add(3).readU8();
      var ip = ptr.add(4).readU8()+'.'+ptr.add(5).readU8()+'.'+
               ptr.add(6).readU8()+'.'+ptr.add(7).readU8();
      return {family:fam, ip:ip, port:port};
    }
    return {family:fam};
  } catch(e){ return {error:String(e)}; }
}
function hook(name, cb){
  var p = Module.findExportByName('ws2_32.dll', name);
  if (!p){ send({type:'api_missing', api:name}); return; }
  Interceptor.attach(p, cb);
  send({type:'api_hooked', api:name, address:p.toString()});
}
hook('getaddrinfo', { onEnter:function(a){ send({type:'getaddrinfo', host:s(a[0])}); } });
hook('gethostbyname', { onEnter:function(a){ send({type:'gethostbyname', host:s(a[0])}); } });
hook('WSASocketA', { onEnter:function(a){ send({type:'WSASocketA', af:a[0].toInt32(), type:a[1].toInt32(), proto:a[2].toInt32()}); } });
hook('socket', { onEnter:function(a){ send({type:'socket', af:a[0].toInt32(), type:a[1].toInt32(), proto:a[2].toInt32()}); } });
hook('connect', {
  onEnter:function(a){ send({type:'connect', addr:sa(a[1], 16)}); },
  onLeave:function(r){ send({type:'connect_ret', ret:r.toInt32()}); }
});
hook('WSAConnect', {
  onEnter:function(a){ send({type:'WSAConnect', addr:sa(a[1], 16)}); }
});
hook('send', {
  onEnter:function(a){ send({type:'send', len:a[2].toInt32()}); },
  onLeave:function(r){ send({type:'send_ret', ret:r.toInt32()}); }
});
hook('sendto', {
  onEnter:function(a){ send({type:'sendto', len:a[2].toInt32(), to:sa(a[4], 16)}); }
});
hook('recv', {
  onEnter:function(a){ this.n = a[2].toInt32(); },
  onLeave:function(r){ send({type:'recv', req:this.n, ret:r.toInt32()}); }
});
hook('recvfrom', {
  onEnter:function(a){ this.n = a[2].toInt32(); },
  onLeave:function(r){ send({type:'recvfrom', req:this.n, ret:r.toInt32()}); }
});
send({type:'ready'});
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--frida", action="store_true")
    ap.add_argument("--follow-image", default=None,
                    help="also observe every process with this image name")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    sockf = open(os.path.join(a.out, "sockets.jsonl"), "w",
                 encoding="utf-8")
    apif = open(os.path.join(a.out, "ws2_api.jsonl"), "w", encoding="utf-8")

    def emit_sock(o):
        sockf.write(json.dumps(o, ensure_ascii=False) + "\n")
        sockf.flush()

    def emit_api(o):
        apif.write(json.dumps(o, ensure_ascii=False) + "\n")
        apif.flush()
        print(json.dumps(o, ensure_ascii=False), flush=True)

    session = None
    if a.frida:
        try:
            import frida
            session = frida.attach(a.pid)
            script = session.create_script(FRIDA_JS)

            def on_message(message, data):
                if message.get("type") == "send":
                    emit_api(message.get("payload"))
                else:
                    emit_api({"type": "frida_message",
                              "message": message})

            script.on("message", on_message)
            script.load()
            emit_api({"type": "frida_attached", "pid": a.pid})
        except Exception as exc:
            emit_api({"type": "frida_attach_failed", "error": repr(exc)})
            session = None

    t0 = time.time()
    seen = set()
    seen_procs = {}
    while time.time() - t0 < a.seconds:
        el = round(time.time() - t0, 2)
        names = _toolhelp_snapshot_pids()
        pids = set()
        if a.pid > 0:
            pids.add(a.pid)
        for pid, nm in names.items():
            if a.follow_image and nm.lower() == a.follow_image.lower():
                pids.add(pid)
                seen_procs[pid] = nm
            if nm.lower() in ("tqmcenter.exe", "iipshostapp.exe",
                              "crossproxy.exe", "tp3helper.exe"):
                pids.add(pid)
                seen_procs[pid] = nm
        for row in netstat_rows():
            proto = row[0]
            pid_s = row[-1]
            if not pid_s.isdigit() or int(pid_s) not in pids:
                continue
            key = tuple(row)
            if key in seen:
                continue
            seen.add(key)
            rec = {"t": el, "proto": proto, "pid": int(pid_s),
                   "proc": names.get(int(pid_s)), "row": row}
            emit_sock(rec)
        time.sleep(0.4)

    emit_sock({"ev": "done", "elapsed": round(time.time() - t0, 1),
               "unique_endpoints": len(seen),
               "platform_pids": seen_procs})
    sockf.close()
    apif.close()
    if session is not None:
        try:
            session.detach()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
