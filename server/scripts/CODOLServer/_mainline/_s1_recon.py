# -*- coding: utf-8 -*-
"""
_s1_recon.py - static reconnaissance for the CODOL lobby path.

Pure disk analysis. No game launch, no injection, no network changes.
Locates key ASCII/GBK strings inside the CODOL client binaries and prints
file offset / RVA / VA for each hit.
"""
import os
import sys

import pefile

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
TARGETS = {
    "exe": os.path.join(ROOT, "codoMP_client_shipRetail.exe"),
    "base": os.path.join(ROOT, "codoMP_client_shipRetailBase.dll"),
    "gdp": os.path.join(ROOT, "GDPOpenProtocol.tdr"),
}

# ASCII probes (encoded ascii) and GBK probes (encoded gbk)
ASCII_PROBES = [
    b"BD_LOBBY_CONNECTED",
    b"DW_LOBBY_CONNECTED",
    b"DW_LOBBY_ERROR",
    b"dwLogonStart",
    b"BD_LOBBY_PROTOCOL_VERSION_FAILURE",
    b"BD_LOBBY_INTERNAL_FAILURE",
    b"BD_LOBBY_PROTOCOL_ERROR",
    b"BD_MAX_ERROR_CODE",
    b"Unknown bdLobbyErrorCode",
    b"bdLobbyErrorCode",
    b"BD_NOT_CONNECTED",
    b"BD_SEND_FAILED",
    b"cppOnDWConnected",
    b"cppOnDWDisconnected",
    b"title_id",
    b"tencent_ticket",
    b"onlinegame",
    b"lobbyhost",
    b"blazehost",
    b"dwblazehost",
    b"dw_lobby",
    b"com_",
]

GBK_PROBES = [
    "\u65e0\u6cd5\u8fde\u63a5\u5927\u5385\u670d\u52a1",  # 无法连接大厅服务
    "\u65e0\u6cd5\u8fde\u63a5\u5927\u5385",
    "\u5927\u5385\u670d\u52a1",
    "\u8fde\u63a5\u5927\u5385",
]


def sections(pe):
    out = []
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode("latin-1")
        out.append(
            {
                "name": name,
                "va": s.VirtualAddress,
                "vsize": s.Misc_VirtualSize,
                "raw": s.PointerToRawData,
                "rawsize": s.SizeOfRawData,
                "chars": s.Characteristics,
            }
        )
    return out


def off_to_rva(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return s["va"] + (off - s["raw"]), s["name"]
    return None, None


def scan(blob, needle):
    hits = []
    start = 0
    while True:
        i = blob.find(needle, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    return hits


def main():
    for key, path in TARGETS.items():
        if not os.path.exists(path):
            print("MISSING", key, path)
            continue
        with open(path, "rb") as fh:
            blob = fh.read()
        print("=" * 78)
        print("TARGET", key, path, len(blob))
        secs = []
        image_base = 0
        try:
            pe = pefile.PE(path, fast_load=True)
            image_base = pe.OPTIONAL_HEADER.ImageBase
            secs = sections(pe)
            print("ImageBase 0x%08X EntryPoint 0x%08X" % (
                image_base, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
            for s in secs:
                print("  SECTION %-10s VA=0x%08X VS=0x%08X RAW=0x%08X RS=0x%08X" % (
                    s["name"], s["va"], s["vsize"], s["raw"], s["rawsize"]))
            pe.close()
        except Exception as exc:  # noqa: BLE001
            print("  (not a PE:", exc, ")")

        print("-- ASCII probes --")
        for probe in ASCII_PROBES:
            hits = scan(blob, probe)
            if not hits:
                continue
            for off in hits:
                rva, sec = off_to_rva(secs, off)
                if rva is not None:
                    print("  %-34s off=0x%08X rva=0x%08X va=0x%08X sec=%s" % (
                        probe.decode("latin-1"), off, rva, image_base + rva, sec))
                else:
                    print("  %-34s off=0x%08X (no section)" % (
                        probe.decode("latin-1"), off))

        print("-- GBK probes --")
        for probe in GBK_PROBES:
            raw = probe.encode("gbk")
            hits = scan(blob, raw)
            if not hits:
                continue
            for off in hits:
                rva, sec = off_to_rva(secs, off)
                if rva is not None:
                    print("  %-34s off=0x%08X rva=0x%08X va=0x%08X sec=%s" % (
                        probe, off, rva, image_base + rva, sec))
                else:
                    print("  %-34s off=0x%08X (no section)" % (probe, off))


if __name__ == "__main__":
    main()
