# xref.py - static cross-reference scanner (E8/E9 rel32 calls + absolute VA refs)
import sys, struct, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e

def load(syms="syms_NEW.json"):
    return e.load_bin(e.SRV, e.DATA + "\\" + syms)

def iter_sections(b, code_only=True):
    for nm, va, vsz, ptr, rsz in b.sections:
        if rsz == 0:
            continue
        if code_only and nm not in (".text",):
            continue
        yield nm, va, vsz, ptr, rsz

def name_of(b, rva):
    if not b.sym_rvas:
        return ""
    i = bisect.bisect_right(b.sym_rvas, rva) - 1
    if i < 0:
        return ""
    return b.sym_rva_name.get(b.sym_rvas[i], "")

def call_xrefs(b, target_rvas):
    out = []
    tset = set(target_rvas)
    for nm, va, vsz, ptr, rsz in iter_sections(b):
        data = b.data
        for i in range(ptr, ptr + rsz - 5):
            op = data[i]
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", data, i + 1)[0]
                src_rva = va + (i - ptr)
                tgt = src_rva + 5 + rel
                if tgt in tset:
                    out.append((src_rva, op, tgt))
    return out

def abs_va_refs(b, va_targets, code_only=False):
    out = []
    tset = set(va_targets)
    for nm, va, vsz, ptr, rsz in iter_sections(b, code_only=code_only):
        data = b.data
        for i in range(ptr, ptr + rsz - 4):
            v = struct.unpack_from("<I", data, i)[0]
            if v in tset:
                out.append((nm, va + (i - ptr), v))
    return out

if __name__ == "__main__":
    b = load()
    print("sections ok; syms:", len(b.syms))
