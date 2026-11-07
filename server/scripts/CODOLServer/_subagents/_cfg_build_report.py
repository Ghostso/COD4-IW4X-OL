#!/usr/bin/env python3
"""Generate cfgblock_fields.json (ASCII script, UTF-8 output data)."""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "cfgblock_fields.json"
BASE = 0x331C5C0

FIELDS = [
    {
        "offset": "+0x000",
        "va": "0x0331C5C0",
        "size": 4,
        "type": "dword",
        "written_by_641600": "yes (0x641BC8, = ApplySettings success flag)",
        "semantics": "apply_ok / real-connection gate. Nonzero => use real objA path",
        "default_when_no_tcls": 0,
        "evidence": "0064161E memset base; 00641BC8 mov [0x331c5c0],eax; read at 007F2BA0/007F2C64/006BBD25/006C195D",
        "confidence": "fact",
    },
    {
        "offset": "+0x004",
        "va": "0x0331C5C4",
        "size": 4,
        "type": "byte buffer (<=4 B used)",
        "written_by_641600": "yes (0x641667 push dst / 0x64166B tag 0x16)",
        "semantics": "TCLS tag 0x16 payload; later treated as a 4-byte value (see +0x53C formatter 0x6415C0). Passed to 0xB88CC0 arg4",
        "default_when_no_tcls": 0,
        "evidence": "00641666 push 0x331c5c4 / 6a16 tag; 00801545 push 0x331c5c4; 007F2CDC push 0x331c5c4",
        "confidence": "partial (buffer role fact, exact tag semantics unknown)",
    },
    {
        "offset": "+0x014",
        "va": "0x0331C5D4",
        "size": 4,
        "type": "dword",
        "written_by_641600": "yes (0x64164C = 0x10)",
        "semantics": "size/capacity for the +0x004 buffer (16 before tag 0x16 read)",
        "default_when_no_tcls": 16,
        "evidence": "00641647 mov ebx,0x10; 0064164C mov [0x331c5d4],ebx; 0080153F mov edi,[0x331c5d4]",
        "confidence": "fact",
    },
    {
        "offset": "+0x018",
        "va": "0x0331C5D8",
        "size": "variable (capacity 16, +0x014)",
        "type": "byte buffer / char[]",
        "written_by_641600": "yes (0x641694 dst / 0x641699 tag 0x18)",
        "semantics": "TCLS tag 0x18 string; copied into 0x75061B8 (0xAD bytes) at 0x642826 and passed to 0xB88CC0 arg2 (the buffer written to the stream)",
        "default_when_no_tcls": "empty",
        "evidence": "00641694 push 0x331c5d8 / 6a18; 00642826 push 0x331c5d8; 007F2D21 push 0x331c5d8",
        "confidence": "partial",
    },
    {
        "offset": "+0x098",
        "va": "0x0331C658",
        "size": 4,
        "type": "dword (length/capacity)",
        "written_by_641600": "yes (0x641685 = 0x80, and overwritten by tag 0x18 read via push at 0x641680)",
        "semantics": "length/capacity of the +0x018 buffer, NOT a port. Consumed as movzx word at 0x7F2CC8 and passed to 0xB88CC0 arg3",
        "default_when_no_tcls": 0,
        "evidence": "00641680 push 0x331c658; 00641685 mov dword [0x331c658],0x80; 00642813 mov eax,[0x331c658]; 007F2CC8 movzx edx,word [0x331c658]",
        "confidence": "fact (role), correction of prior port hypothesis",
    },
    {
        "offset": "+0x09C",
        "va": "0x0331C65C",
        "size": "16 (capacity from +0x0AC)",
        "type": "byte buffer",
        "written_by_641600": "yes (0x6416C4 dst / 0x6416C9 tag 0x19)",
        "semantics": "TCLS tag 0x19 payload. 0xB88CC0 receives its address as arg1 and copies 16 bytes; the first byte also reaches the mode member",
        "default_when_no_tcls": 0,
        "evidence": "006416C4 push 0x331c65c / 6a19; 0064170D push 0x331c65c (0xC3C603 arg); 007F2D26 push 0x331c65c",
        "confidence": "fact (role), tag semantics unknown",
    },
    {
        "offset": "+0x0AC",
        "va": "0x0331C66C",
        "size": 4,
        "type": "dword",
        "written_by_641600": "yes (0x6416B9 = 0x10)",
        "semantics": "size/capacity companion for the +0x09C buffer",
        "default_when_no_tcls": 16,
        "evidence": "006416B4 push 0x331c66c; 006416B9 mov [0x331c66c],ebx(0x10)",
        "confidence": "fact",
    },
    {
        "offset": "+0x0B0",
        "va": "0x0331C670",
        "size": "variable",
        "type": "byte buffer / char[]",
        "written_by_641600": "yes (0x64178C dst / 0x641791 tag 0x07 second field)",
        "semantics": "passed to 0xB88CC0 as arg8 (push at 0x7F2CD0). Copied into object member +0x3658 (cap 0x400) by 0xB88CC0",
        "default_when_no_tcls": "empty",
        "evidence": "0064178C push 0x331c670; 007F2CD0 push 0x331c670; 00B88D75 lea ebx,[esi+0x360c]",
        "confidence": "fact (message role), field purpose unknown",
    },
    {
        "offset": "+0x4B0",
        "va": "0x0331CA70",
        "size": 4,
        "type": "dword (length)",
        "written_by_641600": "yes (0x64173F push dst, clamp to 0x400, default 0x400)",
        "semantics": "length of tag 0x07 payload (host string length)",
        "default_when_no_tcls": 1024,
        "evidence": "0064173F push 0x331ca70; 00641772 mov dword [0x331ca70],0x400; 00641787 push 0x331ca70",
        "confidence": "fact",
    },
    {
        "offset": "+0x4B4",
        "va": "0x0331CA74",
        "size": "variable (capacity n/a)",
        "type": "byte buffer",
        "written_by_641600": "yes (0x6417FE dst / 0x641803 tag 0x1B second field)",
        "semantics": "tag 0x1B payload buffer. NOT referenced by 0x7F2B90 path in this image",
        "default_when_no_tcls": "empty",
        "evidence": "006417F9 push 0x331caf4 (len); 006417FE push 0x331ca74 (dst)",
        "confidence": "fact (written), unused by connection path",
    },
    {
        "offset": "+0x534",
        "va": "0x0331CAF4",
        "size": 4,
        "type": "dword (length)",
        "written_by_641600": "yes (0x6417B1 push dst, clamp to 0x80, default 0x80)",
        "semantics": "length of tag 0x1B payload",
        "default_when_no_tcls": 128,
        "evidence": "006417B1 push 0x331caf4; 006417E4 mov dword [0x331caf4],0x80; 006417F9 push 0x331caf4",
        "confidence": "fact",
    },
    {
        "offset": "+0x538",
        "va": "0x0331CAF8",
        "size": 4,
        "type": "dword",
        "written_by_641600": "yes (0x64185B dst for tag 5 blob copy)",
        "semantics": "TLS/cert fingerprint or IP word: 0x6415C0 formats its 4 bytes as byte0.byte1.byte2.byte3 string. Passed to 0xB88CC0 arg5",
        "default_when_no_tcls": 0,
        "evidence": "006415C3-006415D2 reads 0x331caf8..0x331cafb; 0064185B push 0x331caf8; 007F2CC1 mov ecx,[0x331caf8]",
        "confidence": "partial",
    },
    {
        "offset": "+0x53C..+0xD3F",
        "va": "0x0331CAFC..0x0331D2FF",
        "size": "rest of 0xD40 block",
        "type": "unreferenced by this image",
        "written_by_641600": "no",
        "semantics": "UNKNOWN / unused (no absolute references found in image)",
        "default_when_no_tcls": 0,
        "evidence": "full scan: distinct_offsets inside 0x331C5C0..0x331D300 == 14",
        "confidence": "fact (unreferenced), semantics unresolved",
    },
]

NOTES = {
    "image": "CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin",
    "image_base": "0x400000",
    "block_base": "0x331C5C0",
    "block_size": "0xD40",
    "corrections": [
        "0x331C5C0+0x98 is NOT a port. It is the length/capacity of the +0x18 buffer (initialized to 0x80, then set by the tag 0x18 size out-parameter). The real TCP/UDP port lives in the separate global 0x81A9EC4 (tag 0x07 field 1) and is passed to the objA constructor 0xB88B80, not to 0xB88CC0.",
        "0xB88CC0 has only one caller: 0x7F2D2A. It never receives a port; its port word (arg5) is 0x331C658.",
        "Nothing in the image writes the value 1 into 0x331C5C0. Only 0x641BC8 writes it, using ApplySettings' own return value.",
    ],
}


def main():
    data = {"fields": FIELDS, "notes": NOTES}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote %s (%d fields)" % (OUT, len(FIELDS)))


if __name__ == "__main__":
    main()
