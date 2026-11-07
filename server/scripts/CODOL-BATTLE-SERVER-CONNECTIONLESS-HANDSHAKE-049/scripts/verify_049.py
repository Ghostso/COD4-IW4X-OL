# -*- coding: utf-8 -*-
"""verify_049.py - self-check of the 049 static findings against the recovered image.

Recomputes every load-bearing claim from raw bytes and exits non-zero on any mismatch.
Run:  python scripts\verify_049.py
"""
import os, sys, json, struct
sys.stdout.reconfigure(encoding="utf-8")
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import importlib.util as _u
_s = _u.spec_from_file_location("h049", os.path.join(_here, "049_harness.py"))
H = _u.module_from_spec(_s); _s.loader.exec_module(H)
IB = H.IB

checks = []
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))

# 1. image identity
check("image-sha256", H.sha256_file(H.IMG) == "17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045",
      H.sha256_file(H.IMG))
check("image-size", len(H._img) == 10899456, str(len(H._img)))
check("imagebase", IB == 0x400000, hex(IB))

# 2. connectionless token table (RVAs) still resolve to the exact strings
TOKENS = {"challengeResponse": 0x9BFEE8, "connectReject": 0x9BFEFC, "connectResponse": 0x9BFF0C,
          "heartbeatresponse": 0x9BFF1C, "statResponse": 0x9BFF30, "disconnect_ack": 0x9BFF40,
          "echo": 0x9BFF50, "keyAuthorize": 0x9BFF58, "loadingnewmap": 0x9BFF70, "fastrestart": 0x9BFF90}
for name, rva in TOKENS.items():
    check("token:" + name, H.cstr(rva, 40) == name, repr(H.cstr(rva, 40)))

check("req:getchallenge", H.cstr(0x9BFD04, 32) == 'getchallenge 0 "%s"', repr(H.cstr(0x9BFD04, 32)))
check("req:connect", H.cstr(0x9BFE28, 32) == 'connect %s "%s"', repr(H.cstr(0x9BFE28, 32)))

# 3. D0 address-convention finding: pump call site 0xF9075 targets RVA 0x221E50
b = H.raw(0xF9075, 5); rel = struct.unpack_from("<i", b, 1)[0]
check("D0:pump-call-bytes", b.hex() == "e8d68d1200", b.hex())
check("D0:pump-call-target-rva", (0xF9075 + 5 + rel) == 0x221E50, hex(0xF9075 + 5 + rel))
check("D0:real-callee-prologue", H.raw(0x221E50, 3) == b"\x55\x8b\xec", H.raw(0x221E50, 8).hex())
check("D0:mislabeled-region-is-not-prologue", H.raw(0x621E50, 3) != b"\x55\x8b\xec", H.raw(0x621E50, 8).hex())

# 4. D1: P5 consumer loop boundary + single in-module caller
check("D1:p5-loop-prologue", H.raw(0x7A41D0, 3) == b"\x55\x8b\xec", H.raw(0x7A41D0, 8).hex())
callers = [a for a, k in H.e8_callers(0x7A41D0)]
check("D1:p5-loop-direct-caller", callers == [0x7A4491], str([hex(a) for a in callers]))
check("D1:no-dword-ptr-ref", len(H.refs_dword(IB + 0x7A41D0)) == 0, str(H.refs_dword(IB + 0x7A41D0)))

# 5. D1b: the P5 byte-tag branch operands
check("D1b:tag-cmp-0x81", H.raw(0x7A44F6, 2) == b"\x3c\x81", H.raw(0x7A44F6, 2).hex())
check("D1b:tag-cmp-0x83", H.raw(0x7A4557, 2) == b"\x3c\x83", H.raw(0x7A4557, 2).hex())
check("D1b:tag-cmp-0x84", H.raw(0x7A45F0, 2) == b"\x3c\x84", H.raw(0x7A45F0, 2).hex())
check("D1b:tag-cmp-0x85", H.raw(0x7A46AE, 2) == b"\x3c\x85", H.raw(0x7A46AE, 2).hex())

# 5b. D1c: exact arg provenance of the in-loop byte read
check("D1c:bufobj-load", H.raw(0x7A44AD, 6).hex() == "8b8eb0000000", H.raw(0x7A44AD, 6).hex())
check("D1c:len-load", H.raw(0x7A44B8, 6).hex() == "8bbeac000000", H.raw(0x7A44B8, 6).hex())
check("D1c:dataptr-getter-out-of-image", 0xB9BBB0 >= len(H._img), "0xB9BBB0 vs end 0x%X" % len(H._img))
check("D1c:recv-buf-field", H.raw(0x7A20CC, 6).hex() == "8dbea8000000", H.raw(0x7A20CC, 6).hex())
# 6. D2: OOB pump single caller + dequeue callers
pump_callers = [a for a, k in H.e8_callers(0xF8FB0)]
check("D2:pump-single-caller", pump_callers == [0x1BF3BC], str([hex(a) for a in pump_callers]))
dq_callers = [a for a, k in H.e8_callers(0x221E50)]
check("D2:dequeue-callers", dq_callers == [0xF8F25, 0xF9075], str([hex(a) for a in dq_callers]))
check("D2:pump-parser-call", H.raw(0xF9135, 5).hex() == "e8a68d0c00", H.raw(0xF9135, 5).hex())

# 7. D3: no image exceeds the declared section-3 raw end
for c in [r"CODOLServer\_fullimage\run1\fullimage\image_best.bin",
          r"CODOLServer\_fullimage\run2\fullimage\image_best.bin",
          r"CODOLServer\_mainline\_pop3_smoke\image_best.bin"]:
    p = os.path.join(H.WS, c)
    check("D3:size:" + os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p),
          os.path.exists(p) and os.path.getsize(p) == 10899456,
          str(os.path.getsize(p)) if os.path.exists(p) else "missing")

# 8. section-3 declared geometry (disk EXE)
check("D3:disk-section3-raw", H.d32_disk is not None)
import pefile
pe = pefile.PE(data=H._exe, fast_load=True)
sec3 = [s for s in pe.sections if s.VirtualAddress == 0xA16000]
check("D3:disk-section3-found", len(sec3) == 1, str(len(sec3)))
if sec3:
    s = sec3[0]
    check("D3:disk-section3-vsize", s.Misc_VirtualSize == 0x0DBB1CC0, hex(s.Misc_VirtualSize))
    check("D3:disk-section3-rsize", s.SizeOfRawData == 0x62000, hex(s.SizeOfRawData))
    check("D3:disk-section3-rawptr", s.PointerToRawData == 0x702000, hex(s.PointerToRawData))

# 9. 049 code deliverables exist in the 047 tree
S = r"CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047\src\Codol.BattleServer"
for rel in [r"Protocol\Handshake\ConnectionlessHandshake.cs", r"Protocol\Handshake\HandshakeEvidence.cs",
            r"Sessions\HandshakeStateMachine.cs"]:
    p = os.path.join(H.WS, S, rel)
    check("code:" + rel, os.path.exists(p), p)

n_pass = sum(1 for _, ok, _ in checks if ok)
n_fail = len(checks) - n_pass
for name, ok, detail in checks:
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  -> " + str(detail)))
print()
print("049 verify: passed=%d failed=%d total=%d" % (n_pass, n_fail, len(checks)))
print("RESULT=" + ("PASS" if n_fail == 0 else "FAIL"))
sys.exit(0 if n_fail == 0 else 1)

