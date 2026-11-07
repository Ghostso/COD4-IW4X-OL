import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pefile

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
ORIG = os.path.join(ROOT, r'工具\EX035_DIR\IIPS\iips.dll')
GEN  = os.path.join(ROOT, 'LocalRM.dll')

# ---------- 1. raw header scan: what is really in [0, 0x400) ----------
def header_scan(path, label):
    d = open(path, 'rb').read()
    print(f'### {label}: raw offset 0x000-0x3FF (file header region)')
    print(f'  bytes[0x000:0x040] = {d[0:0x40].hex()}')
    print(f'  bytes[0x040:0x080] = {d[0x40:0x80].hex()}')
    print(f'  bytes[0x080:0x0c0] = {d[0x80:0xc0].hex()}')
    print(f'  bytes[0x0c0:0x100] = {d[0xc0:0x100].hex()}')
    print(f'  bytes[0x100:0x140] = {d[0x100:0x140].hex()}')
    print(f'  bytes[0x140:0x180] = {d[0x140:0x180].hex()}')
    print(f'  bytes[0x180:0x1c0] = {d[0x180:0x1c0].hex()}')
    print(f'  bytes[0x1c0:0x200] = {d[0x1c0:0x200].hex()}')
    print(f'  bytes[0x200:0x240] = {d[0x200:0x240].hex()}')
    print(f'  bytes[0x240:0x280] = {d[0x240:0x280].hex()}')
    print(f'  bytes[0x280:0x2c0] = {d[0x280:0x2c0].hex()}')
    print(f'  bytes[0x2c0:0x300] = {d[0x2c0:0x300].hex()}')
    print(f'  bytes[0x300:0x340] = {d[0x300:0x340].hex()}')
    print(f'  bytes[0x340:0x380] = {d[0x340:0x380].hex()}')
    print(f'  bytes[0x380:0x400] = {d[0x380:0x400].hex()}')
    # find all occurrences of 'This program cannot be run in DOS mode'
    needle = b'This program cannot be run in DOS mode'
    pos = []
    i = d.find(needle)
    while i != -1:
        pos.append(i)
        i = d.find(needle, i+1)
    print(f'  DOS-stub string occurrences at: {[hex(x) for x in pos]}')
    # find every MZ and PE signature in the whole file
    mz, pe = [], []
    for i in range(0, min(len(d), 0x1000)):
        if d[i:i+2] == b'MZ':
            mz.append(i)
    print(f'  "MZ" appearances in first 0x1000 bytes: {[hex(x) for x in mz]}')
    print()

header_scan(ORIG, 'ORIGINAL iips.dll')
header_scan(GEN,  'GENERATED LocalRM.dll')

# ---------- 2. section table raw bytes in both ----------
print('### SECTION TABLE raw bytes (offset 0x178, 5 * 40 bytes)')
for path, label in ((ORIG, 'ORIGINAL'), (GEN, 'GENERATED')):
    d = open(path, 'rb').read()
    fh_off = struct.unpack_from('<I', d, 0x3c)[0]
    nsec = struct.unpack_from('<H', d, fh_off + 6)[0]
    szopt = struct.unpack_from('<H', d, fh_off + 20)[0]
    st = fh_off + 24 + szopt
    print(f'  {label}: lfanew={fh_off:#x} nsec={nsec} sizeopt={szopt:#x} sectab@{st:#x}')
    for i in range(5):
        raw = d[st + i*40: st + i*40 + 40]
        nm = raw[:8].rstrip(b'\x00').decode('latin1')
        vs, va, rs, rp = struct.unpack_from('<IIII', raw, 8)
        pr, pl = struct.unpack_from('<II', raw, 16)
        pn, pnl = struct.unpack_from('<HH', raw, 20)
        ch = struct.unpack_from('<I', raw, 36)[0]
        print(f'    [{i}] {nm:8s} VS={vs:#010x} VA={va:#010x} RS={rs:#010x} RP={rp:#010x} '
              f'PR={pr:#x} PL={pl:#x} PN={pn:#x}/{pnl:#x} CH={ch:#010x}')
    print()
