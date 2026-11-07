# -*- coding: utf-8 -*-
"""verify_046.py - re-derive every decisive 046 fact from raw bytes. STRICTLY READ-ONLY."""
import sys, os, struct, hashlib
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _c046 as C
T=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IB=C.IB
checks=[]
def ck(n,c,d=""): checks.append((n,bool(c),d))
def s(rva,ml=300):
    b=C.raw(rva,ml); 
    return None if b is None else b[:b.find(b"\x00")].decode("latin1","replace")

# identity
ck("S-IMG sha256", C.sha256_file(C.IMG)=="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045")
ck("S-EXE sha256", C.sha256_file(C.EXE)=="36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537")
ck("S-DLL sha256", C.sha256_file(C.DLL)=="ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20")

# A: 045 chain is TQOS
ck("'udp://%s:%d' at RVA 0x985AB0", s(0x985AB0)=="udp://%s:%d", repr(s(0x985AB0)))
ck("QOSCSPkg at 0x985AA4", s(0x985AA4)=="QOSCSPkg")
ck("QOSSSPkg at 0x985A78", s(0x985A78)=="QOSSSPkg")
ck("tqos_create_protohandle err at 0x985B1C", s(0x985B1C)=="tqos_create_protohandle err")
ck("0x85D870 callers == {0x85EC01}", set(a for a,_ in C.e8_callers(0x85D870))=={0x85EC01})
ck("0x85D2E0 callers == {0x85EBBB}", set(a for a,_ in C.e8_callers(0x85D2E0))=={0x85EBBB})
ck("0x87D5A0 callers (E8) == {0x85D3DB,0x85D418,0x85D9B5,0x85D9F7}",
   set(a for a,_ in C.e8_callers(0x87D5A0))=={0x85D3DB,0x85D418,0x85D9B5,0x85D9F7})
ck("0x87C110 callers (E8) == {0x85D49D}", set(a for a,_ in C.e8_callers(0x87C110))=={0x85D49D})
ck("0x87BA50 is E9 -> 0x87BE00", C._img[0x87BA50]==0xE9 and
   (IB+0x87BA50+5+struct.unpack_from("<i",C._img,0x87BA51)[0])==IB+0x87BE00)
# TDR
ck("lib_src\\tdr\\tdr_net.c at 0x99F060", s(0x99F060)=="lib_src\\tdr\\tdr_net.c", repr(s(0x99F060)))
ck("net-buffer diag at 0x99EE98", "net-buffer NOT enough" in (s(0x99EE98) or ""))

# B: decoders read-only consumers, no allocation of input
ck("0x87ED70 has 43 E8 callers", len(C.e8_callers(0x87ED70))==43, str(len(C.e8_callers(0x87ED70))))
ck("0x87EDB0 caller == {0x87C9B7}", set(a for a,_ in C.e8_callers(0x87EDB0))=={0x87C9B7})
ck("0x879AC0 callers == {0x8799BC,0x879D60,0x879F44,0x87A1F7}",
   set(a for a,_ in C.e8_callers(0x879AC0))=={0x8799BC,0x879D60,0x879F44,0x87A1F7})

# E: game-protocol strings live in a DIFFERENT code region and have xrefs there
def refs(va):
    out=[]; i=C._img.find(struct.pack("<I",va))
    while i>=0: out.append(i); i=C._img.find(struct.pack("<I",va),i+1)
    return out
r=refs(IB+0x9B4700)
ck("'gamestateupdate %d' refs == {0x54B7B,0x73214}", set(r)=={0x54B7B,0x73214}, str([hex(x) for x in r]))
r=refs(IB+0x9B46E4)
ck("'EXE_CONFIGSTRINGMISMATCH' refs == {0x731E1,0xF2833}", set(r)=={0x731E1,0xF2833}, str([hex(x) for x in r]))
r=refs(IB+0x9BB5E8)
ck("'EXE_LOSTRELIABLECOMMANDS' refs == {0xF2737,0x376B14}", set(r)=={0xF2737,0x376B14}, str([hex(x) for x in r]))
# no cross-reference between game-string region and the TQOS chain
ck("no game-string xref inside 0x85D000-0x88F000",
   all(not (0x85D000<=x<0x88F000) for x in
       refs(IB+0x9B4700)+refs(IB+0x9B46E4)+refs(IB+0x9BB5E8)+refs(IB+0x9BFF0C)+refs(IB+0x9B46C0)))

# ws2 ordinals
ck("slot 0xCA84E8 -> ord18 select", struct.unpack_from("<I",C._exe,0x594000+0x8A84E8-0x8A8000)[0]==0x80000012)
ck("slot 0xCA84E4 -> ord16 recv",   struct.unpack_from("<I",C._exe,0x594000+0x8A84E4-0x8A8000)[0]==0x80000010)

# movement artifacts
ck("SHA256SUMS.txt in extracted lists 79 files",
   sum(1 for l in open(os.path.join(T,"_extracted","SHA256SUMS.txt"),encoding="utf-8") if len(l.split()[0])==64)==79)

# outputs exist
need=["00_INDEX.md","01_INPUT_INTEGRITY.md","02_045_CHAIN_ATTRIBUTION.md","03_DECODER_SEMANTICS.md",
      "04_MOVEMENT_EVIDENCE_MATRIX.md","05_CLIENT_PATH_MAPPING.md","06_SIX_WAY_CROSS_VALIDATION.md",
      "07_A_BLOCKERS_STATUS.md","08_TESTS_AND_HASHES.md","09_NEXT_ACTION_DECISION.md"]
miss=[f for f in need if not os.path.exists(os.path.join(T,f))]
ok=sum(1 for _,c,_ in checks if c)
print("== 046 self-verification ==")
for n,c,d in checks: print("  [%s] %s %s"%("PASS" if c else "FAIL",n,d))
print("\n%d/%d PASS"%(ok,len(checks)))
if miss: print("MISSING DELIVERABLES:",miss)
sys.exit(0 if ok==len(checks) and not miss else 1)

