# -*- coding: utf-8 -*-
"""Comprehensive string scan of the unpacked image for CoD netchan / message-parser
identifiers and command-name tables. Read-only."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
def allstrings(minlen=4):
    out=[]; i=0; cur=bytearray(); st=0
    while i<len(b):
        c=b[i]
        if 32<=c<127:
            if not cur: st=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((st,cur.decode("latin1")))
            cur=bytearray()
        i+=1
    return out
S=allstrings()
print("total strings:", len(S))
KW=["svc_","clc_","serverCommand","ServerCommand","configstring","ConfigString","CONFIGSTRING",
    "gamestate","Gamestate","GAMESTATE","baseline","Baseline","packetentities","PacketEntities",
    "playerstate","PlayerState","matchstate","MatchState","netchan","Netchan","NETCHAN",
    "readBits","ReadBits","readDelta","ReadDelta","MSG_","OOB","OutOfBand","outofband",
    "nop","NOP","EOF","eof","connectResponse","challengeResponse","getInfo","getinfo","getservers",
    "print","disconnect","reliableAck","reliableCommand","fragment","Fragment"]
hits={k:[] for k in KW}
for off,s in S:
    for k in KW:
        if k in s: hits[k].append((off,s))
for k in KW:
    if hits[k]:
        print("\n### %s (%d)" % (k, len(hits[k])))
        for off,s in hits[k][:14]:
            print("   %08x  %s" % (off, s[:120]))
