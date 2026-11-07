# -*- coding: utf-8 -*-
"""045 self-verification: re-derive every decisive fact from raw bytes. READ-ONLY."""
import sys, os, hashlib, struct
sys.stdout.reconfigure(encoding="utf-8")
WS=r"D:\BaiduNetdiskDownload\使命召唤OL"
R=os.path.join(WS,"CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045")
IMG=os.path.join(WS,r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
EXE=os.path.join(WS,r"COD OL\codoMP_client_shipRetail.exe")
img=open(IMG,"rb").read(); exe=open(EXE,"rb").read()
def sha(p):
    return hashlib.sha256(open(p,"rb").read()).hexdigest()
d32=lambda b,o: struct.unpack_from("<I",b,o)[0]
checks=[]
def ck(n,c,d=""): checks.append((n,bool(c),d))
ck("S-IMG sha256", sha(IMG)=="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045", sha(IMG))
ck("S-EXE sha256", sha(EXE)=="36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537", sha(EXE))
ck("0x0CA84E8 -> RVA 0x8A84E8 is in file", (0xCA84E8-0x400000) < len(img), "filesize=0x%X"%len(img))
S1_VA,S1_RAW=0x8a8000,0x594000
eo=lambda rva: S1_RAW+(rva-S1_VA)
ck("disk 0x8A84E8 == ordinal 18", d32(exe,eo(0x8A84E8))==0x80000012, hex(d32(exe,eo(0x8A84E8))))
ck("disk 0x8A84E4 == ordinal 16", d32(exe,eo(0x8A84E4))==0x80000010, hex(d32(exe,eo(0x8A84E4))))
ck("disk 0x8A853C == ordinal 111", d32(exe,eo(0x8A853C))==0x8000006F, hex(d32(exe,eo(0x8A853C))))
ck("runtime 0x8A8534 == 0x751C0000+0x9CC0", d32(img,0x8A8534)==0x751C9CC0, hex(d32(img,0x8A8534)))
ck("runtime 0x8A853C == 0x751C0000+0x5D50", d32(img,0x8A853C)==0x751C5D50, hex(d32(img,0x8A853C)))
def e8t(tva):
    o=[]
    for i in range(0x1000,0x8a7000-5):
        if img[i]==0xE8 and d32(img,i+1)==(tva-0x400000-i-5)&0xffffffff: o.append(i)
    return o
ck("0x87BA50 E8 callers == {0x85D96E,0x85E71A}", set(e8t(0x400000+0x87BA50))=={0x85D96E,0x85E71A}, ",".join(hex(x) for x in e8t(0x400000+0x87BA50)))
ck("0x87BE00 E8 callers == 0", len(e8t(0x400000+0x87BE00))==0)
ck("0x87D5A0 callers include 0x85D9B5,0x85D9F7", {0x85D9B5,0x85D9F7} <= set(e8t(0x400000+0x87D5A0)))
ck("0x87BA50 is E9 -> 0x87BE00", img[0x87BA50]==0xE9 and (0x400000+0x87BA50+5+struct.unpack_from("<i",img,0x87BA51)[0])==0x400000+0x87BE00)
ck("path cmp 0x2733 (WSAEWOULDBLOCK)", struct.pack("<BI",0x3D,0x2733) in img)
ck("path sub 0x2714 (WSAEINTR)", struct.pack("<BI",0x2D,0x2714) in img)
need=["00_INDEX.md","01_SAMPLE_IDENTITY_AND_ADDRESS_MAPPING.md","02_IMPORT_IDENTITY_HYPOTHESES.md","03_IO_PATH_EVIDENCE.tsv","04_SIX_WAY_ARCHITECTURE_MATRIX.tsv","05_PROTOCOL_EVIDENCE_MATRIX.tsv","06_CAUSAL_DIFFERENCE_ANALYSIS.md","07_SERVER_READINESS_ISSUE_LEDGER.tsv","08_NEXT_ACTION_DECISION.md","TEST_AND_VALIDATION_RESULTS.md","SHA256SUMS.txt","FILE_HASH_MANIFEST.tsv"]
miss=[f for f in need if not os.path.exists(os.path.join(R,f))]
ck("all 12 deliverables exist", not miss, "missing:"+",".join(miss))
ok=sum(1 for _,c,_ in checks if c)
print("== 045 self-verification ==")
for n,c,d in checks: print("  [%s] %s %s"%("PASS" if c else "FAIL", n, d))
print("\n%d/%d PASS"%(ok,len(checks)))
sys.exit(0 if ok==len(checks) else 1)
