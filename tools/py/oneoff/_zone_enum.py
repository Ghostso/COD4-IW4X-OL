"""Static enumeration of zone names requested by the CODOL client (READ-ONLY).

Rationale (all statically verified on the plaintext runtime image):
  * zone requests land in a global table at 0x01D06440, record stride 0x44,
    layout = { char name[0x40]; dword group_mask@0x40 }  (count at 0x239B11C)
  * 0x49F280 walks that table and calls 0x49ED40(record, mask)
  * 0x49ED40 does snprintf(buf,0x100,"%s.ff", record) -> looks up main\\<name>.ff
  * the names come from stack arrays built with immediate string pointers in the
    family that calls 0x49E160 / 0x49E410 / 0x49E4D0 / 0x49E540
  => every requested zone name is a code immediate; it can be enumerated offline.

Usage:
  python -X utf8 _zone_enum.py enq      -> arch_zone_requests.csv
  python -X utf8 _zone_enum.py diff     -> compare with sandbox main\\
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(ROOT, "CODOLServer", "_mainline",
                     "_dyn100_run_20260925_182324", "live", "image_best.bin")
MAIN = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923", "main")
BASE = 0x400000
CODE_LO, CODE_HI = 0x00400000, 0x00E16000      # executable ranges (.tp3 1st/2nd)
STR_LO, STR_HI = 0x00D80000, 0x00E60000        # string/immediate region

# family that feeds the zone-request table (call sites of 0x49E160)
ZONE_CALLERS = [0x49E67B, 0x49EC93, 0x4FCC7C, 0x4FCD32, 0x4FCE4F, 0x4FE76C,
                0x4FE951, 0x515ED5, 0x59B212, 0x5BFBF9, 0x5BFCBB, 0x5C2C23,
                0x5C8448, 0x5CB441, 0x5CB451, 0x813D09]

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_\./]{2,60}$")


def load():
    with open(IMAGE, "rb") as f:
        return f.read()


def func_start(data, va, back=0x600):
    """Nearest preceding `55 8B EC` prologue (push ebp; mov ebp,esp)."""
    lo = max(BASE, va - back)
    for p in range(va - BASE - 3, lo - BASE, -1):
        if data[p:p + 3] == b"\x55\x8b\xec":
            if p >= 4 and data[p - 1] in (0xCC, 0xC3, 0x90, 0x5D):
                return BASE + p
            if data[p - 4:p - 1] == b"\xcc\xcc\xcc":
                return BASE + p
    return 0


def read_cstr(data, va, maxlen=80):
    if not (STR_LO <= va < STR_HI):
        return None
    o = va - BASE
    e = data.find(b"\x00", o, o + maxlen)
    if e < 0:
        return None
    raw = data[o:e]
    if not raw:
        return None
    try:
        s = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    if NAME_RE.match(s):
        return s
    return None


def _c7_len(data, p):
    """Length of `mov r/m32, imm32` (opcode C7) starting at p, else 0."""
    if data[p] != 0xC7:
        return 0
    m = data[p + 1]
    mod, rm = m >> 6, m & 7
    n = 2
    sib_disp0 = False
    if rm == 4:                              # SIB follows
        sib = data[p + 2]
        n += 1
        sib_disp0 = (mod == 0) and ((sib & 7) == 5)
    if mod == 0:
        if rm == 5:
            n += 4
        elif sib_disp0:
            n += 4
    elif mod == 1:
        n += 1
    elif mod == 2:
        n += 4
    return n + 4                             # + imm32


def build_imm_index(data):
    """One pass over the code range -> {imm_value: [(instr_va, kind), ...]}."""
    idx = {}

    def add(va, val, kind):
        idx.setdefault(val, []).append((va, kind))

    lo, hi = CODE_LO - BASE, CODE_HI - BASE
    for p in range(lo, hi - 12):
        b = data[p]
        if b == 0xC7:
            ln = _c7_len(data, p)
            if ln:
                add(BASE + p, struct.unpack_from("<I", data, p + ln - 4)[0],
                    "mov-imm")
        elif b == 0x68:
            add(BASE + p, struct.unpack_from("<I", data, p + 1)[0], "push")
    return idx


_IMM = None


def imm_sites(data, target):
    global _IMM
    if _IMM is None:
        _IMM = build_imm_index(data)
    return _IMM.get(target, [])


def collect(data):
    """All name-like strings referenced as code immediates."""
    cand = {}
    seen_va = set()
    for m in re.finditer(rb"[\x20-\x7e]{3,64}", data):
        va = BASE + m.start()
        if not (STR_LO <= va < STR_HI) or va in seen_va:
            continue
        s = read_cstr(data, va)
        if not s:
            continue
        seen_va.add(va)
        for i, kind in imm_sites(data, va):
            cand[(s, va, i)] = (kind, func_start(data, i))
    return cand



def zone_family(data):
    """Returns (direct, related) function-start dicts.

    direct  = functions containing a call to the zone-submit 0x49E160
    related = functions called from within a direct function (one hop), which
              is where the marketplace / common_mp name arrays are built
    """
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    direct, related = {}, {}
    for c in ZONE_CALLERS:
        f = func_start(data, c)
        if f:
            direct[f] = direct.get(f, 0) + 1
    for f in list(direct):
        blob = data[f - BASE: f - BASE + 0x800]
        for ins in md.disasm(blob, f):
            if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                g = func_start(data, int(ins.op_str, 16))
                if g:
                    related[g] = related.get(g, 0) + 1
            if ins.mnemonic == "ret":
                break
    # keep only callees that themselves gate on the "is zone loaded" test 0x49F180
    filt = {}
    for g in related:
        for ins in md.disasm(data[g - BASE: g - BASE + 0x600], g):
            if ins.mnemonic == "call" and ins.op_str.startswith("0x") \
                    and int(ins.op_str, 16) == 0x49F180:
                filt[g] = related[g]
                break
            if ins.mnemonic == "ret":
                break
    return direct, filt


ZONE_LIKE = re.compile(r"(_mp$|^patch_|^localized_|^common_|^ui_mp$|^menu$|"
                       r"^console$|^white$|^default2d$|loadscreen$)")


# producers I read instruction-by-instruction (array built then passed to 0x49E160)
VERIFIED = {0x4FCC00, 0x4FCCA0, 0x4FCD50, 0x49E410}
# same "check 0x49F180 then load" pattern, inferred
PATTERN = {0x49E600, 0x4FE830}


def _conf(f):
    if f in VERIFIED:
        return "verified"
    if f in PATTERN:
        return "pattern"
    return "candidate"


def cmd_enq():
    data = load()
    direct, related = zone_family(data)
    rows = []
    for (s, sva, iva), (kind, f) in collect(data).items():
        if f in direct:
            mem = "direct"
        elif f in related:
            mem = "related"
        else:
            mem = ""
        if not mem:
            continue
        zl = "zone" if (ZONE_LIKE.search(s) or
                        0xDB5E00 <= sva <= 0xDB6600) else ""
        rows.append((s, "%08X" % sva, "%08X" % iva, kind, "%08X" % f, mem,
                     zl, _conf(f)))
    rows.sort(key=lambda r: ({"direct": 0, "related": 1}[r[5]],
                             {"verified": 0, "pattern": 1, "candidate": 2}[r[7]],
                             r[0]))
    out = os.path.join(ROOT, "arch_zone_requests.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("name|str_va|instr_va|kind|func|member|zone_like|confidence\n")
        for r in rows:
            f.write("%s|%s|%s|%s|%s|%s|%s|%s\n" % r)
    zrows = [r for r in rows if r[6] == "zone"]
    print("wrote %s (%d rows; zone-shaped=%d)" % (out, len(rows), len(zrows)))
    for r in zrows:
        print("  %-9s %-9s %-34s %s func=%s" % (r[7], r[5], r[0], r[1], r[4]))
    return 0


def cmd_diff():
    data = load()
    direct, related = zone_family(data)
    present = set()
    if os.path.isdir(MAIN):
        for n in os.listdir(MAIN):
            if n.lower().endswith(".ff"):
                present.add(n[:-3].lower())
    want = {}
    for (s, sva, iva), (kind, f) in collect(data).items():
        if f in direct or f in related:
            if ZONE_LIKE.search(s) or 0xDB5E00 <= sva <= 0xDB6600:
                want[s.lower()] = (sva, _conf(f))
    print("main\\ *.ff present : %d" % len(present))
    print("requested (zone set): %d" % len(want))
    for lvl in ("verified", "pattern", "candidate"):
        keys = [k for k in want if want[k][1] == lvl]
        if not keys:
            continue
        print()
        print("=== %s (%d) ===" % (lvl, len(keys)))
        for k in sorted(keys):
            sva, _ = want[k]
            print("  %-9s %-42s str@%08X" %
                  ("MISSING" if k not in present else "ok", k, sva))
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "enq":
        return cmd_enq()
    if argv[0] == "diff":
        return cmd_diff()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
