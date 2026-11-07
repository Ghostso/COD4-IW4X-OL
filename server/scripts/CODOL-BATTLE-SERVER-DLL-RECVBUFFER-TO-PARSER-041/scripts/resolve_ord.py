# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
import pefile

# resolve ws2_32 ordinals from local system dll (non-target, read-only)
ordmap={}
for p in [r"C:\Windows\SysWOW64\ws2_32.dll"]:
    try:
        q=pefile.PE(p, fast_load=False)
        for e in q.DIRECTORY_ENTRY_EXPORT.symbols:
            if e.name: ordmap[e.ordinal]=e.name.decode()
    except Exception as ex:
        print("err",ex)

slots = {
 0x10b02a40:"ord116", 0x10b02a48:"ord17", 0x10b02a4c:"ord20", 0x10b02a54:"ord151",
 0x10b02a5c:"WSACloseEvent", 0x10b02a60:"WSASocketW", 0x10b02a64:"WSAEnumNetworkEvents",
 0x10b02a68:"WSAEventSelect", 0x10b02a6c:"WSACreateEvent", 0x10b02a70:"WSAWaitForMultipleEvents",
 0x10b02a9c:"ord3", 0x10b02ac0:"?", 0x10b02ac4:"?", 0x10b02ac8:"?",
 0x10b0232c:"CreateThread", 0x10b021d0:"SleepEx", 0x10b022d4:"ReleaseMutex",
 0x10b0227c:"WaitForSingleObject", 0x10b021c8:"QueueUserAPC", 0x10b02400:"TerminateThread",
}
for va,label in slots.items():
    v = rd32(va-IB)
    if v is None: print("0x%08X %s -> <oob>"%(va,label)); continue
    if v & 0x80000000:
        od=v&0xffff
        print("0x%08X %-28s ORD %d = %s" % (va,label,od,ordmap.get(od,"?")))
    else:
        hn=read_hintname(v); print("0x%08X %-28s NAME = %s" % (va,label, hn[1].decode() if hn else "?"))
