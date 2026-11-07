# -*- coding: utf-8 -*-
"""verify_048.py - re-derive the decisive 048 facts from raw bytes. Read-only.

Exit code 0 iff every check passes. Mirrors 046's verify_046.py discipline.
"""
import os, sys, json, struct, hashlib
sys.stdout.reconfigure(encoding="utf-8")
_here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_here)
import importlib.util
spec=importlib.util.spec_from_file_location("h048", os.path.join(_here,"048_harness.py"))
H=importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
IB=H.IB
chk=[]
def ck(n,ok,d=""): chk.append((n,bool(ok),d))
def refs(va): return sorted(H.refs_dword(IB+va))

# identity
ck("S-IMG sha256", H.sha256_file(H.IMG)=="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045")
ck("S-EXE sha256", H.sha256_file(H.DLEXE)=="36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537")
ck("S-DLL sha256", H.sha256_file(H.DLL)=="ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20")
ck("image size", len(H._img)==10899456)

# 046 inheritance reproducible
ck("0x85D870 callers == {0x85EC01}", set(a for a,_ in H.e8_callers(0x85D870))=={0x85EC01})
ck("0x85D2E0 callers == {0x85EBBB}", set(a for a,_ in H.e8_callers(0x85D2E0))=={0x85EBBB})
ck("0x87C110 callers == {0x85D49D}", set(a for a,_ in H.e8_callers(0x87C110))=={0x85D49D})
ck("0x87BA50 is jmp 0x87BE00",
   H._img[0x87BA50]==0xE9 and (IB+0x87BA50+5+struct.unpack_from("<i",H._img,0x87BA51)[0])==IB+0x87BE00)

# ws2_32 ordinal slots (raw, from disk exe)
ck("slot recv(16)", H.d32_disk(0x8A84E4)==0x80000010)
ck("slot select(18)", H.d32_disk(0x8A84E8)==0x80000012)
ck("slot socket(23)", H.d32_disk(0x8A8548)==0x80000017)

# connectionless anchors
ck("connectResponse @0x9BFF0C", H.cstr(0x9BFF0C,32)=="connectResponse")
ck("connectResponse xrefs == {0x1C17B5}", refs(0x9BFF0C)==[0x1C17B5], str([hex(x) for x in refs(0x9BFF0C)]))
ck("challengeResponse xrefs == {0x1C1685}", refs(0x9BFEE8)==[0x1C1685])
ck("connectReject xrefs == {0x1C1756}", refs(0x9BFEFC)==[0x1C1756])
ck("getchallenge fmt xrefs == {0x1C071F}", refs(0x9BFD04)==[0x1C071F])

# game protocol anchors unchanged from 046
ck("gamestateupdate %d xrefs", refs(0x9B4700)==[0x54B7B,0x73214], str([hex(x) for x in refs(0x9B4700)]))
ck("EXE_CONFIGSTRINGMISMATCH xrefs", refs(0x9B46E4)==[0x731E1,0xF2833])
ck("EXE_LOSTRELIABLECOMMANDS xrefs", refs(0x9BB5E8)==[0xF2737,0x376B14])

# P5 recv wrapper instruction shape
b=H.raw(0x876EED,6)
ck("P5 recv call slot", b==bytes.fromhex("ff15e484ca00"), b.hex() if b else "None")
ck("P4/P5 have no cross refs to game anchors",
   all(not (0x865000<=x<0x877100) for x in refs(0x9B4700)+refs(0x9B46E4)+refs(0x9BB5E8)+refs(0x9BFF0C)))

# 047 change present + 8 new tests
T47=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047"
for rel in ("src/Codol.BattleServer/Analysis/StaticEvidenceFact.cs",
            "src/Codol.BattleServer/Analysis/ProtocolModuleReadiness.cs",
            "src/Codol.BattleServer/Protocol/ConnectionlessCommands.cs",
            "src/Codol.BattleServer/Protocol/ConnectionlessTextDecoder.cs",
            "src/Codol.BattleServer/Protocol/OpcodeDispatcher.cs"):
    ck("047 new file "+os.path.basename(rel), os.path.exists(os.path.join(T47,rel.replace("/",os.sep))))

ok=sum(1 for _,c,_ in chk if c)
print("== 048 self-verification ==")
for n,c,d in chk:
    print("  [%s] %s %s" % ("PASS" if c else "FAIL", n, d))
print("\n%d/%d PASS" % (ok,len(chk)))
sys.exit(0 if ok==len(chk) else 1)
