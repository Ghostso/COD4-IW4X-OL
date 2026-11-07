"""从实机 RX 取证日志生成 test_battle 的回放 fixture。

用法: python -I _gen_test_fixture.py <run_kit_dir>
读取 <run_kit_dir>/_battle_out.txt 里的
  [battle] RX 16B FULL <hex>     (第一次出现)
  [battle] RX 219B FULL <hex>    (第一次出现)
写出 tests/battle_real_packets.inc —— 不要手工编辑那个文件。
"""
import os
import re
import sys

kit = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"..\..\CHAIN_UNIFIED_20261103\run_codol_001\runs", "ONCE_20261105_151237", "kit")
log = os.path.join(kit, "_battle_out.txt")
txt = open(log, encoding="utf-8", errors="replace").read()

m = re.search(r"RX 219B FULL ([0-9A-Fa-f]+)", txt)
if not m:
    raise SystemExit("no 219B packet in %s" % log)
kx = m.group(1)
if len(kx) != 219 * 2:
    raise SystemExit("219B packet hex len=%d, expected %d" % (len(kx), 219 * 2))

mi = re.search(r"RX 16B FULL ([0-9A-Fa-f]+)", txt)
init = mi.group(1) if mi else ""
bad = [c for c in kx if c not in "0123456789abcdefABCDEF"]
if bad:
    raise SystemExit("non-hex char in kx hex: %r" % bad[:8])

cookie = kx[12:12 + 76]          # pkt[6:44] -> hex chars 12..88

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battle_real_packets.inc")


def emit(f, name, s):
    f.write("static const char *%s =\n" % name)
    for i in range(0, len(s), 60):
        f.write('    "%s"\n' % s[i:i + 60])
    f.write("    ;\n")


with open(out, "w", encoding="utf-8") as f:
    f.write("/* 自动生成, 勿手工编辑 —— 见 _gen_test_fixture.py\n")
    f.write(" * 来源: %s\n */\n" % log)
    emit(f, "KX_REAL_HEX", kx)
    emit(f, "COOKIE_REAL_HEX", cookie)
    if init:
        f.write('static const char *INIT_REAL_HEX = "%s";\n' % init)
print("wrote %s  (kx=%dB cookie=%dB init=%dB)"
      % (out, len(kx) // 2, len(cookie) // 2, len(init) // 2))
