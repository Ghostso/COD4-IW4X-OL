import sys, traceback
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import engine_dump as ED, ctypes, ctypes.wintypes as wt
h = ED.open_pid(8700)
try:
    print('protection map:')
    for b,s,st,pr in ED.protection_map(h, 0x00994000, 0x4D1000):
        print('  %08x size=%x state=%x protect=%x' % (b,s,st,pr))
    print('reading main region...')
    d = ED.read_region(h, 0x00994000, 0x4D1000)
    print('main ok', len(d))
    print('reading sentinel...')
    s = ED.read_region(h, 0x00CA8000, 0x1000)
    print('sentinel ok', len(s), sum(1 for x in s if x))
    print('derive:', ED.derive_runtime_code_range(s))
except Exception:
    traceback.print_exc()
finally:
    import ctypes as C
    C.windll.kernel32.CloseHandle(h)
