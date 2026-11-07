#!/usr/bin/env python3
"""Read-only analysis of TenProxy.dll (the CODOL-side TCLS shared-memory consumer).

Pure static analysis of a PE file on disk. No process launch, no writes to the
target tree, no debugger. ASCII-only output.

TenProxy.dll is loaded at 0x10000000 inside the game process.  Its export
"Invoke" (ordinal 1) allocates the CTclsProxy object; slot +0x04 of the primary
vtable is CTclsProxy::Initialize, which opens

    TCLS_SHAREDMEMEMORY<decimal pid>

and maps it read-only.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import capstone
import pefile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
TENPROXY = PROJECT / "COD OL" / "TenProxy.dll"

# VAs inside TenProxy.dll (image base 0x10000000)
PRIMARY_VTABLE = 0x100205D0
INITIALIZE = 0x10005E40
SLOT_GETDWORD = 0x10007DA0       # primary vtable +0x24
SLOT_GETBYTES = 0x10007EA0       # primary vtable +0x28
SLOT_GETBLOCK = 0x10008250       # primary vtable +0x30
SLOT_GETBLOCK2 = 0x10008510      # primary vtable +0x38
CTOR = 0x10005510
INVOKE_BODY = 0x10001D70


def load(path: Path = TENPROXY):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=False)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    return pe, data, md


IMAGE_BASE = 0x10000000


def rva_for_va(pe, va):
    return va - pe.OPTIONAL_HEADER.ImageBase


def raw_for_va(pe, va):
    rva = rva_for_va(pe, va)
    for sec in pe.sections:
        lo = sec.VirtualAddress
        size = max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < lo + size:
            delta = rva - lo
            if delta < sec.SizeOfRawData:
                return sec.PointerToRawData + delta
    return None


def read_va(pe, data, va, size):
    off = raw_for_va(pe, va)
    if off is None or off + size > len(data):
        return None
    return data[off:off + size]


def wstr(pe, data, va, limit=256):
    raw = read_va(pe, data, va, limit * 2)
    if raw is None:
        return None
    out = []
    for i in range(0, len(raw) - 1, 2):
        ch = raw[i] | (raw[i + 1] << 8)
        if ch == 0:
            break
        out.append(chr(ch))
    return "".join(out)


def cstr(pe, data, va, limit=256):
    raw = read_va(pe, data, va, limit)
    if raw is None:
        return None
    end = raw.find(b"\x00")
    return raw[:end if end >= 0 else len(raw)].decode("latin1", "replace")


def imports(pe):
    out = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for desc in pe.DIRECTORY_ENTRY_IMPORT:
            dll = desc.dll.decode("latin1", "replace")
            for imp in desc.imports:
                name = (imp.name.decode("latin1", "replace")
                        if imp.name else "ord%d" % imp.ordinal)
                out[imp.address] = "%s!%s" % (dll, name)
    return out


def disasm(pe, data, md, start, end, imp=None):
    off = raw_for_va(pe, start)
    if off is None:
        raise SystemExit("no raw data for 0x%X" % start)
    blob = data[off:off + (end - start)]
    pos = 0
    rows = []
    while pos < len(blob):
        insn = next(md.disasm(blob[pos:], start + pos), None)
        if insn is None:
            pos += 1
            continue
        note = ""
        if insn.mnemonic in ("call", "jmp") and insn.operands:
            op = insn.operands[0]
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 \
                    and op.mem.index == 0 and imp:
                note = "  ; " + imp.get(op.mem.disp, "IAT?0x%X" % op.mem.disp)
            elif op.type == capstone.x86.X86_OP_IMM:
                s = wstr(pe, data, op.imm, 96)
                if s and len(s) > 3:
                    note = '  ; L"%s"' % s
        rows.append((insn, note))
        pos += insn.size
    return rows


def show(rows):
    for insn, note in rows:
        print("0x%08X  %-22s %-7s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, note))


def cmd_vtable(args):
    pe, data, md = load()
    base = int(args.base, 16)
    raw = read_va(pe, data, base, 4 * (args.count + 1))
    print("primary vtable VA 0x%08X" % base)
    for i in range(args.count + 1):
        ptr = struct.unpack_from("<I", raw, i * 4)[0]
        stub = read_va(pe, data, ptr, 5)
        target = ptr
        if stub and stub[0] == 0xE9:
            rel = struct.unpack_from("<i", stub, 1)[0]
            target = (ptr + 5 + rel) & 0xFFFFFFFF
        print("  +0x%02X  slot 0x%08X  stub 0x%08X  -> 0x%08X" %
              (i * 4, base + i * 4, ptr, target))


def cmd_disasm(args):
    pe, data, md = load()
    imp = imports(pe)
    show(disasm(pe, data, md, int(args.start, 16), int(args.end, 16), imp))


def cmd_strings(args):
    pe, data, md = load()
    for spec in args.va:
        va = int(spec, 16)
        print("W 0x%08X %r" % (va, wstr(pe, data, va)))
        print("A 0x%08X %r" % (va, cstr(pe, data, va)))


def cmd_layout(args):
    """Emit the TCLS shared-memory tag/entry layout reconstruction."""
    pe, data, md = load()
    layout = {
        "object_name": {
            "format": "TCLS_SHAREDMEMEMORY%d",
            "suffix": "decimal PID of the game process (GetCurrentProcessId)",
            "evidence": "TenProxy.dll 0x100061E2 OpenFileMappingW "
                        "with 0xF001F, name built at 0x10006177",
        },
        "mapping": {
            "size": "0x80000 (512 KiB), created by the producer",
            "initial_version_dword": "0x40",
            "consumer_version_check": "cmp [this+0x18D0],0x40 ; jae ok",
        },
        "header": [
            {"offset": "0x00", "size": 4,
             "meaning": "version/header dword; must be >= 0x40",
             "evidence": "0x100062E9 mov eax,[edx]; 0x100062F4 cmp eax,0x40"},
            {"offset": "0x04", "size": 4,
             "meaning": "tag offset table base (relative to mapped base)",
             "evidence": "0x10006371 / 0x10006383 store [this+0x18C4] / +0x18C8"},
        ],
        "tag_lookup": {
            "table_base": "mapped + 0x04",
            "entry_offset": "dword at mapped + 4 + (tag-1)*4",
            "entry_address": "mapped + entry_offset",
            "entry_fields": [
                {"offset": "+0x00", "meaning": "payload byte length (4 = DWORD)"},
                {"offset": "+0x04", "meaning": "payload bytes / value"},
            ],
            "evidence": "0x10007DE3 mov eax,[edx+ecx*4-4] ; "
                        "0x10007DED mov edx,[ecx+0x18C4] ; 0x10007DF3 add edx,[ebp-0x10]",
        },
        "consumed_tags": [
            {"tag": 1, "kind": "dword"},
            {"tag": 5, "kind": "block", "note": "LoginKey, one-shot"},
            {"tag": 7, "kind": "string", "note": "<= 0x400 bytes"},
            {"tag": 8, "kind": "block", "note": "fields split on ';' and ':'"},
            {"tag": 0x12, "kind": "dword", "note": "length of tag 5"},
            {"tag": 0x16, "kind": "dword"},
            {"tag": 0x18, "kind": "block", "note": "<= 0x80 bytes"},
            {"tag": 0x19, "kind": "block", "note": "<= 0x10 bytes"},
            {"tag": 0x1B, "kind": "block", "note": "<= 0x80 bytes"},
        ],
        "config_block_331C5C0": [
            {"block_off": "0x000", "size": 4, "source": "parser success flag",
             "evidence": "0x641BC8"},
            {"block_off": "0x004", "size": 0x10, "source": "tag 0x16 (DWORD)",
             "len_at": "0x014", "evidence": "0x641661"},
            {"block_off": "0x018", "size": 0x80, "source": "tag 0x18 (block)",
             "len_at": "0x09C", "evidence": "0x641694"},
            {"block_off": "0x0B0", "size": 0x400, "source": "tag 7 (string)",
             "len_at": "0x4B0", "evidence": "0x64178C"},
            {"block_off": "0x4B4", "size": 0x80, "source": "tag 0x1B (block)",
             "len_at": "0x534", "evidence": "0x6417FE"},
            {"block_off": "0x538", "size": 0x400, "source": "tag 5 (block, len = tag 0x12)",
             "evidence": "0x64185B"},
        ],
    }
    print(json.dumps(layout, indent=1, ensure_ascii=True))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("vtable")
    p.add_argument("--base", default=hex(PRIMARY_VTABLE))
    p.add_argument("--count", type=int, default=16)
    p.set_defaults(func=cmd_vtable)

    p = sub.add_parser("disasm")
    p.add_argument("start")
    p.add_argument("end")
    p.set_defaults(func=cmd_disasm)

    p = sub.add_parser("strings")
    p.add_argument("va", nargs="+")
    p.set_defaults(func=cmd_strings)

    p = sub.add_parser("layout")
    p.set_defaults(func=cmd_layout)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
