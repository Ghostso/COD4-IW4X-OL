# -*- coding: utf-8 -*-
"""048_harness.py - shared read-only analysis harness for task 048.

Identity (must equal 01_INPUT_IDENTITY_AND_HASHES.md):
  image_best.bin  sha256 17cef6e0...f045  size 10899456  ImageBase 0x400000  file_offset == RVA
  codoMP_client_shipRetail.exe      36997674...b537  7841344   (.tp3 packed, on-disk)
  codoMP_client_shipRetailBase.dll  ef75220d...6a20  60327992

No writes outside this task directory. No runtime access.
"""
import os, struct, hashlib
import pefile, capstone

WS   = r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG  = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
DLEXE= os.path.join(WS, r"COD OL\codoMP_client_shipRetail.exe")
DLL  = os.path.join(WS, r"COD OL\codoMP_client_shipRetailBase.dll")
IB   = 0x400000
TASK = os.path.join(WS, "CODOL-BATTLE-SERVER-CLIENT-GAME-RECEIVE-PATH-048")

_img = open(IMG,"rb").read()
_exe = open(DLEXE,"rb").read()
_pe  = pefile.PE(data=_img, fast_load=True)
_pexe= pefile.PE(data=_exe, fast_load=True)

SECS  = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
              vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
         for s in _pe.sections]
DSECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
              vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
         for s in _pexe.sections]

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()

def sec_of(rva):
    for s in SECS:
        if s["va"] <= rva < s["va"]+max(s["vsize"], s["rsize"]): return s
    return None

def in_file(rva, n=1):
    if rva < 0 or rva+n > len(_img): return False
    s = sec_of(rva)
    return bool(s) and s["raw"] <= rva and rva+n <= s["raw"]+max(s["rsize"],0)

def raw(rva,n):  return _img[rva:rva+n] if in_file(rva,n) else None
def d32(rva):
    b=raw(rva,4); return struct.unpack("<I",b)[0] if b else None
def cstr(rva, ml=256):
    b=raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e if e>=0 else ml].decode("latin1","replace")

def disk_off(rva):
    for s in DSECS:
        if s["va"] <= rva < s["va"]+max(s["vsize"],s["rsize"]):
            return s["raw"]+(rva-s["va"])
    return None
def d32_disk(rva):
    o=disk_off(rva); return struct.unpack_from("<I",_exe,o)[0] if o is not None else None

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
def dis(rva,n=16):
    if not in_file(rva,n): return None
    return next(md.disasm(_img[rva:rva+n], IB+rva), None)
def dis_range(rva,end,maxn=200000):
    s=sec_of(rva)
    if not s: return []
    end=min(end, s["raw"]+s["rsize"]); out=[]
    for ins in md.disasm(_img[rva:end], IB+rva):
        out.append(ins)
        if len(out)>=maxn: break
    return out
def fmt(ins): return "  %08X  %-20s %s %s" % (ins.address-IB, ins.bytes.hex(), ins.mnemonic, ins.op_str)
def dump(rva,end,title=None):
    L=[]
    if title: L.append("=== %s RVA=%06X..%06X ===" % (title,rva,end))
    for i in dis_range(rva,end): L.append(fmt(i))
    return "\n".join(L)

def e8_callers(target_rva, lo=0x1000, hi=None):
    hi = hi or (len(_img)-5); out=[]; tva=IB+target_rva
    for i in range(lo,hi):
        if _img[i] in (0xE8,0xE9):
            rel=struct.unpack_from("<i",_img,i+1)[0]
            if (IB+i+5+rel)&0xFFFFFFFF == tva: out.append((i,"call" if _img[i]==0xE8 else "jmp"))
    return out

def refs_dword(value):
    pat=struct.pack("<I", value & 0xFFFFFFFF); hits=[]; i=_img.find(pat)
    while i>=0:
        if sec_of(i) is not None: hits.append(i)
        i=_img.find(pat,i+1)
    return hits

# ws2_32 ordinal -> name (resolved from the on-disk EXE's .tp3 ordinal slots)
WSA_ORD = {1:"accept",2:"bind",3:"closesocket",4:"connect",5:"getpeername",6:"getsockname",
 7:"getsockopt",8:"htonl",9:"htons",10:"ioctlsocket",11:"inet_addr",12:"inet_ntoa",13:"listen",
 14:"ntohl",15:"ntohs",16:"recv",17:"recvfrom",18:"select",19:"send",20:"sendto",21:"setsockopt",
 22:"shutdown",23:"socket",52:"gethostbyname",110:"WSAGetLastError",111:"WSASetLastError",
 114:"WSAStartup",115:"WSACleanup",116:"__WSAFDIsSet"}

def ws2_iat_map():
    m={}
    for rva in range(0x8A8380,0x8A8700,4):
        v=d32_disk(rva)
        if v is not None and v>>31: m[rva]=WSA_ORD.get(v&0xffff,"ws2ord%d"%(v&0xffff))
    return m

def w(name,text):
    p=os.path.join(TASK,name)
    os.makedirs(os.path.dirname(p),exist_ok=True)
    with open(p,"w",encoding="utf-8") as f: f.write(text)
    return p
