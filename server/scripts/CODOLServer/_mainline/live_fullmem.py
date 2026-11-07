# -*- coding: utf-8 -*-
"""live_fullmem.py -- run the full chain (Auth/Lobby/battle + client via the
suspend-handle nt10 patch), then dump the client's complete module image once
it has reached an in-match state.

Runs inside the elevated agent.
"""
import ctypes, ctypes.wintypes as wt, json, os, struct, subprocess, sys, threading, time

RUN = sys.argv[1]
CHAIN_SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
KIT = os.path.join(RUN, "kit")
OUT = os.path.join(RUN, "mem")
os.makedirs(OUT, exist_ok=True)

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]
MEM_COMMIT = 0x1000; PAGE_GUARD = 0x100
LO = 0x00400000; HI = 0x0EA59000

def find_pid(name="codoMP_client_shipRetail.exe"):
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace")
    for line in r.stdout.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if c and c[0].casefold() == name.casefold():
            try: return int(c[1].replace(",", ""))
            except (IndexError, ValueError): pass
    return None

def regions(h):
    out, addr = [], LO
    mbi = MBI()
    while addr < HI:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        b = mbi.BaseAddress or 0; s = mbi.RegionSize or 0
        if s == 0: break
        b0, s0 = b, s
        if b0 < LO: s0 -= (LO - b0); b0 = LO
        if b0 + s0 > HI: s0 = HI - b0
        if s0 > 0: out.append({"base": b0, "size": s0, "state": int(mbi.State), "protect": int(mbi.Protect)})
        nxt = b + s
        if nxt <= addr: break
        addr = nxt
    return out

def dump(pid, path):
    h = k32.OpenProcess(0x0410, False, pid)
    if not h: return 0, ctypes.get_last_error()
    blob = bytearray(HI - LO); regs = regions(h); fails = 0; got_total = 0
    for r in regs:
        if r["state"] != MEM_COMMIT: continue
        if r["protect"] & PAGE_GUARD: continue
        if (r["protect"] & 0xFF) == 0x01: continue
        p = 0
        while p < r["size"]:
            n = min(0x40000, r["size"] - p)
            buf = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(r["base"] + p), buf, n, ctypes.byref(g)) and g.value:
                off = r["base"] - LO + p
                blob[off:off + g.value] = buf.raw[:g.value]
                got_total += g.value
                p += n
            else:
                n2 = min(0x1000, r["size"] - p)
                buf2 = ctypes.create_string_buffer(n2); g2 = ctypes.c_size_t(0)
                if k32.ReadProcessMemory(h, ctypes.c_void_p(r["base"] + p), buf2, n2, ctypes.byref(g2)) and g2.value:
                    off = r["base"] - LO + p
                    blob[off:off + g2.value] = buf2.raw[:g2.value]
                    got_total += g2.value
                else:
                    fails += 1
                p += n2
    k32.CloseHandle(h)
    with open(path, "wb") as f: f.write(bytes(blob))
    nz = sum(1 for b in blob if b)
    return got_total, {"nonzero": nz, "fails": fails, "regions": len(regs)}

result = {}

def chain():
    p = subprocess.run([sys.executable, "-X", "utf8", "-u", os.path.join(KIT, "run_all.py"),
                        "--secs", str(CHAIN_SECS), "--out", os.path.join(RUN, "chain.txt"),
                        "--retries", "1"], cwd=KIT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=CHAIN_SECS + 120)
    result["rc"] = p.returncode
    print("chain rc=%s" % p.returncode, flush=True)

t = threading.Thread(target=chain, daemon=True); t.start()

# Wait for the client, then wait for game_state=10 (in-match).
t0 = time.time(); pid = None
while time.time() - t0 < CHAIN_SECS:
    pid = find_pid()
    if pid: break
    time.sleep(0.1)
if not pid:
    print("no client"); sys.exit(1)
print("client pid=%d at t=%.1fs" % (pid, time.time() - t0), flush=True)

logp = os.path.join(KIT, "_c_battle_out.txt")
inmatch_t = None
while time.time() - t0 < CHAIN_SECS:
    if os.path.exists(logp):
        try:
            txt = open(logp, encoding="utf-8", errors="replace").read()
            if "TX_SNAPSHOT" in txt:
                inmatch_t = time.time() - t0
                break
        except OSError:
            pass
    time.sleep(0.5)
print("in-match at t=%s" % inmatch_t, flush=True)

# Give it a few seconds to settle, then take two dumps.
time.sleep(4)
for i in range(2):
    p = os.path.join(OUT, "mem_%d.bin" % i)
    n, meta = dump(pid, p)
    print("dump %d: %.1f MB %s" % (i, n / 1048576.0, meta), flush=True)
    json.dump({"pid": pid, "in_match_t": inmatch_t, "bytes": n, "meta": meta,
               "path": p}, open(os.path.join(OUT, "mem_%d.json" % i), "w"), indent=1)
    time.sleep(3)
t.join(60)
