# -*- coding: utf-8 -*-
"""041 evidence generator (read-only). Writes evidence/ files."""
import sys, os, io, json, struct, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
import pefile

EV = C.EV
os.makedirs(EV, exist_ok=True)

def w(path, text):
    io.open(os.path.join(EV, path), "w", encoding="utf-8", newline="").write(text)

def disasm_text(lo, hi, title):
    L = ["# %s" % title, "# Base: VA = 0x%08X + RVA ; .text file_off = RVA - 0xC00" % IB, ""]
    for i in dis_range(lo, hi):
        rva = i.address - IB
        off = rva2off(rva)
        L.append("0x%06X  VA=0x%08X  off=0x%06X  %-18s %-11s %s" % (
            rva, i.address, off, i.bytes.hex(), i.mnemonic, i.op_str))
    return "\n".join(L) + "\n"

w("recv_cluster_disasm.txt", disasm_text(0x235CD0, 0x236150,
   "041 recv cluster: ctor 0x235CD0 / dtor 0x235DC0 / sendrecv 0x235E00 / checksum 0x2360B0 / tick 0x236110"))
w("caller_threadproc_disasm.txt", disasm_text(0x231050, 0x231181,
   "041 caller thread proc 0x231050 (CreateThread start address) + tail"))
w("ping_manager_disasm.txt", "\n\n".join([
    disasm_text(0x22D470, 0x22D580, "ping manager: create-thread + map insert (0x22D470)"),
    disasm_text(0x22A670, 0x22A770, "ping map: lookup-by-key (0x22A670)"),
    disasm_text(0x22A770, 0x22A840, "ping map: accessor (0x22A770)"),
    disasm_text(0x22AF90, 0x22B010, "ping map: lower_bound (0x22AF90)"),
    disasm_text(0x22B010, 0x22B090, "ping map: accessor2 (0x22B010)"),
]))

# ---- IAT slot resolution ----
ordmap = {}
q = pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=False)
for e in q.DIRECTORY_ENTRY_EXPORT.symbols:
    if e.name: ordmap[e.ordinal] = e.name.decode()
def slot_info(r):
    v = rd32(r)
    if not v: return ("NULL", None, "")
    if v & 0x80000000:
        od = v & 0xffff
        return ("ORDINAL", od, ordmap.get(od, "ord:%d" % od))
    hn = read_hintname(v)
    return ("NAME", None, hn[1].decode("latin1") if hn else "?")

rows = ["SLOT_RVA\tSLOT_VA\tKIND\tORDINAL\tRESOLVED_NAME\tROLE_041"]
role = {
 0xB02A40: "WSACleanup (socket stack teardown, 0x45313C thunk)",
 0xB02A48: "recvfrom -> RECEIVE POINT (0x235F7E, also libcurl 0x42D97F)",
 0xB02A4C: "sendto (ICMP echo request, 0x235EC9)",
 0xB02A54: "__WSAFDIsSet (0x453148 thunk, not used in this cluster)",
 0xB02A5C: "WSACloseEvent (event teardown 0x235DD7/0x23112E)",
 0xB02A60: "WSASocketW (only socket-create site in DLL, 0x235D6D)",
 0xB02A64: "WSAEnumNetworkEvents (0x235F4C)",
 0xB02A68: "WSAEventSelect (0x235D81, FD_READ)",
 0xB02A6C: "WSACreateEvent (0x235D4F)",
 0xB02A70: "WSAWaitForMultipleEvents (0x235F23, 0x23602F)",
 0xB0232C: "CreateThread (0x22D53C - launches thread proc 0x10231050)",
 0xB021D0: "SleepEx (0x231103, 100ms poll)",
 0xB0227C: "WaitForSingleObject (mutex)",
 0xB022D4: "ReleaseMutex",
 0xB021C8: "QueueUserAPC (0x22FD84 - resume/steer worker)",
 0xB02400: "TerminateThread (0x22FDA3)",
 0xB02A9C: "closesocket (ord3, 0x4530EE thunk, 0x23111C)",
 0xB023B4: "GetLocalTime", 0xB023BC: "SystemTimeToFileTime",
 0xB0221C: "GetCurrentProcessId", 0xB02224: "GetTickCount",
}
for r, lab in sorted(role.items()):
    k, od, nm = slot_info(r)
    rows.append("0x%06X\t0x%08X\t%s\t%s\t%s\t%s" % (
        r, IB+r, k, (od if od is not None else ""), nm, lab))
w("iat_slot_resolution.tsv", "\n".join(rows) + "\n")

# ---- all receive-family call sites ----
def tgt15(ins):
    m = re.search(r"\[(0x[0-9a-f]+)\]", ins.op_str)
    return int(m.group(1), 16) if m else None
ff = scan_ff15()
recv_slots = {}
for k in range(768):
    r = 0xB02000 + 4*k; k2, od, nm = slot_info(r)
    if nm.lower().startswith("recv"):
        recv_slots[r] = nm
lines = ["CALL_RVA\tCALL_VA\tSECTION\tIAT_SLOT_VA\tAPI\tREGION_NOTE"]
ff_sorted = sorted(ff, key=lambda i: i.address)
for i in ff_sorted:
    t = tgt15(i)
    if t is None: continue
    tr = t - IB
    if tr in recv_slots:
        rva = i.address - IB
        note = "041 PING CLUSTER (0x235xxx)" if 0x235000 <= rva < 0x240000 else \
               ("libcurl/OpenSSL region" if rva >= 0x2D0000 else "other")
        lines.append("0x%06X\t0x%08X\t%s\t0x%08X\t%s\t%s" % (rva, i.address, sec_of_rva(rva), t, recv_slots[tr], note))
w("all_receive_callsites.tsv", "\n".join(lines) + "\n")

print("wrote recv_cluster_disasm.txt, caller_threadproc_disasm.txt, ping_manager_disasm.txt,")
print("      iat_slot_resolution.tsv, all_receive_callsites.tsv")
