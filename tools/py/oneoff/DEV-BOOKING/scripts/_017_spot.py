# -*- coding: utf-8 -*-
"""017 read-only spot check of the client's accepted-state fields."""
import ctypes, ctypes.wintypes as wt, struct, sys
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

def find_pid():
    import subprocess
    out = subprocess.run(['powershell','-NoProfile','-Command',
        "(Get-Process -Name codoMP_client_shipretail -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)"],
        capture_output=True, text=True).stdout.strip()
    return int(out) if out else 0

pid = find_pid()
print('game pid =', pid)
if not pid:
    sys.exit(0)
h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
print('OpenProcess ->', h, 'err', ctypes.get_last_error())
if not h:
    sys.exit(0)

def rd(addr, size):
    b = ctypes.create_string_buffer(size); got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), b, size, ctypes.byref(got)):
        return b.raw[:got.value]
    return None

def u32(a):
    d = rd(a, 4); return struct.unpack('<I', d)[0] if d and len(d)==4 else None

G = {'matching':0x082E13FC,'flag':0x0849B61C,'netcore':0x08269774,'dwstate':0x084ABA7C}
sp = u32(G['matching']); nsp = u32(G['netcore'])
fl = rd(G['flag'],1); dw = rd(G['dwstate'],1)
print('[global] [0x082E13FC] matching = %s' % (hex(sp) if sp is not None else 'READ-FAIL'))
print('[global] [0x0849B61C] flag     = %s' % (fl.hex() if fl else 'READ-FAIL'))
print('[global] [0x08269774] netcore  = %s' % (hex(nsp) if nsp is not None else 'READ-FAIL'))
print('[global] [0x084ABA7C] dwstate  = %s' % (dw.hex() if dw else 'READ-FAIL'))
if sp:
    vt = u32(sp)
    print('[matching] vtable [%s] = %s (expect 0x00DC7274 if this is base matching)' % (hex(sp), hex(vt) if vt else None))
    blk = rd(sp + 0x1C, 0x274)
    if blk and len(blk) == 0x274:
        print('[matching] +0x1C  = 0x%08X' % struct.unpack_from('<I', blk, 0)[0])
        print('[matching] +0x278 = 0x%04X' % struct.unpack_from('<H', blk, 0x278-0x1C)[0])
        print('[matching] +0x283 = %d' % blk[0x283-0x1C])
        print('[matching] +0x288 = 0x%04X  (byte=%d, accepted-branch marker)' % (
            struct.unpack_from('<H', blk, 0x288-0x1C)[0], blk[0x288-0x1C]))
    else:
        print('[matching] block READ-FAIL')
if nsp:
    nb = rd(nsp + 0x38, 0x4C4)
    if nb and len(nb) == 0x4C4:
        tsp = struct.unpack_from('<I', nb, 0x4F4-0x38)[0]
        print('[netcore] +0x4F4 transport = %s  +0x4F8 = %d' % (hex(tsp), nb[0x4F8-0x38]))
        if 0x10000 < tsp < 0x80000000:
            tb = rd(tsp + 0xC8, 0x580)
            if tb and len(tb) == 0x580:
                print('[transport] +0xC8(raw type) = %d  +0x644 = %d  +0x5E8 = %d' % (
                    struct.unpack_from('<I', tb, 0)[0],
                    struct.unpack_from('<I', tb, 0x644-0xC8)[0],
                    struct.unpack_from('<I', tb, 0x5E8-0xC8)[0]))
    else:
        print('[netcore] block READ-FAIL')
