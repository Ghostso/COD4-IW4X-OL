from pathlib import Path
import pefile, re, sys

root = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
files = [
    root / "COD OL/codoMP_client_shipRetail.exe",
    root / "COD OL/codoMP_client_shipRetailBase.dll",
    root / "COD OL/TenProxy.dll",
    root / "COD OL/TCLS/TCLSClient.dll",
    root / "COD OL/TCLS/TCLS.dll",
    root / "COD OL/WeGameLauncher/launcher.exe",
    root / "WeGame/client_launcher.exe",
    root / "WeGame/tgp_daemon.exe",
    root / "WeGame/tcls/tcls_core.exe",
]
patterns = [
    b"TCLS_SHAREDMEMEMORY", b"TCLS_TASMEMORY_", b"tcls_core",
    b"TCLS_TENPROXY_RESULT", b"TCLS_GMAE_EXIT", b"TP3GameGuardShareMapping",
    b"TPUSERACCOUNT_SHAREDMEMEMORY", b"XTDL2", b"WIN_NO_TCLS", b"IsTCLSLogOn",
    b"codoMP_client_shipRetail.exe", b"StartFor", b"AddPath", b"game_id",
    b"cmd_start_for.ini", b"cmd_launcher_info.ini", b"TenProxy",
]
imports = {
    b"OpenFileMapping", b"MapViewOfFile", b"CreateFileMapping", b"CreateFile",
    b"CreateProcess", b"GetCommandLine", b"GetEnvironmentVariable",
    b"CreateNamedPipe", b"CallNamedPipe", b"WaitNamedPipe", b"OpenMutex",
    b"CreateMutex", b"GetCurrentProcessId", b"ShellExecute", b"WinExec",
    b"RegOpenKey", b"RegQueryValue", b"WSAConnect", b"connect",
}
for path in files:
    if not path.exists():
        continue
    data = path.read_bytes()
    print("\n" + "#" * 100)
    print("FILE", path, "size", len(data))
    pe = pefile.PE(data=data, fast_load=True)
    print("machine", hex(pe.FILE_HEADER.Machine), "ts", hex(pe.FILE_HEADER.TimeDateStamp),
          "base", hex(pe.OPTIONAL_HEADER.ImageBase), "entry", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
          "sizeimage", hex(pe.OPTIONAL_HEADER.SizeOfImage))
    print("sections", [(s.Name.rstrip(b"\0").decode("latin1"), hex(s.VirtualAddress),
                        hex(s.Misc_VirtualSize), hex(s.PointerToRawData)) for s in pe.sections])
    try:
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    except Exception as exc:
        print("import parse error", exc)
    print("IMPORTS:")
    for ent in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        hits = []
        for imp in ent.imports:
            if not imp.name:
                continue
            nm = imp.name.decode("latin1")
            if any(x.lower() in nm.lower().encode() for x in imports):
                hits.append((nm, hex(imp.address)))
        if hits:
            print(" ", ent.dll.decode("latin1"), hits)
    print("STRINGS:")
    for pat in patterns:
        offs = []
        start = 0
        while True:
            off = data.find(pat, start)
            if off < 0:
                break
            offs.append(off)
            start = off + 1
        if offs:
            print(" ", pat.decode("latin1"), "count", len(offs), "raw_offsets", [hex(x) for x in offs[:20]])
            for off in offs[:5]:
                try:
                    section = next(s for s in pe.sections if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData)
                    rva = section.VirtualAddress + (off - section.PointerToRawData)
                    va = pe.OPTIONAL_HEADER.ImageBase + rva
                    print("    ->", hex(off), "rva", hex(rva), "va", hex(va), "section", section.Name.rstrip(b"\0").decode("latin1"))
                except Exception as exc:
                    print("    ->", hex(off), "map error", exc)
