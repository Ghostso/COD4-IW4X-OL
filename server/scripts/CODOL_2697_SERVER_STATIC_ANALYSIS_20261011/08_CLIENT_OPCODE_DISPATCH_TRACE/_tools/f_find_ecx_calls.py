import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
OUT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'

def rva_of_file(im, off):
    for nm, va, vsz, ptr, rsz in im.sections:
        if rsz and ptr <= off < ptr + rsz:
            return nm, va + (off - ptr)
    return None, None

im = c.load()
lines = []
for target_rva in (0xA2E50, 0xA2D90):
    target_va = im.ib + target_rva
    lines.append('===== E8 -> %#x =====' % target_va)
    hits = []
    for nm, va, vsz, ptr, rsz in im.sections:
        if nm not in ('.text', '.tvm0', '.rimp'):
            continue
        for off in range(ptr, ptr + rsz - 4):
            if im.data[off] != 0xE8:
                continue
            rel = struct.unpack_from('<i', im.data, off + 1)[0]
            src_va = im.ib + va + (off - ptr)
            if src_va + 5 + rel == target_va:
                hits.append((nm, va + (off - ptr), off, src_va))
    lines.append('NONE' if not hits else str(hits))

for target_rva in (0xA2E50, 0xA2D90):
    target_va = im.ib + target_rva
    lines.append('===== dword %#x =====' % target_va)
    b = struct.pack('<I', target_va)
    start = 0
    found = False
    while True:
        j = im.data.find(b, start)
        if j < 0:
            break
        nm, rva = rva_of_file(im, j)
        lines.append('%s file=%#x rva=%s' % (nm, j, hex(rva) if rva is not None else '?'))
        found = True
        start = j + 1
    if not found:
        lines.append('NONE')

with open(os.path.join(OUT, 'f_ecx_call_search.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('\n'.join(lines))
