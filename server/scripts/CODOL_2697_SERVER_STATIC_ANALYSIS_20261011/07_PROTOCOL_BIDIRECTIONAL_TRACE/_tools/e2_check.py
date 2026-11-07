import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e, xref
b = e.load_bin(e.SRV, e.DATA + r"\syms_NEW.json")
print("=== Reached 0x0A49B0..0x0A4D10 ===")
e.show(b, 0xA49B0, 0xA4D10)
print("=== Reached tail 0x0A4E90..0x0A5000 ===")
e.show(b, 0xA4E90, 0xA5005)
print("=== call refs WriteSnapshot ===", xref.call_xrefs(b, {0xA4FA0}))
print("=== call refs WriteSnapshotReached ===", xref.call_xrefs(b, {0xA4860}))
print("=== abs refs WriteSnapshot ===", xref.abs_va_refs(b, {0x400000+0xA4FA0, 0xA4FA0}))
print("=== abs refs Reached ===", xref.abs_va_refs(b, {0x400000+0xA4860, 0xA4860}))
