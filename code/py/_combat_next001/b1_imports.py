# -*- coding: utf-8 -*-
"""B: 定位 socket 层。先解析导入表，再看哪些模块/字符串与网络相关。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE

pe = PE.load()
data = pe.data

# ---- 解析导入目录 ----
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
opt = e_lfanew + 24
magic = struct.unpack_from("<H", data, opt)[0]
dd_off = opt + (112 if magic == 0x20B else 96)
imp_rva, imp_size = struct.unpack_from("<II", data, dd_off + 8)   # entry 1 = import
print("import dir rva=0x%X size=%d" % (imp_rva, imp_size))

def rva2off(rva):
    for s in pe.sections:
        if s.vaddr <= rva < s.vaddr + max(s.vsize, s.rawsize):
            return s.rawptr + (rva - s.vaddr)
    return None

off = rva2off(imp_rva)
mods = {}
i = 0
while True:
    ent = off + i * 20
    oft, ts, fc, name_rva, first_thunk = struct.unpack_from("<IIIII", data, ent)
    if name_rva == 0 and ts == 0 and first_thunk == 0:
        break
    no = rva2off(name_rva)
    nm = data[no:data.index(b"\0", no)].decode("latin1")
    # 解析 thunk
    funcs = []
    t = rva2off(oft if oft else first_thunk)
    if t:
        k = 0
        while True:
            v = struct.unpack_from("<I", data, t + k * 4)[0]
            if v == 0: break
            if v & 0x80000000:
                funcs.append(("ord", v & 0xFFFF))
            else:
                ho = rva2off(v)
                hn = data[ho + 2:data.index(b"\0", ho + 2)].decode("latin1")
                funcs.append(("name", hn))
            k += 1
    mods[nm] = funcs
    i += 1

print("modules = %d" % len(mods))
NET = ("ws2_32.dll", "wsock32.dll", "wininet.dll", "iphlpapi.dll", "dnsapi.dll",
       "mswsock.dll", "winhttp.dll", "secur32.dll", "crypt32.dll", "ncrypt.dll")
for nm in mods:
    low = nm.lower()
    if any(n in low for n in ("ws2", "wsock", "iphlp", "dnsapi", "mswsock", "winhttp", "secur32", "crypt", "ncrypt", "wininet")):
        print()
        print("### %s  (%d funcs)" % (nm, len(mods[nm])))
        names = [f[1] for f in mods[nm] if f[0] == "name"]
        print("   " + ", ".join(sorted(names)))
