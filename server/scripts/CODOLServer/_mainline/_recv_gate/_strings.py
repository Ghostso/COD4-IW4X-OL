import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_strings.log")

buf = io.StringIO()
try:
    sys.path.insert(0, os.path.join(HERE, ".."))
    r = __import__("_recv_gate_disasm")
    img = open(r.IMG, "rb").read()
    BASE = r.BASE

    VAS = [
        0xD352A8,   # sscanf fmt with 3 conversions (parser @0xADE38B)
        0xD34218,   # log string before [x+0x870C] = 0x130
        0xD34E34,   # proxyish check arg1 (status parse)
        0xDBBCBC,   # proxyish check arg2
        0xD351AC, 0xD351D4, 0xD351E0, 0xD35208, 0xD35238,
        0xD389E0,   # "HTTP/1.%d %d"
        0xCBE460,   # prop 0x2734 value (case @0xC76091)
        0xD95664, 0xD95674, 0xD95680,  # URL fmt strings (c761xx)
        0xD33BB8, 0xD33BC0, 0xD33BC8,  # header-name candidates (ad4a70 str)
        0xD5A1F8,   # vtable base
        0xD5A228,   # "auth_task"
        0xD5A238,   # 0x15-dword struct copied in vt_b99350
        0xD5A2AC,   # string in vt_b994b0
        0xDAE091,   # ret string in numeric getter case [eax+0x478]!=0
    ]
    lines = []
    for va in VAS:
        o = va - BASE
        if o < 0 or o >= len(img):
            lines.append("VA=0x%08X OUT-OF-RANGE" % va)
            continue
        raw = img[o:o + 96]
        txt = raw.split(b"\x00")[0]
        val = txt.decode("latin1")
        if any(ord(c) > 126 or (ord(c) < 32 and c not in "\t") for c in val):
            val = "hex:" + txt.hex() + "  printable:" + \
                "".join(chr(c) if 32 <= c <= 126 else "." for c in txt[:40])
        lines.append("VA=0x%08X  %s" % (va, val))
    r.OUT = HERE
    r.write_report("gate_strings.txt", lines)
    buf.write("ok %d strings\n" % len(VAS))
except Exception:
    buf.write(traceback.format_exc())
open(LOG, "w", encoding="utf-8").write(buf.getvalue())
print("done")
