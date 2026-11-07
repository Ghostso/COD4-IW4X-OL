# EX-065 PHASE 3/5: recover the TCLS<->CODOL context boundary by scanning
# tcls_core.exe for IPC artefacts, GamePID flow, and named objects.
import json
import re

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"

KEY_STRINGS = [
    b"TCLS_SHAREDMEMEMORY", b"TCLS_SHAREDMEMORY", b"GamePID", b"TCLS",
    b"IIPS", b"CODOL", b"codoMP_client_shipRetail", b"Repair", b"Restore",
    b"WeGame", b"SharedMemory", b"SHAREDMEM", b"GamePid", b"gamepid",
]

IPC_APIS = [
    "OpenFileMappingA", "OpenFileMappingW", "CreateFileMappingA",
    "CreateFileMappingW", "MapViewOfFile", "UnmapViewOfFile",
    "CreateMutexA", "CreateMutexW", "OpenMutexA", "OpenMutexW",
    "CreateEventA", "CreateEventW", "OpenEventA", "OpenEventW",
    "CreateNamedPipeA", "CreateNamedPipeW", "ConnectNamedPipe",
    "CreateProcessA", "CreateProcessW", "ShellExecuteA", "ShellExecuteW",
    "ShellExecuteExA", "ShellExecuteExW", "WinExec",
    "GetCommandLineA", "GetCommandLineW", "CommandLineToArgvW",
    "GetEnvironmentVariableA", "GetEnvironmentVariableW",
    "GetCurrentProcessId", "CreateToolhelp32Snapshot", "Process32First",
    "Process32FirstW", "Process32Next", "Process32NextW", "OpenProcess",
    "QueryFullProcessImageNameA", "QueryFullProcessImageNameW",
    "RegOpenKeyA", "RegOpenKeyW", "RegOpenKeyExA", "RegOpenKeyExW",
    "RegQueryValueA", "RegQueryValueExA", "RegQueryValueExW",
    "GetPrivateProfileIntA", "GetPrivateProfileIntW",
    "GetPrivateProfileStringA", "GetPrivateProfileStringW",
    "SHGetFolderPathA", "SHGetFolderPathW", "SHGetKnownFolderPath",
    "LoadLibraryA", "LoadLibraryW", "GetProcAddress",
]


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("PHASE 3: IPC / context strings in tcls_core.exe")
    print("=" * 78)
    for s in KEY_STRINGS:
        st = 0
        while True:
            i = img.data.find(s, st)
            if i < 0:
                break
            rva, sec = img.raw2rva(i)
            print("  %-34s raw 0x%07X RVA 0x%07X sec %-8s" % (
                s.decode(errors="replace"), i,
                rva if rva is not None else 0, sec))
            st = i + 1

    print()
    print("=" * 78)
    print("PHASE 1/5: IPC + process + registry APIs actually imported")
    print("=" * 78)
    found = {}
    for slot, (dll, nm) in img.imports.items():
        if nm in IPC_APIS:
            found.setdefault(nm, []).append((slot, dll))
    for nm in IPC_APIS:
        if nm in found:
            for slot, dll in found[nm]:
                print("  %-32s IAT VA 0x%08X  %s" % (
                    nm, img.base + slot, dll))

    print()
    print("=" * 78)
    print("call sites for the key IPC / process APIs")
    print("=" * 78)
    lo, hi = img.codesec()
    hits = {}
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        if insn.mnemonic == "call" and insn.operands \
                and insn.operands[0].type == X86_OP_MEM \
                and insn.operands[0].mem.base == 0:
            nm = img.imports.get(insn.operands[0].mem.disp - img.base)
            if nm and nm[1] in IPC_APIS:
                hits.setdefault(nm[1], []).append(r)
        r += insn.size
    for nm in IPC_APIS:
        if nm in hits:
            print("  %-32s %d sites  %s" % (
                nm, len(hits[nm]),
                " ".join("0x%X" % x for x in hits[nm][:8])))


if __name__ == "__main__":
    main()
