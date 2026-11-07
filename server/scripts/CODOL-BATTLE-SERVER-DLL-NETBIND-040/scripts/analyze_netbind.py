#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CODOL-BATTLE-SERVER-DLL-NETBIND-040
静态解析主 DLL (codoMP_client_shipRetailBase.dll) 的动态 Winsock 绑定路径。

只读分析：不修改目标 DLL/EXE，不启动游戏，不做动态调试。
输出: evidence/*.tsv, evidence/*.json

关键方法:
  - PE 节区表 -> RVA/VA/file-offset 映射 (严格按节区表, 不假设 RVA==offset)
  - .text 线性反汇编 (capstone) 建立指令图, 提取 FF15 (call [abs32]) 与 E8 (call rel32)
  - .idata2 隐藏导入表: IAT 槽 0xB02000.. 每个槽文件值为 IMAGE_IMPORT_BY_NAME 指针或序号
  - WS2_32/WSOCK32 序号导入用本机 ws2_32.dll/wsock32.dll 只读导出表解析 (非目标资产)
"""
import pefile, struct, capstone, json, os, hashlib, collections, sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
DLL  = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
EV   = os.path.join(ROOT, "evidence")
os.makedirs(EV, exist_ok=True)

b  = open(DLL, "rb").read()
pe = pefile.PE(data=b, fast_load=False)
IB = pe.OPTIONAL_HEADER.ImageBase
SIZE_IMG = pe.OPTIONAL_HEADER.SizeOfImage

SECTIONS = []
for s in pe.sections:
    SECTIONS.append(dict(
        name=s.Name.rstrip(b"\0").decode("latin1"),
        va=s.VirtualAddress, vsize=s.Misc_VirtualSize,
        raw=s.PointerToRawData, rsize=s.SizeOfRawData))

def sec_of_rva(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            return s["name"]
    return "?"

def rva2off(r):
    for s in SECTIONS:
        if s["va"] <= r < s["va"] + max(s["vsize"], s["rsize"]):
            return s["raw"] + (r - s["va"])
    return None

def off2rva(o):
    for s in SECTIONS:
        if s["raw"] <= o < s["raw"] + s["rsize"]:
            return s["va"] + (o - s["raw"])
    return None

def rd32(rva):
    o = rva2off(rva)
    return struct.unpack("<I", b[o:o+4])[0] if o is not None else None

def cstr(rva, maxlen=200):
    o = rva2off(rva)
    if o is None: return None
    e = b.find(b"\0", o, o+maxlen)
    if e < 0: e = o+maxlen
    return b[o:e]

def read_hintname(rva):
    o = rva2off(rva)
    if o is None: return None
    hint = struct.unpack("<H", b[o:o+2])[0]
    e = b.find(b"\0", o+2)
    try: nm = b[o+2:e].decode("ascii")
    except Exception: nm = b[o+2:e].decode("latin1")
    return hint, nm

# ---------------------------------------------------------------- 外部 API 表 (非目标资产, 只读)
def export_table(path):
    t_ord, t_name = {}, {}
    if not os.path.exists(path): return t_ord, t_name
    try:
        p = pefile.PE(path, fast_load=False)
        if hasattr(p, "DIRECTORY_ENTRY_EXPORT"):
            for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
                if e.name:
                    n = e.name.decode("latin1")
                    t_name[n] = e.ordinal
                    t_ord[e.ordinal] = n
    except Exception:
        pass
    return t_ord, t_name

WS2_ORD, WS2_NAME = export_table(r"C:\Windows\SysWOW64\ws2_32.dll")
WSK_ORD, WSK_NAME = export_table(r"C:\Windows\SysWOW64\wsock32.dll")

WINSOCK_API_NAMES = set(list(WS2_NAME.keys()) + list(WSK_NAME.keys()))
WINSOCK_EXTRA = {
    "WSAStartup","WSACleanup","WSAGetLastError","WSASetLastError","__WSAFDIsSet",
    "WSAIoctl","WSARecv","WSARecvFrom","WSASend","WSASendTo","recv","recvfrom","send","sendto",
    "select","ioctlsocket","socket","closesocket","connect","bind","listen","accept",
    "gethostbyname","gethostbyaddr","getaddrinfo","getnameinfo","freeaddrinfo","gethostname",
    "inet_addr","inet_ntoa","htonl","htons","ntohl","ntohs","shutdown","getpeername","getsockname",
    "setsockopt","getsockopt","WSASocketA","WSASocketW","WSAEventSelect","WSAEnumNetworkEvents",
    "WSACreateEvent","WSACloseEvent","WSAWaitForMultipleEvents","WSAEnumProtocolsA","WSAEnumProtocolsW",
    "WSAAsyncSelect","WSAResetEvent","WSASetEvent","WSAAddressToStringA","WSAAddressToStringW",
}
WINSOCK_API_NAMES |= WINSOCK_EXTRA

# ---------------------------------------------------------------- .idata2 隐藏导入表
IAT_BASE = 0xB02000
IAT_DIR_SIZE = 0xC00                 # 数据目录 12 (IAT) Size
N_SLOTS = IAT_DIR_SIZE // 4          # 768

rows = []
for k in range(N_SLOTS):
    slot_rva = IAT_BASE + 4*k
    slot_va  = IB + slot_rva
    off      = rva2off(slot_rva)
    v        = rd32(slot_rva)
    kind = "NULL"; hint = ""; name = ""
    if v:
        if v & 0x80000000:
            kind = "ORDINAL"; hint = ""; name = "ordinal:0x%x(%d)" % (v & 0xffff, v & 0xffff)
        else:
            hn = read_hintname(v)
            if hn:
                kind = "NAME"; hint = hn[0]; name = hn[1]
            else:
                kind = "RAWPTR"
    # winsock 归属推断
    is_ws = False
    if kind == "NAME" and name in WINSOCK_API_NAMES: is_ws = True
    if kind == "ORDINAL":
        od = v & 0xffff
        if 0xB02A40 <= slot_rva <= 0xB02B60 and od in WS2_ORD: is_ws = True
    rows.append(dict(idx=k, slot_rva=slot_rva, slot_va=slot_va, slot_off=off,
                     kind=kind, value=v, hint=hint, name=name, winsock=is_ws))

with open(os.path.join(EV, "idata2_iat_slots.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("SLOT_IDX\tSLOT_RVA\tSLOT_VA\tFILE_OFF\tKIND\tVALUE\tHINT\tAPI_NAME\tWINSOCK\n")
    for r in rows:
        f.write("%d\t0x%08X\t0x%08X\t%s\t%s\t0x%08X\t%s\t%s\t%s\n" % (
            r["idx"], r["slot_rva"], r["slot_va"],
            ("0x%06X" % r["slot_off"]) if r["slot_off"] is not None else "",
            r["kind"], r["value"], r["hint"], r["name"], "Y" if r["winsock"] else "N"))

winsock_slots = [r for r in rows if r["winsock"]]
with open(os.path.join(EV, "winsock_slots.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("SLOT_IDX\tSLOT_RVA\tSLOT_VA\tFILE_OFF\tKIND\tAPI_NAME\tRESOLVED_OR_ORDINAL\n")
    for r in winsock_slots:
        resolved = r["name"]
        if r["kind"] == "ORDINAL":
            od = r["value"] & 0xffff
            resolved = "%s(ws2_ord=%d)" % (WS2_ORD.get(od, "?"), od)
        f.write("%d\t0x%08X\t0x%08X\t0x%06X\t%s\t%s\t%s\n" % (
            r["idx"], r["slot_rva"], r["slot_va"], r["slot_off"], r["kind"], r["name"], resolved))

# ---------------------------------------------------------------- .text 线性反汇编
text = [s for s in SECTIONS if s["name"] == ".text"][0]
tdata = b[text["raw"]: text["raw"]+text["rsize"]]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False

ws_slot_set = {r["slot_va"] for r in winsock_slots}
slot_by_va = {r["slot_va"]: r for r in rows}

# 稳健字节级扫描: 不依赖全量线性反汇编 (避免单个坏字节中断)
def byte_scan_ff15(data, base):
    hits=[]; i=0; n=len(data)-6
    while i < n:
        if data[i]==0xFF and data[i+1]==0x15:
            hits.append((base+i, struct.unpack("<I", data[i+2:i+6])[0], data[i:i+6]))
            i+=6; continue
        i+=1
    return hits

def byte_scan_e8(data, base):
    hits=[]; i=0; n=len(data)-5
    while i < n:
        if data[i]==0xE8:
            rel=struct.unpack("<i", data[i+1:i+5])[0]
            hits.append((base+i, (base+i+5+rel)&0xFFFFFFFF, data[i:i+5]))
            i+=5; continue
        i+=1
    return hits

ff15_raw = byte_scan_ff15(tdata, IB + text["va"])
e8_raw   = byte_scan_e8(tdata, IB + text["va"])

class Insn(object):
    __slots__=("address","bytes","mnemonic","op_str")
    def __init__(self,address,byts,mn,ops):
        self.address=address; self.bytes=byts; self.mnemonic=mn; self.op_str=ops

def dis_at(va, nbytes=16):
    o=rva2off(va-IB)
    if o is None: return None
    for i in md.disasm(b[o:o+nbytes], va):
        return Insn(i.address, i.bytes, i.mnemonic, i.op_str)
    return None

ff15=[]
for va,tgt,_ in ff15_raw:
    ins=dis_at(va)
    if ins is not None and ins.mnemonic=="call" and ins.op_str.startswith("dword ptr ["):
        ff15.append((ins,tgt))

insns=[]
for va,tgt,_ in e8_raw:
    ins=dis_at(va)
    if ins is not None and ins.mnemonic=="call":
        insns.append(ins)

with open(os.path.join(EV, "winsock_callsites.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("CALL_ID\tTEXT_RVA\tTEXT_VA\tFILE_OFF\tSECTION\tBYTES\tINSN\tSLOT_RVA\tSLOT_VA\tSLOT_FILE_OFF\tSLOT_KIND\tSLOT_NAME\tRESOLVED_API\tWINSOCK\n")
    n = 0
    for i, tgt in ff15:
        if tgt not in ws_slot_set: continue
        r = slot_by_va[tgt]
        n += 1
        rva = i.address - IB
        off = rva2off(rva)
        resolved = r["name"]
        if r["kind"] == "ORDINAL":
            od = r["value"] & 0xffff
            resolved = WS2_ORD.get(od, "ordinal:%d" % od)
        f.write("WC-%03d\t0x%06X\t0x%08X\t0x%06X\t%s\t%s\t%s %s\t0x%06X\t0x%08X\t0x%06X\t%s\t%s\t%s\tY\n" % (
            n, rva, i.address, off, sec_of_rva(rva), i.bytes.hex(),
            i.mnemonic, i.op_str, r["slot_rva"], r["slot_va"],
            r["slot_off"] if r["slot_off"] is not None else 0, r["kind"], r["name"], resolved))

# 全部 FF15 (含非 winsock) 统计
all_ff15 = collections.Counter()
for i, tgt in ff15:
    all_ff15[tgt] += 1

# E8 -> call rel32, 建调用目标
e8_targets = collections.Counter()
for i in insns:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: tgt = int(i.op_str, 16)
        except Exception: continue
        e8_targets[tgt] += 1

# ---------------------------------------------------------------- LoadLibraryA / GetProcAddress 调用点
def callsites_of_slot(slot_rva):
    va = IB + slot_rva
    out = []
    for i, tgt in ff15:
        if tgt == va:
            out.append(i)
    return out

slot_ll  = [r for r in rows if r["name"] == "LoadLibraryA"]
slot_gpa = [r for r in rows if r["name"] == "GetProcAddress"]

with open(os.path.join(EV, "loadlib_gpa_callsites.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("CALL_ID\tAPI\tTEXT_RVA\tTEXT_VA\tFILE_OFF\tSECTION\tBYTES\tSLOT_RVA\tSLOT_VA\tSLOT_FILE_OFF\n")
    n = 0
    pairs = [("LoadLibraryA",x) for x in slot_ll] + [("GetProcAddress",x) for x in slot_gpa]
    for label, r in pairs:
        for i in callsites_of_slot(r["slot_rva"]):
                n += 1
                rva = i.address - IB
                off = rva2off(rva)
                f.write("LB-%03d\t%s\t0x%06X\t0x%08X\t0x%06X\t%s\t%s\t0x%06X\t0x%08X\t0x%06X\n" % (
                    n, label, rva, i.address, off, sec_of_rva(rva), i.bytes.hex(),
                    r["slot_rva"], r["slot_va"], r["slot_off"]))

# ---------------------------------------------------------------- 模块身份字符串位置
dll_name_rvas = {}
for m in pe.sections:
    pass
for nm in [b"WS2_32.dll", b"WSOCK32.dll"]:
    st = 0
    while True:
        j = b.find(nm, st)
        if j < 0: break
        r = off2rva(j)
        dll_name_rvas.setdefault(nm.decode(), []).append((j, r, sec_of_rva(r) if r is not None else "?"))
        st = j+1

# ---------------------------------------------------------------- 汇总 JSON
summary = dict(
    dll_sha256=hashlib.sha256(b).hexdigest(),
    size=len(b), image_base=IB, size_of_image=SIZE_IMG,
    entry_point=pe.OPTIONAL_HEADER.AddressOfEntryPoint,
    sections=SECTIONS,
    iat_dir_rva=pe.OPTIONAL_HEADER.DATA_DIRECTORY[12].VirtualAddress,
    iat_dir_size=pe.OPTIONAL_HEADER.DATA_DIRECTORY[12].Size,
    import_dir_rva=pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].VirtualAddress,
    import_dir_size=pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].Size,
    n_iat_slots=N_SLOTS,
    n_named=sum(1 for r in rows if r["kind"] == "NAME"),
    n_ordinal=sum(1 for r in rows if r["kind"] == "ORDINAL"),
    n_winsock_slots=len(winsock_slots),
    n_ff15=len(ff15),
    n_winsock_callsites=sum(1 for i,t in ff15 if t in ws_slot_set),
    n_text_insns=len(insns),
    dll_name_rvas=dll_name_rvas,
    winsock_slot_names=sorted({r["name"] for r in winsock_slots}),
)
with open(os.path.join(EV, "analysis_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

# section json
with open(os.path.join(EV, "pe_sections.json"), "w", encoding="utf-8") as f:
    json.dump(SECTIONS, f, indent=2, ensure_ascii=False)

print(json.dumps({k: summary[k] for k in
    ["dll_sha256","size","image_base","entry_point","n_iat_slots","n_named","n_ordinal",
     "n_winsock_slots","n_ff15","n_winsock_callsites","n_text_insns"]}, indent=2))
print("winsock slot names:", summary["winsock_slot_names"])
print("dll_name_rvas:", dll_name_rvas)



