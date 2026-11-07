# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

TARGETS = {
  "WSAStartup_str": 0x00D90B14,
  "getaddrinfo_err_str": 0x00D33308,
  "udp_uri_str": 0x00D85AB0,
  "natType_str": 0x00DBFD28,
  "getchallenge_str": 0x00DBFD04,
  "secp224r1_str": 0x00D3D628,
  "socket_err_str": 0x00D36567,
}

def find_refs(addr):
    """在可执行段中查找 68 <imm32> / mov reg,<imm32> 引用该地址的位置。"""
    res = []
    for pre, kind, ln in ((b"\x68","push",1),(b"\xb8","mov eax",1),(b"\xb9","mov ecx",1),
                          (b"\xba","mov edx",1),(b"\xbb","mov ebx",1),(b"\xbe","mov esi",1),
                          (b"\xbf","mov edi",1),(b"\xbd","mov ebp",1)):
        needle = pre + struct.pack("<I", addr & 0xFFFFFFFF)
        for o in pe.find_bytes(needle):
            va = pe.off_to_va(o)
            if va and pe.is_exec(va):
                res.append((kind, va, ln))
    return res

for name, addr in TARGETS.items():
    refs = find_refs(addr)
    print("%-22s 0x%08X  refs=%d" % (name, addr, len(refs)))
    for kind, va, _ in refs[:10]:
        print("      %-8s at %08X" % (kind, va))
