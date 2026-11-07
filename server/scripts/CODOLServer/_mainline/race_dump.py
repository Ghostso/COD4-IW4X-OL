# -*- coding: utf-8 -*-
"""race_dump.py -- start the normal chain and dump the client image the moment
it appears, racing ACE's arming window.

Runs inside the elevated agent.  Two threads:
  A. launches run_all.py (normal Auth/Lobby/battle chain, client reached unpacked)
  B. polls for codoMP_client_shipRetail.exe every 5 ms; on first sight it dumps
     the full module window [0x400000, 0x400000+SizeOfImage) to <out>/race_<t>.bin

Usage: python -X utf8 race_dump.py <run_dir> [<chain_seconds>]
"""
import ctypes, ctypes.wintypes as wt, json, os, struct, subprocess, sys, threading, time

RUN = sys.argv[1]
CHAIN_SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
KIT = os.path.join(RUN, "kit")
OUT = os.path.join(RUN, "race")
os.makedirs(OUT, exist_ok=True)

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
K32_MBI = type("MBI", (ctypes.Structure,), {"_fields_": [
    ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
    ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
    ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]})

MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE = (0x02, 0x04, 0x20, 0x40, 0x80)

def find_pid(name="codoMP_client_shipRetail.exe"):
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace")
    for line in r.stdout.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if c and c[0].casefold() == name.casefold():
            try: return int(c[1].replace(",", ""))
            except (IndexError, ValueError): pass
    return None

def peek_pid(pid):
    """Return True when the image header is readable (window still open)."""
    h = k32.OpenProcess(0x0410, False, pid)
    if not h: return False, ctypes.get_last_error()
    buf = ctypes.create_string_buffer(0x1000); got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x400000), buf, 0x1000, ctypes.byref(got))
    err = ctypes.get_last_error()
    k32.CloseHandle(h)
    return bool(ok), err

def dump(pid, prefix):
    h = k32.OpenProcess(0x0410, False, pid)
    if not h: return 0, ctypes.get_last_error()
    hdr = ctypes.create_string_buffer(0x1000); got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(0x400000), hdr, 0x1000, ctypes.byref(got)):
        e = ctypes.get_last_error(); k32.CloseHandle(h); return 0, e
    hb = hdr.raw
    if hb[:2] != b"MZ": k32.CloseHandle(h); return 0, -1
    e = struct.unpack_from("<I", hb, 0x3C)[0]
    size = struct.unpack_from("<I", hb, e + 24 + 56)[0]
    blob = bytearray(size); have = 0
    addr = 0x400000; end = 0x400000 + size
    mbi = K32_MBI()
    while addr < end:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)): break
        rb = mbi.BaseAddress or 0; rs = mbi.RegionSize or 0
        if rs == 0: break
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE and not (mbi.Protect & PAGE_GUARD):
            buf = ctypes.create_string_buffer(rs); g = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(rb), buf, rs, ctypes.byref(g)) and g.value:
                off = rb - 0x400000
                if 0 <= off < size:
                    blob[off:off + min(g.value, size - off)] = buf.raw[:min(g.value, size - off)]
                    have += g.value
        addr = rb + rs
    k32.CloseHandle(h)
    if have == 0: return 0, -2
    with open(prefix + ".bin", "wb") as f: f.write(bytes(blob))
    return have, 0

result = {}

def chain():
    env = dict(os.environ)
    p = subprocess.run([sys.executable, "-X", "utf8", "-u", os.path.join(KIT, "run_all.py"),
                        "--secs", str(CHAIN_SECS), "--out", os.path.join(RUN, "chain.txt"),
                        "--retries", "1"], cwd=KIT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=CHAIN_SECS + 120)
    result["chain_rc"] = p.returncode
    print("chain rc=%s" % p.returncode, flush=True)

t = threading.Thread(target=chain, daemon=True); t.start()

t0 = time.time(); pid = None
while time.time() - t0 < CHAIN_SECS and pid is None:
    pid = find_pid()
    if pid is None: time.sleep(0.005)

if pid is None:
    print("no client appeared"); sys.exit(1)

print("client pid=%d at t=%.2fs" % (pid, time.time() - t0), flush=True)

# Burst-attempt dumps in the first seconds after appearance.
saved = []
for i in range(60):
    ok, err = peek_pid(pid)
    n, derr = dump(pid, os.path.join(OUT, "race_%02d" % i))
    print("  attempt %02d t=%.3fs readable=%s err=%s dumped=%.1fMB" %
          (i, time.time() - t0, ok, err, n / 1048576.0), flush=True)
    if n:
        saved.append(n)
        if len(saved) >= 3: break
    time.sleep(0.05)

summary = {"pid": pid, "appeared_at": time.time() - t0,
           "attempts": i + 1, "dumps": saved}
open(os.path.join(OUT, "race_summary.json"), "w", encoding="utf-8").write(
    json.dumps(summary, indent=1))
print(json.dumps(summary), flush=True)
t.join(CHAIN_SECS + 60)
