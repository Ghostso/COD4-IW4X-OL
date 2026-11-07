from pathlib import Path
import sys

import pefile

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")

targets = [
    r"COD OL\codoMP_client_shipRetail.exe",
    r"COD OL\codoMP_client_shipRetailBase.dll",
    r"COD OL\TenProxy.dll",
    r"COD OL\TenRpcs.dll",
    r"COD OL\GameRpcs.dll",
    r"COD OL\tcj.dll",
    r"COD OL\GDPLoader.dll",
    r"COD OL\GameDataPlatformServer.dll",
    r"COD OL\policyprobe.dll",
    r"COD OL\GbSpy.dll",
    r"COD OL\ACE-DRV32.dll",
    r"COD OL\tersafe.dll",
    r"COD OL\libcef.dll",
    r"COD OL\localization.txt",
]

phrases = [
    "请从 Client 启动游戏",
    "从 Client 启动游戏",
    "要 从 Client 启动游戏",
    "请从Client启动游戏",
    "Client 启动游戏",
    "Client.exe)启动游戏",
    "请使用腾讯游戏登录器",
    "TCLS文件夹内的Client.exe",
    "启动游戏。",
    "WIN_NO_TCLS",
    "IsTCLSLogOn",
]


def section_for(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.Name.rstrip(b"\0").decode(errors="replace")
    return "?"


def scan_file(path):
    b = path.read_bytes()
    print("\n" + "=" * 100)
    print("FILE", path, "size", len(b))
    is_pe = b[:2] == b"MZ"
    pe = None
    if is_pe:
        try:
            pe = pefile.PE(data=b, fast_load=True)
        except Exception:
            pe = None
    base = pe.OPTIONAL_HEADER.ImageBase if pe else 0

    for phrase in phrases:
        variants = {
            "utf16le": phrase.encode("utf-16le"),
            "utf8": phrase.encode("utf-8"),
            "gbk": phrase.encode("gbk", errors="replace"),
        }
        for enc, pat in variants.items():
            pos = 0
            hits = 0
            while True:
                pos = b.find(pat, pos)
                if pos < 0:
                    break
                hits += 1
                rva = None
                if pe:
                    try:
                        rva = pe.get_rva_from_offset(pos)
                    except Exception:
                        rva = None
                va = (base + rva) if rva is not None else None
                sec = section_for(pe, rva) if (pe and rva is not None) else "?"
                ctx = b[max(0, pos - 40):pos + len(pat) + 60]
                print("  HIT", repr(phrase), enc, "off", hex(pos), "rva", hex(rva) if rva is not None else "-",
                      "va", hex(va) if va is not None else "-", "section", sec, "ctx", ctx.hex())
                pos += 1
            if hits == 0:
                continue


for rel in targets:
    p = ROOT / rel
    if not p.exists():
        print("MISSING", p)
        continue
    scan_file(p)
