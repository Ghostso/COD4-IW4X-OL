# -*- coding: utf-8 -*-
"""a23: xrefs (VA dwords) to key strings -> locating game protocol code."""
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
targets={
 "net-buffer NOT enough(sizeinfo)":0x99EE98,
 "lib_src\\tdr\\tdr_net.c":0x99F060,
 "gamestateupdate %d":0x9B4700,
 "CA_GAMESTATE":0x9C0974,
 "EXE_AWAITINGGAMESTATE":0x9C5F1C,
 "EXE_LOSTRELIABLECOMMANDS":0x9BB5E8,
 "EXE_SERVERCOMMANDOVERFLOW":0x9BB584,
 "CG_ServerCommand:":0x9C61AD,
 "connectResponse":0x9BFF0C,
 "EXE_CONFIGSTRINGMISMATCH":0x9B46E4,
 "EXE_POSSIBLECONFIGSTRINGMISMATCH":0x9B46C0,
 "ExpectedNetConfigStringMismatch":0x9B4D98,
 "EXE_ERR_RELIABLE_CYCLED_OUT":0x9C61C0,
}
for nm,rva in targets.items():
    va=IB+rva
    pat=struct.pack("<I",va)
    refs=[]
    i=C._img.find(pat)
    while i>=0:
        refs.append(i); i=C._img.find(pat,i+1)
    print("%-38s VA 0x%08X refs: %s"%(nm,va,", ".join("0x%X"%r for r in refs) or "NONE"))
